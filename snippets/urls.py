from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.views.static import serve as static_serve

from funfactory.monkeypatches import patch


# Apply funfactory monkeypatches.
patch()

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


def robots_txt(request):
    permission = 'Allow' if settings.ENGAGE_ROBOTS else 'Disallow'
    return HttpResponse('User-agent: *\n{0}: /'.format(permission),
                        mimetype='text/plain')

urlpatterns = patterns('',
    url(r'', include('snippets.base.urls')),

    url(r'^admin/', include('smuggler.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^robots\.txt$', robots_txt)
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Use custom serve function that adds necessary headers.
    def serve_media(*args, **kwargs):
        response = static_serve(*args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response

    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', serve_media, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ) + staticfiles_urlpatterns()
