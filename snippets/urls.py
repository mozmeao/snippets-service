from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.views.generic import RedirectView
from django.views.static import serve as static_serve
from django.urls import include, path, re_path


def robots_txt(request):
    permission = 'Allow' if settings.ENGAGE_ROBOTS else 'Disallow'
    return HttpResponse('User-agent: *\n{0}: /'.format(permission), content_type='text/plain')


urlpatterns = [
    path('', include('snippets.base.urls')),
    path('robots.txt', robots_txt),

    # contribute.json url
    re_path(r'^(?P<path>contribute\.json)$', static_serve, {'document_root': settings.ROOT}),
]

if settings.ENABLE_ADMIN:
    urlpatterns += [
        path('admin/', admin.site.urls),
    ]
    admin.site.site_header = settings.SITE_HEADER
    admin.site.site_title = settings.SITE_TITLE

elif settings.ADMIN_REDIRECT_URL:
    urlpatterns.append(
        path('admin/', RedirectView.as_view(url=settings.ADMIN_REDIRECT_URL))
    )

if settings.OIDC_ENABLE:
    import mozilla_django_oidc
    urlpatterns.append(path('oidc/', mozilla_django_oidc.urls))

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Use custom serve function that adds necessary headers.
    def serve_media(*args, **kwargs):
        response = static_serve(*args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        if settings.BUNDLE_BROTLI_COMPRESS:
            response['Content-Encoding'] = 'br'
        return response

    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media, {'document_root': settings.MEDIA_ROOT}),
    ] + staticfiles_urlpatterns()
