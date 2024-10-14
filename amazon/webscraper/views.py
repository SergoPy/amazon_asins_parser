from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib.auth.decorators import user_passes_test
import os

from .tasks import start_asins_monitoring
from .settings import FE_PASSWORD, scrapyd, VERIFY
from .utils import create_tables_manager, asins_scraper_manager, get_campaigns, \
    get_client_ip, search_term_report_manager, run_asins_monitoring, run_campaign_upload, run_advertising_monitoring
from .validators import validate_asins_monitoring_request, term_report_validator_request, \
    campaign_upload_validator, validate_advertising_monitoring_requests

DEFAULT_CAMPAIGN_TYPES = {'seed': 'Seed', 'str_low': 'Str Low', 'exact_other': 'Exact Other', 'variation': 'Variation', 'exact_top': 'Exact Top', 'exact': 'Exact',
                          'exact_low': 'Ecact Low', 'broad': 'Broad', 'brands': 'Brands', 'auto': 'Auto', 'category': 'Category'}


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def login_view(request):
    # ip = get_client_ip(request)
    # print(f"ip: {ip}")
    print(f"VERIFY: {VERIFY}")
    print(f"request.user.is_authenticated: {request.user.is_authenticated}")
    start_asins_monitoring()

    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('scraper_interface')
        else:
            content = {
                'password_status': 'No password entered'
            }
            return render(request, 'login_page.html', context=content)
    else:
        data = request.POST
        username = data.get('username')
        password = data.get('password')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if remember_me:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            # VERIFY.add(ip)
            print(f"VERIFY after: {VERIFY}")
            return redirect('scraper_interface')
        else:
            messages.error(request, 'Invalid login credentials')
            content = {
                'username': username,
            }
            return render(request, 'login_page.html', context=content)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if 'username' in form.errors:
            messages.error(
                request, form.errors['username'][0], extra_tags='username')
        if 'password1' in form.errors:
            messages.error(
                request, form.errors['password1'][0], extra_tags='password1')
        if 'password2' in form.errors:
            messages.error(
                request, form.errors['password2'][0], extra_tags='password2')
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            return redirect('login_page')
        else:
            content = {
                'data': request.POST
            }
            return render(request, 'register_page.html', context=content)
    else:
        form = UserCreationForm()
        return render(request, 'register_page.html', {'form': form})


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def scrape_view(request):
    # ip = get_client_ip(request)
    # print(f"ip: {ip}")
    print(f"VERIFY: {VERIFY}")
    print(f"request.user.is_authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        if request.method == 'GET':
            campaign_name = get_campaigns(request)
            context = {
                'MEDIA_URL': settings.MEDIA_URL,
                'MEDIA_ROOT': settings.MEDIA_ROOT,
                'campaign_names': campaign_name,
                'def_campaign': DEFAULT_CAMPAIGN_TYPES
            }
        else:
            data = request.POST
            files = request.FILES
            if campaign_upload_validator(data, files):
                run_campaign_upload(data, files)
            asins_scraper_manager(data, scrapyd)
            filenames = create_tables_manager(data, request)

            campaign_name = get_campaigns(request)
            context = {
                'MEDIA_URL': settings.MEDIA_URL,
                'MEDIA_ROOT': settings.MEDIA_ROOT,
                'filenames': filenames,
                'campaign_names': campaign_name,
                'def_campaign': DEFAULT_CAMPAIGN_TYPES
            }
        return render(request, 'scraper_interface.html', context=context)
    else:
        return redirect('login_page')


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def monitoring_view(request):
    # ip = get_client_ip(request)
    if request.user.is_authenticated:
        if request.method == 'GET':
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
    else:
        return redirect('login_page')


def logout_view(request):
    logout(request)
    return redirect('login_page')


def get_campaign_names(request):
    table_id = request.GET.get('table_id')
        # if table_id:
    if request.user.is_authenticated:
        campaign_names = ["its_work", "its_godd",
                          "all_pkey", "good_job", "upg", "okko", table_id]
        return JsonResponse({'campaign_names': campaign_names})
    return JsonResponse({'error': 'User not authenticated'}, status=401)


@user_passes_test(lambda u: u.is_superuser)
def serve_statistic(request):
    file_path = os.path.join(settings.MEDIA_ROOT, 'statistic.html')
    try:
        with open(file_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='text/html')
    except FileNotFoundError:
        raise Http404("Statistic file not found")
