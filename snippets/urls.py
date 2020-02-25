from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic import RedirectView
from django.views.static import serve as static_serve
from django.shortcuts import render
from django.urls import include, path, re_path

import sentry_sdk
from ratelimit.exceptions import Ratelimited


def robots_txt(request):
    permission = 'Allow' if settings.ENGAGE_ROBOTS else 'Disallow'
    return HttpResponse('User-agent: *\n{0}: /'.format(permission), content_type='text/plain')


def handler403(request, exception=None):
    if isinstance(exception, Ratelimited):
        with sentry_sdk.configure_scope() as scope:
            scope.level = 'info'
            scope.set_tag('logger', 'ratelimited')
            sentry_sdk.capture_message(message='Rate limited')
        return render(request, template_name='base/ratelimited.jinja', status=429)
    return HttpResponseForbidden('Forbidden')


urlpatterns = [
    path('', include('snippets.base.urls')),
    path('robots.txt', robots_txt),

    # Favicon
    re_path(r'^(?P<path>favicon\.ico)$', static_serve, {'document_root': settings.STATIC_ROOT}),
    # contribute.json url
    re_path(r'^(?P<path>contribute\.json)$', static_serve, {'document_root': settings.ROOT}),
]

if settings.ENABLE_ADMIN:
    urlpatterns += [
        re_path(r'^taggit/', include('taggit_selectize.urls')),
        path('admin/', admin.site.urls),
    ]
    admin.site.site_header = settings.SITE_HEADER
    admin.site.site_title = settings.SITE_TITLE

elif settings.ADMIN_REDIRECT_URL:
    urlpatterns.append(
        path('admin/', RedirectView.as_view(url=f'{settings.ADMIN_REDIRECT_URL}/admin/'))
    )

if settings.OIDC_ENABLE:
    urlpatterns.append(path('oidc/', include('mozilla_django_oidc.urls')))

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Use custom serve function that adds necessary headers.
    def serve_media(*args, **kwargs):
        response = static_serve(*args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        if (settings.BUNDLE_BROTLI_COMPRESS and (
                kwargs['path'].startswith(settings.MEDIA_BUNDLES_ROOT) or
                kwargs['path'].startswith(settings.MEDIA_BUNDLES_PREGEN_ROOT))):
            response['Content-Encoding'] = 'br'
        return response

    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media, {'document_root': settings.MEDIA_ROOT}),
    ] + staticfiles_urlpatterns()
