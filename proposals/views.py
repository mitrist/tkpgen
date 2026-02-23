import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from docxtpl import DocxTemplate

from .forms import ComplexProposalForm, ProposalForm, TariffForm
from .models import Region, RegionServicePrice, Service, TKPRecord

COMPLEX_TEMPLATE_NAME = 'Шаблон 9 Комплексное ТКП.docx'
UNIT_DISPLAY = {'m2': 'м²', 'piece': 'шт'}


def _get_libreoffice_path():
    """Путь к LibreOffice: на Windows ищем soffice.exe в стандартных каталогах."""
    if sys.platform == 'win32':
        for base in (os.environ.get('ProgramFiles', 'C:\\Program Files'),
                     os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')):
            exe = Path(base) / 'LibreOffice' / 'program' / 'soffice.exe'
            if exe.exists():
                return str(exe)
    return 'libreoffice'


def _convert_docx_to_pdf(docx_path, out_dir):
    """Конвертация docx в PDF: LibreOffice (Linux/Windows) или docx2pdf (Windows + MS Word)."""
    docx_path = Path(docx_path)
    out_dir = Path(out_dir)
    cmd = _get_libreoffice_path()
    if sys.platform == 'win32' and cmd == 'libreoffice':
        try:
            from docx2pdf import convert as docx2pdf_convert
            docx2pdf_convert(str(docx_path), str(out_dir / 'tkp.pdf'))
            return
        except ImportError:
            raise FileNotFoundError(
                'На Windows нужен LibreOffice или пакет docx2pdf (pip install docx2pdf, требуется MS Word). '
                'Установите LibreOffice или выполните: pip install docx2pdf'
            )
    subprocess.run(
        [cmd, '--headless', '--convert-to', 'pdf', '--outdir', str(out_dir), str(docx_path)],
        check=True,
    )


def _sanitize_filename(name):
    """Очистка строки для использования в имени файла."""
    if not name or not name.strip():
        return 'client'
    s = name.strip()
    s = re.sub(r'[\s]+', '_', s)
    s = re.sub(r'[\\/:*?"<>|]', '', s)
    return s[:100] if s else 'client'


def _get_next_seq_for_date(date_obj):
    """Порядковый номер ТКП на указанную дату."""
    count = TKPRecord.objects.filter(date=date_obj).count()
    return count + 1


def _format_price(value):
    """Форматирование цены с разделителями тысяч (1 000 000)."""
    if value is None:
        return ''
    s = str(int(value))
    n = len(s)
    if n <= 3:
        return s
    r = n % 3 or 3
    result = s[:r]
    for i in range(r, n, 3):
        result += ' ' + s[i:i + 3]
    return result


@require_http_methods(['GET', 'POST'])
def form_view(request):
    """Шаг 1: форма ввода параметров ТКП."""
    if request.method == 'POST':
        form = ProposalForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            service = data['service']
            s = data.get('s') or 0
            if data.get('is_internal'):
                price_value = data.get('internal_price') or 0
                region_name = ''
            else:
                region = data['region']
                try:
                    rsp = RegionServicePrice.objects.get(region=region, service=service)
                    price_value = rsp.unit_price * s
                except RegionServicePrice.DoesNotExist:
                    messages.error(
                        request,
                        f'Не найдена цена для региона "{region.name}" и услуги "{service.name}". '
                        'Выполните: python manage.py init_services --clear, затем python manage.py load_region_prices',
                    )
                    return render(request, 'proposals/form.html', {
                        'form': form,
                        'service_units_json': json.dumps({str(s.pk): s.unit_type for s in Service.objects.all()}),
                    })
                region_name = region.name
            client_value = (
                (data['internal_client'] or '').strip()
                if data.get('is_internal')
                else (data['client'] or '')
            )
            request.session['proposal_data'] = {
                'date': data['date'].strftime('%Y-%m-%d'),
                'service_id': service.pk,
                'service_name': service.name,
                'city': region_name,
                'price': str(price_value),
                'client': client_value,
                'room': data['room'] or '',
                'srok': data['srok'] or '',
                'text': data['text'] or '',
                's': '' if data.get('is_internal') else str(s),
            }
            return redirect('proposals:confirm')
    else:
        form = ProposalForm()

    service_units = {str(s.pk): s.unit_type for s in Service.objects.all()}
    return render(request, 'proposals/form.html', {
        'form': form,
        'service_units_json': json.dumps(service_units),
    })


@require_http_methods(['GET', 'POST'])
def confirm_view(request):
    """Шаг 2: подтверждение и скачивание PDF."""
    data = request.session.get('proposal_data')
    if not data:
        return redirect('proposals:form')

    if request.method == 'POST':
        try:
            base_name = _generate_and_save_files(data)
        except Exception as e:
            messages.error(request, f'Ошибка генерации: {e}')
            return redirect('proposals:confirm')
        if base_name:
            _save_tkp_record(data)
            request.session['tkp_download_base'] = base_name
            return redirect('proposals:download_success')
        messages.error(
            request,
            'Ошибка генерации. Проверьте, что шаблоны .docx есть в папке templates_docx/'
        )
        return redirect('proposals:confirm')

    from datetime import datetime
    date_display = datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
    price_display = _format_price(Decimal(data['price']))

    context = {
        'date': date_display,
        'service_name': data['service_name'],
        'city': data['city'],
        'price': price_display,
        'price_raw': data['price'],
        'client': data['client'],
        'room': data.get('room', ''),
        'srok': data.get('srok', ''),
        'text': data['text'],
        's': data['s'],
    }
    return render(request, 'proposals/confirm.html', context)


@require_http_methods(['GET'])
def download_success_view(request):
    """Страница после формирования ТКП: ссылки на скачивание PDF и DOCX."""
    base_name = request.session.pop('tkp_download_base', None)
    if not base_name:
        return redirect('proposals:form')
    context = {
        'base_name': base_name,
        'pdf_name': f'{base_name}.pdf',
        'docx_name': f'{base_name}.docx',
    }
    return render(request, 'proposals/download_success.html', context)


@require_http_methods(['GET'])
def download_file_view(request, file_type):
    """Отдача PDF или DOCX по base_name из GET-параметра (для скачивания после формирования)."""
    base_name = request.GET.get('f', '').strip()
    if not base_name or file_type not in ('pdf', 'docx'):
        raise Http404()
    if not re.match(r'^[a-zA-Z0-9_\-\u0400-\u04FF]+$', base_name):
        raise Http404()
    out_dir = Path(getattr(settings, 'TKP_OUTPUT_DIR', settings.BASE_DIR / 'TKP_output'))
    ext = 'pdf' if file_type == 'pdf' else 'docx'
    path = out_dir / f'{base_name}.{ext}'
    if not path.exists():
        raise Http404()
    return FileResponse(
        open(path, 'rb'),
        as_attachment=True,
        filename=path.name,
    )


def _parse_complex_rows(rows_data):
    """
    Валидация и разбор строк комплексного ТКП из JSON.
    Возвращает (list of dicts, error_message).
    Каждый dict: service_name, unit, quantity, price_per_unit, total (Decimal).
    """
    if not rows_data:
        return [], 'Добавьте хотя бы одну строку'
    try:
        rows = json.loads(rows_data) if isinstance(rows_data, str) else rows_data
    except (json.JSONDecodeError, TypeError):
        return [], 'Неверный формат данных строк'
    if not isinstance(rows, list) or len(rows) == 0:
        return [], 'Добавьте хотя бы одну строку'
    result = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        name = (r.get('service_name') or '').strip()
        unit = (r.get('unit') or 'm2').strip() in ('piece', 'шт') and 'piece' or 'm2'
        try:
            qty = Decimal(str(r.get('quantity') or 0))
            price = Decimal(str(r.get('price_per_unit') or 0))
        except Exception:
            continue
        if qty < 0 or price < 0:
            continue
        total = (qty * price).quantize(Decimal('0.01'))
        result.append({
            'service_name': name or f'Позиция {i + 1}',
            'unit': unit,
            'quantity': qty,
            'price_per_unit': price,
            'total': total,
        })
    if not result:
        return [], 'Заполните хотя бы одну строку (наименование, количество, цена)'
    return result, None


@require_http_methods(['GET', 'POST'])
def complex_form_view(request):
    """Форма комплексного ТКП: дата, клиент, срок, таблица строк."""
    if request.method == 'POST':
        form = ComplexProposalForm(request.POST)
        rows_data = request.POST.get('rows_json', '')
        rows, row_error = _parse_complex_rows(rows_data)
        if form.is_valid() and not row_error:
            # Сессия сериализуется в JSON — храним числа как строки
            rows_serializable = [
                {
                    'service_name': r['service_name'],
                    'unit': r['unit'],
                    'quantity': str(r['quantity']),
                    'price_per_unit': str(r['price_per_unit']),
                    'total': str(r['total']),
                }
                for r in rows
            ]
            data = {
                'date': form.cleaned_data['date'].strftime('%Y-%m-%d'),
                'client': (form.cleaned_data['client'] or '').strip(),
                'srok': form.cleaned_data.get('srok') or '',
                'rows': rows_serializable,
                'text1': (form.cleaned_data.get('text1') or '').strip(),
                'text2': (form.cleaned_data.get('text2') or '').strip(),
            }
            request.session['complex_proposal_data'] = data
            return redirect('proposals:complex_confirm')
        if row_error:
            messages.error(request, row_error)
    else:
        form = ComplexProposalForm()
    return render(request, 'proposals/complex_form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def complex_confirm_view(request):
    """Подтверждение комплексного ТКП и генерация docx/pdf."""
    data = request.session.get('complex_proposal_data')
    if not data:
        return redirect('proposals:complex_form')

    if request.method == 'POST':
        try:
            base_name = _generate_complex_and_save_files(data)
        except Exception as e:
            messages.error(request, f'Ошибка генерации: {e}')
            return redirect('proposals:complex_confirm')
        if base_name:
            _save_complex_tkp_record(data)
            request.session['tkp_download_base'] = base_name
            return redirect('proposals:download_success')
        messages.error(request, 'Ошибка генерации. Проверьте шаблон в templates_docx/')
        return redirect('proposals:complex_confirm')

    date_display = datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
    total_sum = sum(Decimal(str(r['total'])) for r in data['rows'])
    rows_display = []
    for i, r in enumerate(data['rows'], 1):
        rows_display.append({
            'num': i,
            'service_name': r['service_name'],
            'unit_display': UNIT_DISPLAY.get(r['unit'], r['unit']),
            'quantity': r['quantity'],
            'price_per_unit': r['price_per_unit'],
            'total': _format_price(Decimal(str(r['total']))),
        })
    context = {
        'date': date_display,
        'client': data['client'],
        'srok': data.get('srok', ''),
        'rows': rows_display,
        'total_sum': _format_price(total_sum),
        'text1': data.get('text1', ''),
        'text2': data.get('text2', ''),
    }
    return render(request, 'proposals/complex_confirm.html', context)


TKP_TABLE_PLACEHOLDER = '___TKP_TABLE_INSERT___'


def _set_table_borders(table, sz='4', val='single', color='000000'):
    """Включает границы таблицы через tblBorders (вся таблица)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tblPr = table._tbl.tblPr
    tblBorders = tblPr.find(qn('w:tblBorders'))
    if tblBorders is None:
        tblBorders = OxmlElement('w:tblBorders')
        tblPr.append(tblBorders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = tblBorders.find(qn(f'w:{edge}'))
        if el is None:
            el = OxmlElement(f'w:{edge}')
            tblBorders.append(el)
        el.set(qn('w:val'), val)
        el.set(qn('w:sz'), sz)
        el.set(qn('w:color'), color)


def _build_complex_table_document(rows_ctx, total_sum_formatted):
    """Создаёт Document с одной таблицей позиций (для вставки в основной docx)."""
    from docx import Document
    doc = Document()
    table = doc.add_table(rows=len(rows_ctx) + 2, cols=6)  # заголовок + строки + итого
    _set_table_borders(table)
    header = table.rows[0].cells
    headers_text = ('№', 'Наименование услуги', 'Ед. изм.', 'Количество', 'Цена за ед.', 'Стоимость')
    for i, text in enumerate(headers_text):
        header[i].text = text
        for run in header[i].paragraphs[0].runs:
            run.bold = True
    for i, r in enumerate(rows_ctx, 1):
        row_cells = table.rows[i].cells
        row_cells[0].text = str(r['num'])
        row_cells[1].text = r['service_name']
        row_cells[2].text = r['unit_display']
        row_cells[3].text = r['quantity']
        row_cells[4].text = r['price_per_unit']
        row_cells[5].text = r['total_formatted']
    last = table.rows[len(rows_ctx) + 1].cells
    last[0].merge(last[5])
    last[0].text = f"Итого: {total_sum_formatted} ₽"
    return doc


def _insert_table_into_docx(docx_path, table_doc):
    """Находит в docx абзац с плейсхолдером и заменяет его на таблицу."""
    from copy import deepcopy
    from docx import Document
    doc = Document(str(docx_path))
    placeholder = TKP_TABLE_PLACEHOLDER
    for p in doc.paragraphs:
        if placeholder in p.text:
            table = table_doc.tables[0]
            table_elem = deepcopy(table._tbl)
            p._p.addnext(table_elem)
            p._p.getparent().remove(p._p)
            doc.save(str(docx_path))
            return
    # если абзац не найден, таблица не вставляется (шаблон без плейсхолдера)


def _generate_complex_and_save_files(data):
    """Генерация docx по шаблону комплексного ТКП, конвертация в PDF, сохранение. Возвращает base_name."""
    templates_dir = getattr(settings, 'TEMPLATES_DOCX_DIR', Path(settings.BASE_DIR) / 'templates_docx')
    template_path = templates_dir / COMPLEX_TEMPLATE_NAME
    if not template_path.exists():
        return None

    date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
    date_display = date_obj.strftime('%d.%m.%Y')
    seq = _get_next_seq_for_date(date_obj)
    number = f'{date_obj:%d%m%Y}_{seq}'

    total_sum = sum(Decimal(str(r['total'])) for r in data['rows'])
    total_sum_formatted = _format_price(total_sum)
    rows_ctx = []
    for i, r in enumerate(data['rows'], 1):
        rows_ctx.append({
            'num': i,
            'service_name': r['service_name'],
            'unit_display': UNIT_DISPLAY.get(r['unit'], r['unit']),
            'quantity': str(r['quantity']),
            'price_per_unit': _format_price(Decimal(str(r['price_per_unit']))),
            'total_formatted': _format_price(Decimal(str(r['total']))),
        })

    default_row = {
        'num': '', 'service_name': '', 'unit_display': '',
        'quantity': '', 'price_per_unit': '', 'total_formatted': '',
    }
    # text1, text2 — опционально; в шаблоне {{ text1 }} / {{ text2 }} (пустые не выводятся)
    context = {
        'date': date_display,
        'client': data['client'],
        'srok': data.get('srok', ''),
        'number': number,
        'total_sum_formatted': total_sum_formatted,
        'row': default_row,
        'rows': rows_ctx,
        'rows_table_placeholder': TKP_TABLE_PLACEHOLDER,
        'text1': data.get('text1') or '',
        'text2': data.get('text2') or '',
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        docx_path = tmpdir / 'tkp.docx'
        pdf_path = tmpdir / 'tkp.pdf'
        doc = DocxTemplate(str(template_path))
        doc.render(context)
        doc.save(str(docx_path))
        table_doc = _build_complex_table_document(rows_ctx, total_sum_formatted)
        _insert_table_into_docx(docx_path, table_doc)
        _convert_docx_to_pdf(docx_path, pdf_path.parent)
        client_safe = _sanitize_filename(data.get('client') or '')
        base_name = f'{client_safe}_{date_obj:%d%m%Y}_{seq}'
        out_dir = Path(getattr(settings, 'TKP_OUTPUT_DIR', settings.BASE_DIR / 'TKP_output'))
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, out_dir / f'{base_name}.pdf')
        shutil.copy2(docx_path, out_dir / f'{base_name}.docx')
        return base_name


def _save_complex_tkp_record(data):
    """Сохранение записи о сформированном комплексном ТКП."""
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
    seq = _get_next_seq_for_date(date_obj)
    number = _generate_doc_number(data.get('client') or '', date_obj, seq)
    total_sum = sum(Decimal(str(r['total'])) for r in data['rows'])
    TKPRecord.objects.create(
        date=date_obj,
        number=number,
        client=data.get('client') or '',
        service='Комплексное ТКП',
        sum_total=total_sum,
    )


@require_http_methods(['GET'])
def table_view(request):
    """Страница перечня сформированных ТКП с фильтрами по каждому столбцу."""
    records = TKPRecord.objects.all()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    number = request.GET.get('number', '').strip()
    client = request.GET.get('client', '').strip()
    service = request.GET.get('service', '').strip()
    sum_min = request.GET.get('sum_min', '').strip()
    sum_max = request.GET.get('sum_max', '').strip()
    if date_from:
        try:
            d = datetime.strptime(date_from, '%Y-%m-%d').date()
            records = records.filter(date__gte=d)
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.strptime(date_to, '%Y-%m-%d').date()
            records = records.filter(date__lte=d)
        except ValueError:
            pass
    if number:
        records = records.filter(number__icontains=number)
    if client:
        records = records.filter(client__icontains=client)
    if service:
        records = records.filter(service=service)
    if sum_min:
        try:
            records = records.filter(sum_total__gte=Decimal(sum_min.replace(',', '.')))
        except (ValueError, Exception):
            pass
    if sum_max:
        try:
            records = records.filter(sum_total__lte=Decimal(sum_max.replace(',', '.')))
        except (ValueError, Exception):
            pass
    services = list(TKPRecord.objects.values_list('service', flat=True).distinct().order_by('service'))
    context = {
        'records': records,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'number': number,
            'client': client,
            'service': service,
            'sum_min': sum_min,
            'sum_max': sum_max,
        },
        'services_list': services,
    }
    return render(request, 'proposals/table.html', context)


@require_http_methods(['GET', 'POST'])
def tariffs_view(request):
    """Редактирование тарифов по регионам: список пар Услуга–Регион и форма добавления."""
    if request.method == 'POST':
        delete_id = request.POST.get('delete_id')
        if delete_id:
            try:
                RegionServicePrice.objects.filter(pk=delete_id).delete()
                messages.success(request, 'Тариф удалён.')
            except Exception:
                pass
            return redirect('proposals:tariffs')
        form = TariffForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            service = data['service']
            new_name = (data.get('new_region_name') or '').strip()
            if new_name:
                region, _ = Region.objects.get_or_create(name=new_name, defaults={})
            else:
                region = data['region']
            RegionServicePrice.objects.update_or_create(
                region=region,
                service=service,
                defaults={'unit_price': data['unit_price']},
            )
            messages.success(request, f'Тариф сохранён: {service.name} — {region.name}.')
            return redirect('proposals:tariffs')
    else:
        form = TariffForm()
    tariffs_list = RegionServicePrice.objects.select_related('region', 'service').order_by('region__name', 'service__name')
    context = {'form': form, 'tariffs_list': tariffs_list}
    return render(request, 'proposals/tariffs.html', context)


def _generate_doc_number(client, date_obj, seq):
    """Генерация номера документа: client_DDMMYYYY_N."""
    client_safe = _sanitize_filename(client or '')
    date_str = date_obj.strftime('%d%m%Y')
    return f'{client_safe}_{date_str}_{seq}'


def _save_tkp_record(data):
    """Сохранение записи о сформированном ТКП."""
    from datetime import datetime
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
    seq = _get_next_seq_for_date(date_obj)
    number = _generate_doc_number(data.get('client') or '', date_obj, seq)
    TKPRecord.objects.create(
        date=date_obj,
        number=number,
        client=data.get('client') or '',
        service=data['service_name'],
        sum_total=Decimal(data['price']),
    )


def _generate_and_save_files(data):
    """Генерация docx, конвертация в PDF, сохранение обоих в TKP_output. Возвращает base_name файлов."""
    try:
        service = Service.objects.get(pk=data['service_id'])
    except Service.DoesNotExist:
        return None

    templates_dir = getattr(settings, 'TEMPLATES_DOCX_DIR', Path(settings.BASE_DIR) / 'templates_docx')
    template_path = templates_dir / service.template_file

    if not template_path.exists():
        return None

    from datetime import datetime
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
    date_display = date_obj.strftime('%d.%m.%Y')
    seq = _get_next_seq_for_date(date_obj)
    number = f'{date_obj:%d%m%Y}_{seq}'

    price_val = Decimal(data['price'])

    context = {
        'city': data.get('city', ''),
        'price': _format_price(price_val),
        'date': date_display,
        'client': data['client'] or '',
        'room': data.get('room') or '',
        'srok': data.get('srok') or '',
        'text': data['text'] or '',
        's': data.get('s') or '',
        'number': number,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        docx_path = tmpdir / 'tkp.docx'
        pdf_path = tmpdir / 'tkp.pdf'

        doc = DocxTemplate(str(template_path))
        doc.render(context)
        doc.save(str(docx_path))

        _convert_docx_to_pdf(docx_path, pdf_path.parent)

        client_safe = _sanitize_filename(data.get('client') or '')
        base_name = f'{client_safe}_{date_obj:%d%m%Y}_{seq}'
        out_dir = Path(getattr(settings, 'TKP_OUTPUT_DIR', settings.BASE_DIR / 'TKP_output'))
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, out_dir / f'{base_name}.pdf')
        shutil.copy2(docx_path, out_dir / f'{base_name}.docx')
        return base_name
