import json
import re
import subprocess
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from docxtpl import DocxTemplate

from .forms import ProposalForm
from .models import RegionServicePrice, Service, TKPRecord


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
                        'Загрузите справочник: python manage.py load_region_prices',
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
            pdf_path = _generate_pdf(data)
        except Exception as e:
            messages.error(request, f'Ошибка генерации PDF: {e}')
            return redirect('proposals:confirm')
        if pdf_path and pdf_path.exists():
            _save_tkp_record(data)
            response = FileResponse(
                open(pdf_path, 'rb'),
                as_attachment=True,
                filename=Path(pdf_path).name,
            )
            try:
                pdf_path.unlink(missing_ok=True)
            except OSError:
                pass
            return response
        messages.error(
            request,
            'Ошибка генерации PDF. Проверьте, что шаблоны .docx есть в папке templates_docx/'
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
def table_view(request):
    """Страница перечня сформированных ТКП."""
    records = TKPRecord.objects.all()
    context = {'records': records}
    return render(request, 'proposals/table.html', context)


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


def _generate_pdf(data):
    """Генерация docx и конвертация в PDF. Возвращает путь к PDF."""
    try:
        service = Service.objects.get(pk=data['service_id'])
    except Service.DoesNotExist:
        return None

    templates_dir = getattr(settings, 'TEMPLATES_DOCX_DIR', Path(settings.BASE_DIR) / 'templates_docx')
    template_path = templates_dir / service.template_file

    if not template_path.exists():
        return None

    from datetime import datetime
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
    date_display = date_obj.strftime('%d.%m.%Y')

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
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        docx_path = tmpdir / 'tkp.docx'
        pdf_path = tmpdir / 'tkp.pdf'

        doc = DocxTemplate(str(template_path))
        doc.render(context)
        doc.save(str(docx_path))

        subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'pdf',
             '--outdir', str(pdf_path.parent), str(docx_path)],
            check=True
        )

        date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        date_str = date_obj.strftime('%d%m%Y')  # 18022026
        seq = _get_next_seq_for_date(date_obj)
        client_safe = _sanitize_filename(data.get('client') or '')

        pdf_filename = f'{client_safe}_{date_str}_{seq}.pdf'
        result_path = Path(tempfile.gettempdir()) / pdf_filename
        import shutil
        shutil.copy2(pdf_path, result_path)
        return result_path
