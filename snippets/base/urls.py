from django.conf.urls.defaults import patterns, url

from snippets.base import views


urlpatterns = patterns('',
    url(r'^/?$', views.index, name='snippets.base.index'),
)
