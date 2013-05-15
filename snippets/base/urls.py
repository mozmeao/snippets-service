from django.conf.urls.defaults import patterns, url

from snippets.base import views


urlpatterns = patterns('',
    url(r'^/?$', views.index, name='snippets.base.index'),
    url(r'^(?P<startpage_version>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)/'
        '(?P<appbuildid>[^/]+)/(?P<build_target>[^/]+)/(?P<locale>[^/]+)/'
        '(?P<channel>[^/]+)/(?P<os_version>[^/]+)/(?P<distribution>[^/]+)/'
        '(?P<distribution_version>[^/]+)/$', views.fetch_snippets,
        name='view_snippets'),
)
