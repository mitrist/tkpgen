"""Views для mini app MAX и API-оберток над существующей логикой сервиса."""

from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
from datetime import datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.clickjacking import xframe_options_exempt
from docxtpl import DocxTemplate

from .choices import INTERNAL_CLIENT_CHOICES, SROK_CHOICES
from .forms import ContractForm
from .max_webapp_auth import (
    get_or_create_max_user,
    issue_app_token,
    validate_max_init_data,
    validate_ttl_and_replay,
    verify_app_token,
)
from .models import ContractRecord, Counterparty, Service, TKPRecord
from .requisites_parser import FIELD_ORDER, parse_requisites_file
from .telegram_miniapp import _draft_from_form_data
from .tkp_draft_service import submit_final
from .tkp_reference import get_tkp_reference_data
from .contract_payment_terms import PAYMENT_TERMS_CHOICE_2, payment_terms_text_for_doc
from .contract_poryadok import PORYADOK_CHOICE_1
from .views import (
    COMPLEX_CONTRACTS_WITH_SPEC_TABLE,
    COMPLEX_CONTRACT_TEMPLATE_03,
    CONTRACT_SPEC_TABLE_PLACEHOLDER,
    CONTRACT_TEMPLATES_SUBDIR,
    SERVICE_TO_CONTRACT_TEMPLATE,
    UNIVERSAL_TKP_SERVICE,
    _build_complex_table_document,
    _complex_rows_json_to_ctx,
    _convert_docx_to_pdf,
    _director_genitive,
    _dolznost_from_customer_in_person,
    _format_price,
    _generate_complex_and_save_files,
    _get_next_contract_seq_for_date,
    _insert_table_into_docx,
    _load_ris_text_file,
    _normalize_ris_text,
    _ensure_tkp_output_path,
    _save_complex_tkp_record,
    contract_template_extras_for_ctx,
    get_contract_template_for_complex_tkp,
)

logger = logging.getLogger(__name__)


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _auth_payload_from_request(request):
    token = request.headers.get("X-Max-App-Token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        token = (request.GET.get("token") or "").strip()
    payload = verify_app_token(token)
    return payload


def _max_auth_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        payload = _auth_payload_from_request(request)
        if not payload:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        request.max_auth = payload
        return view_func(request, *args, **kwargs)

    return wrapped


@require_http_methods(["GET"])
@xframe_options_exempt
def max_app_view(request):
    """Страница mini app MAX (frontend shell)."""
    return render(request, "proposals/max_app.html", {})


@require_http_methods(["POST"])
@csrf_exempt
def max_auth_validate_view(request):
    """Проверка initData MAX и выдача app token для API mini app."""
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    init_data = body.get("initData") or ""
    validated = validate_max_init_data(init_data)
    if not validated:
        if not getattr(settings, "MAX_ALLOW_INSECURE_INITDATA", False):
            return JsonResponse({"error": "Invalid initData"}, status=401)
        # Временный fallback для запуска mini app без валидного initData.
        # Нужен только как временный обход в окружениях, где MAX client не передает initData.
        logger.warning("MAX auth fallback: initData invalid, issuing insecure token")
        app_token = issue_app_token(
            user_id=1,
            max_user_id="insecure",
            chat_id="",
        )
        return JsonResponse(
            {
                "ok": True,
                "appToken": app_token,
                "insecure": True,
                "warning": "initData validation skipped",
                "user": {
                    "id": 1,
                    "max_user_id": "insecure",
                    "first_name": "",
                    "last_name": "",
                },
            }
        )

    ok, err = validate_ttl_and_replay(validated)
    if not ok:
        return JsonResponse({"error": err or "initData validation failed"}, status=401)

    try:
        user = get_or_create_max_user(validated)
    except Exception as exc:
        return JsonResponse({"error": f"User mapping failed: {exc}"}, status=400)

    user_data = validated.get("user") if isinstance(validated.get("user"), dict) else {}
    chat_data = validated.get("chat") if isinstance(validated.get("chat"), dict) else {}
    app_token = issue_app_token(
        user_id=user.pk,
        max_user_id=str(user_data.get("id") or ""),
        chat_id=str(chat_data.get("id") or ""),
    )
    return JsonResponse(
        {
            "ok": True,
            "appToken": app_token,
            "user": {
                "id": user.pk,
                "max_user_id": user_data.get("id"),
                "first_name": user_data.get("first_name") or "",
                "last_name": user_data.get("last_name") or "",
            },
        }
    )


@require_http_methods(["GET"])
@csrf_exempt
@_max_auth_required
def max_reference_view(request):
    """Справочники для mini app."""
    data = get_tkp_reference_data()
    data["internal_clients"] = [{"value": v, "label": l} for v, l in INTERNAL_CLIENT_CHOICES if v]
    data["srok_choices"] = [{"value": v, "label": l} for v, l in SROK_CHOICES if v]
    data["counterparties"] = list(
        Counterparty.objects.order_by("-created_at").values(
            "id",
            "name",
            "inn",
            "kpp",
            "address",
            "director",
            "ogrn",
            "account",
            "bank",
            "bik",
            "kor_account",
            "phone",
            "email",
        )[:200]
    )
    data["ris_text"] = _load_ris_text_file()
    return JsonResponse(data)


@require_http_methods(["POST"])
@csrf_exempt
@_max_auth_required
def max_submit_single_tkp_view(request):
    """Сформировать ТКП на одну услугу из данных mini app."""
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    max_user_id = request.max_auth.get("m") or request.max_auth.get("u")
    chat_id = request.max_auth.get("c") or max_user_id
    draft, err = _draft_from_form_data(str(max_user_id), str(chat_id), body)
    if err:
        return JsonResponse({"error": err}, status=400)

    base_name, err = submit_final(draft, user=None)
    if err:
        return JsonResponse({"error": err}, status=400)
    return JsonResponse(
        {
            "ok": True,
            "base_name": base_name,
            "download_docx": f"/max/api/download/docx/?f={base_name}",
            "download_pdf": f"/max/api/download/pdf/?f={base_name}",
        }
    )


@require_http_methods(["POST"])
@csrf_exempt
@_max_auth_required
def max_submit_complex_tkp_view(request):
    """Сформировать комплексное ТКП."""
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    rows = body.get("rows") or []
    if not isinstance(rows, list) or not rows:
        return JsonResponse({"error": "rows required"}, status=400)
    date_value = (body.get("date") or "").strip()
    client = (body.get("client") or "").strip()
    if not date_value or not client:
        return JsonResponse({"error": "date and client required"}, status=400)

    try:
        date_obj = datetime.strptime(date_value[:10], "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    rows_serializable = []
    for r in rows:
        try:
            qty = Decimal(str(r.get("quantity") or 0))
            price = Decimal(str(r.get("price_per_unit") or 0))
            total = Decimal(str(r.get("total") or (qty * price)))
        except Exception:
            return JsonResponse({"error": "Invalid rows numeric values"}, status=400)
        rows_serializable.append(
            {
                "service_name": (r.get("service_name") or "").strip() or "Позиция",
                "comment": (r.get("comment") or "").strip(),
                "srok": (r.get("srok") or "").strip(),
                "unit": (r.get("unit") or "m2"),
                "quantity": str(qty),
                "price_per_unit": str(price),
                "total": str(total),
            }
        )

    data = {
        "date": date_obj.strftime("%Y-%m-%d"),
        "client": client,
        "region_name": (body.get("region_name") or "").strip(),
        "room": (body.get("room") or "").strip(),
        "srok": (body.get("srok") or "").strip(),
        "text1": (body.get("text1") or "").strip(),
        "rows": rows_serializable,
    }
    try:
        base_name = _generate_complex_and_save_files(data)
    except Exception as exc:
        return JsonResponse({"error": f"Complex TKP generation failed: {exc}"}, status=500)
    if not base_name:
        return JsonResponse({"error": "Complex TKP generation failed"}, status=500)
    _save_complex_tkp_record(data, user=None)
    return JsonResponse(
        {
            "ok": True,
            "base_name": base_name,
            "download_docx": f"/max/api/download/docx/?f={base_name}",
            "download_pdf": f"/max/api/download/pdf/?f={base_name}",
        }
    )


@require_http_methods(["POST"])
@csrf_exempt
@_max_auth_required
def max_requisites_parse_view(request):
    """Извлечь реквизиты из файла (.docx/.pdf)."""
    source_file = request.FILES.get("source_file")
    if not source_file:
        return JsonResponse({"error": "source_file required"}, status=400)
    try:
        parsed = parse_requisites_file(source_file.name, source_file.read())
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "fields": parsed})


@require_http_methods(["POST"])
@csrf_exempt
@_max_auth_required
def max_requisites_save_view(request):
    """Создать карточку контрагента."""
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    payload = {}
    for key in FIELD_ORDER:
        payload[key] = (body.get(key) or "").strip()
    payload["kpp"] = (body.get("kpp") or "").strip()
    payload["kor_account"] = (body.get("kor_account") or "").strip()
    payload["email"] = (body.get("email") or "").strip()
    inn = payload.get("inn") or ""
    if inn and Counterparty.objects.filter(inn=inn).exists():
        cp = Counterparty.objects.filter(inn=inn).order_by("-created_at").first()
        return JsonResponse({"ok": True, "counterparty_id": cp.pk, "exists": True})
    cp = Counterparty.objects.create(**payload)
    return JsonResponse({"ok": True, "counterparty_id": cp.pk, "exists": False})


@require_http_methods(["GET"])
@csrf_exempt
@_max_auth_required
def max_counterparties_view(request):
    q = (request.GET.get("q") or "").strip()
    qs = Counterparty.objects.all().order_by("-created_at")
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(inn__icontains=q)
    data = list(
        qs.values(
            "id",
            "name",
            "inn",
            "kpp",
            "address",
            "director",
            "ogrn",
            "account",
            "bank",
            "bik",
            "kor_account",
            "phone",
            "email",
        )[:200]
    )
    return JsonResponse({"results": data})


@require_http_methods(["GET"])
@csrf_exempt
@_max_auth_required
def max_counterparty_detail_view(request, pk):
    try:
        cp = Counterparty.objects.get(pk=pk)
    except Counterparty.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(
        {
            "id": cp.pk,
            "name": cp.name or "",
            "inn": cp.inn or "",
            "kpp": cp.kpp or "",
            "address": cp.address or "",
            "director": cp.director or "",
            "director_genitive": _director_genitive(cp.director or ""),
            "ogrn": cp.ogrn or "",
            "account": cp.account or "",
            "bank": cp.bank or "",
            "bik": cp.bik or "",
            "kor_account": cp.kor_account or "",
            "email": cp.email or "",
            "phone": cp.phone or "",
        }
    )


@require_http_methods(["GET"])
@csrf_exempt
@_max_auth_required
def max_tkps_view(request):
    """Список последних ТКП для выбора в mini app."""
    q = (request.GET.get("q") or "").strip()
    qs = TKPRecord.objects.all().order_by("-created_at")
    if q:
        qs = qs.filter(
            Q(number__icontains=q)
            | Q(client__icontains=q)
            | Q(service__icontains=q)
        )
    data = list(
        qs.values(
            "id",
            "number",
            "date",
            "client",
            "service",
            "sum_total",
        )[:150]
    )
    return JsonResponse({"results": data})


def _build_contract_context(cd, cp, tkp, contract_template_file=""):
    include_ris = bool(cd.get("include_ris"))
    ris_text = _normalize_ris_text(_load_ris_text_file()) if include_ris else ""
    customer_name = (cd.get("customer_name") or "").strip() or (cp.name or "")
    customer_represented_by = (cd.get("customer_represented_by") or "").strip() or _director_genitive(cp.director or "")
    customer_represented_by_nominative = (cd.get("customer_represented_by_nominative") or "").strip() or (cp.director or "")
    price_val = cd["price"]
    customer_in_person_raw = (cd.get("customer_in_person") or "").strip()
    payment_terms_txt = payment_terms_text_for_doc(cd.get("payment_terms"))
    base = {
        "customer_name": customer_name,
        "customer_represented_by": customer_represented_by,
        "customer_represented_by_nominative": customer_represented_by_nominative,
        "customer_in_person": customer_in_person_raw,
        "dolznost": _dolznost_from_customer_in_person(customer_in_person_raw),
        "acting_on_basis": (cd.get("acting_on_basis") or "").strip(),
        "work_completion_period": (cd.get("work_completion_period") or "").strip(),
        "period_starts_from": (cd.get("period_starts_from") or "").strip(),
        "price": _format_price(price_val),
        "payment_terms": payment_terms_txt,
        "usl": payment_terms_txt,
        "ris": ris_text,
        "ris_head": "10. ОСОБЫЕ УСЛОВИЯ" if include_ris else "",
        "name": cd.get("name") or cp.name or "",
        "address": cd.get("address") or cp.address or "",
        "inn": cd.get("inn") or cp.inn or "",
        "kpp": cd.get("kpp") or cp.kpp or "",
        "ogrn": cd.get("ogrn") or cp.ogrn or "",
        "account": cd.get("account") or cp.account or "",
        "bank": cd.get("bank") or cp.bank or "",
        "bik": cd.get("bik") or cp.bik or "",
        "kor_account": cd.get("kor_account") or cp.kor_account or "",
        "email": cd.get("email") or cp.email or "",
        "room": cd.get("room") or tkp.room or "",
        "s": cd.get("s") or tkp.s or "",
        "text": (tkp.text or "").strip(),
    }
    base.update(contract_template_extras_for_ctx(cd, contract_template_file))
    return base


@require_http_methods(["POST"])
@csrf_exempt
@_max_auth_required
def max_contract_submit_view(request):
    """Сформировать договор из данных mini app."""
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    tkp_id = body.get("tkp_id")
    if not tkp_id:
        return JsonResponse({"error": "tkp_id required"}, status=400)
    try:
        tkp = TKPRecord.objects.get(pk=int(tkp_id))
    except Exception:
        return JsonResponse({"error": "TKP not found"}, status=404)

    if tkp.service == UNIVERSAL_TKP_SERVICE:
        return JsonResponse({"error": "Для универсального ТКП договор не формируется"}, status=400)

    is_complex_contract = tkp.service == "Комплексное ТКП"
    if is_complex_contract:
        contract_template_file = (body.get("complex_contract_type") or "").strip()
        if not contract_template_file:
            contract_template_file = (
                get_contract_template_for_complex_tkp(tkp.rows_json or []) or COMPLEX_CONTRACT_TEMPLATE_03
            )
    else:
        contract_template_file = SERVICE_TO_CONTRACT_TEMPLATE.get(tkp.service)
        if not contract_template_file:
            return JsonResponse({"error": f"No contract template for service '{tkp.service}'"}, status=400)

    mutable = dict(body)
    mutable.setdefault("date", tkp.date.strftime("%Y-%m-%d"))
    mutable.setdefault("price", str(tkp.sum_total or 0))
    mutable.setdefault("payment_terms", PAYMENT_TERMS_CHOICE_2)
    mutable.setdefault("poryadok", PORYADOK_CHOICE_1)
    mutable.setdefault("dney", 20)
    mutable.setdefault("room", tkp.room or "")
    mutable.setdefault("s", tkp.s or "")
    mutable.setdefault("complex_contract_type", contract_template_file if is_complex_contract else "")
    form = ContractForm(mutable)
    if not form.is_valid():
        return JsonResponse({"error": "Validation failed", "form_errors": form.errors}, status=400)
    cd = form.cleaned_data
    cp = cd["counterparty"]
    date_obj = cd["date"]
    seq = _get_next_contract_seq_for_date(date_obj)
    contract_number = f"{date_obj:%d%m%Y}_{seq}"
    ctx = {
        "contract_number": contract_number,
        "number": contract_number,
        "date": date_obj.strftime("%d.%m.%Y"),
        **_build_contract_context(cd, cp, tkp, contract_template_file),
    }
    templates_dir = Path(getattr(settings, "TEMPLATES_DOCX_DIR", Path(settings.BASE_DIR) / "templates_docx"))
    template_path = templates_dir / CONTRACT_TEMPLATES_SUBDIR / contract_template_file
    if not template_path.exists():
        return JsonResponse({"error": f"Contract template not found: {contract_template_file}"}, status=404)

    out_dir = Path(getattr(settings, "TKP_OUTPUT_DIR", settings.BASE_DIR / "TKP_output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    file_base = f"Дог_{contract_number}"
    docx_path = out_dir / f"{file_base}.docx"
    pdf_path = out_dir / f"{file_base}.pdf"

    doc = DocxTemplate(str(template_path))
    doc.render(ctx)
    doc.save(str(docx_path))
    if (
        is_complex_contract
        and tkp.rows_json
        and contract_template_file in COMPLEX_CONTRACTS_WITH_SPEC_TABLE
    ):
        rows_ctx, total_fmt = _complex_rows_json_to_ctx(tkp.rows_json)
        table_doc = _build_complex_table_document(rows_ctx, total_fmt)
        _insert_table_into_docx(str(docx_path), table_doc, CONTRACT_SPEC_TABLE_PLACEHOLDER)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        shutil.copy2(docx_path, tmpdir / "contract.docx")
        _convert_docx_to_pdf(tmpdir / "contract.docx", tmpdir)
        src = tmpdir / "contract.pdf"
        if not src.exists():
            src = tmpdir / "tkp.pdf"
        if not src.exists():
            first = next(tmpdir.glob("*.pdf"), None)
            src = first if first else src
        if src and src.exists():
            shutil.copy2(src, pdf_path)

    ContractRecord.objects.create(
        date=date_obj,
        number=contract_number,
        status=ContractRecord.STATUS_FINAL,
        tkp=tkp,
        counterparty=cp,
        client=tkp.client or "",
        service=tkp.service or "",
        sum_total=cd["price"],
        docx_file=file_base,
        pdf_file=file_base,
        contract_snapshot=ctx,
        created_by=None,
    )
    return JsonResponse(
        {
            "ok": True,
            "contract_number": contract_number,
            "base_name": file_base,
            "download_docx": f"/max/api/download/docx/?f={file_base}",
            "download_pdf": f"/max/api/download/pdf/?f={file_base}",
        }
    )


@require_http_methods(["GET"])
@csrf_exempt
@_max_auth_required
def max_download_view(request, file_type):
    """Скачать PDF или DOCX по base_name."""
    base_name = request.GET.get("f", "").strip()
    if not base_name or file_type not in ("pdf", "docx"):
        raise Http404()
    if not re.match(r"^[a-zA-Z0-9_+\-\u0400-\u04FF\u00AB\u00BB\u2116]+$", base_name):
        raise Http404()
    ext = "pdf" if file_type == "pdf" else "docx"
    path = _ensure_tkp_output_path(base_name, ext)
    if not path:
        raise Http404()
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name)
