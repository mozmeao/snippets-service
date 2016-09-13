from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.views.generic import RedirectView
from django.views.static import serve as static_serve


def robots_txt(request):
    permission = 'Allow' if settings.ENGAGE_ROBOTS else 'Disallow'
    return HttpResponse('User-agent: *\n{0}: /'.format(permission), content_type='text/plain')

urlpatterns = [
    url(r'', include('snippets.base.urls')),
    url(r'^robots\.txt$', robots_txt),

    # contribute.json url
    url(r'^(?P<path>contribute\.json)$', 'django.views.static.serve',
        {'document_root': settings.ROOT}),
]


if settings.ENABLE_ADMIN:
    urlpatterns += [
        url(r'^admin/', include(admin.site.urls)),
    ]
    admin.site.site_header = 'Snippets Administration'
    admin.site.site_title = 'Mozilla Snippets'
elif settings.ADMIN_REDIRECT_URL:
    urlpatterns.append(
        url(r'^admin/', RedirectView.as_view(url=settings.ADMIN_REDIRECT_URL))
    )

if settings.SAML_ENABLE:
    urlpatterns += [
        url(r'^saml2/', include('snippets.saml.urls'))
        ]


# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Use custom serve function that adds necessary headers.
    def serve_media(*args, **kwargs):
        response = static_serve(*args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response

    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve_media, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ] + staticfiles_urlpatterns()
