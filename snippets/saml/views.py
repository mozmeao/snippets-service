from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import render


def metadata(request):
    expire = datetime.utcnow() + timedelta(hours=settings.SAML_CONFIG['valid_for'])
    context = {
        'saml_entity_id': settings.SAML_ENTITY_ID,
        'saml_sso_url': settings.SAML_SSO_URL,
        'expire': datetime.strftime(expire, '%Y-%m-%dT%H:%M:%SZ'),
    }
    return render(request, 'saml/metadata.xml', context, content_type='application/xml',)
