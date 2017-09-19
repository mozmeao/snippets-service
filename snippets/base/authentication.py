from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.backends import ModelBackend


class AuthBackend(OIDCAuthenticationBackend, ModelBackend):
    pass
