from django.conf.urls import url

import views


urlpatterns = [
    url(r'^login/$', 'djangosaml2.views.login', name='saml2_login'),
    url(r'^acs/$', 'djangosaml2.views.assertion_consumer_service', name='saml2_acs'),
    url(r'^metadata/$', views.metadata, name='saml2_metadata'),
]
