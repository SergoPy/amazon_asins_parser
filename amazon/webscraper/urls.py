"""webscraper URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect

from . import views

urlpatterns = [
    path('v2/admin/', admin.site.urls),
    path('v2/', csrf_exempt(views.login_view), name='login_page'),
    path('v2/signup/', csrf_exempt(views.register_view), name='register_page'),
    path('v2/controlpanel/', csrf_exempt(views.scrape_view), name='scraper_interface'),
    path('v2/monitoring/', csrf_exempt(views.monitoring_view), name='monitoring'),
    path('v2/logout/', csrf_exempt(views.logout_view), name='logout'),
     path('v2/statistic/', csrf_exempt(views.serve_statistic), name='serve_statistic'),
    path('', lambda request: redirect('login_page')),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
