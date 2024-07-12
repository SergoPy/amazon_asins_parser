from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .tasks import start_asins_monitoring
from .settings import FE_PASSWORD, scrapyd, VERIFY
from .utils import create_tables_manager, asins_scraper_manager, \
    get_client_ip, search_term_report_manager, run_asins_monitoring, run_campaign_upload, run_advertising_monitoring
from .validators import validate_asins_monitoring_request, term_report_validator_request,\
    campaign_upload_validator, validate_advertising_monitoring_requests


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def login_view(request):
    ip = get_client_ip(request)
    start_asins_monitoring()
    if request.method == 'GET':
        if ip not in VERIFY:
            content = {
                'password_status': 'No password entered'
            }
            return render(request, 'login_page.html', context=content)
        else:
            return redirect('scraper_interface')
    else:
        data = request.POST
        password = data.get('password')
        if password == FE_PASSWORD:
            VERIFY.add(ip)  # TODO: refactor this shit the fuck out
            return redirect('scraper_interface')
        else:
            content = {
                'password_status': 'Wrong password, try again'
            }
            return render(request, 'login_page.html', context=content)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def scrape_view(request):
    if request.method == 'GET':
        ip = get_client_ip(request)
        if ip not in VERIFY:
            return redirect('login_page')

        context = {
            'MEDIA_URL': settings.MEDIA_URL,
            'MEDIA_ROOT': settings.MEDIA_ROOT
        }
    else:
        data = request.POST
        files = request.FILES
        if campaign_upload_validator(data, files):
            run_campaign_upload(data, files)
        asins_scraper_manager(data, scrapyd)
        filenames = create_tables_manager(data)

        context = {
            'MEDIA_URL': settings.MEDIA_URL,
            'MEDIA_ROOT': settings.MEDIA_ROOT,
            'filenames': filenames,
        }

    return render(request, 'scraper_interface.html', context=context)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def monitoring_view(request):
    if request.method == 'GET':
        ip = get_client_ip(request)
        if ip not in VERIFY:
            return redirect('login_page')
        context = {}
    else:
        data = request.POST
        files = request.FILES
        filenames = []

        if validate_asins_monitoring_request(data):
            run_asins_monitoring(data, scrapyd)
        if validate_advertising_monitoring_requests(data):
            run_advertising_monitoring(data, scrapyd)
        if term_report_validator_request(files):
            term_report = search_term_report_manager(data, files)
            filenames.append(term_report)
        context = {
            'MEDIA_URL': settings.MEDIA_URL,
            'MEDIA_ROOT': settings.MEDIA_ROOT,
            'filenames': filenames,
        }

    return render(request, 'monitoring_page.html', context=context)
