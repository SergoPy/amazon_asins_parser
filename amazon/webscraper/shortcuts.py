from django.conf import settings
from django.shortcuts import render


def render_with_staticfiles(request, template_name):
    context = {
        'MEDIA_URL': settings.MEDIA_URL,
    }

    return render(request, template_name, context=context)
