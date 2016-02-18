import os

import saml2
from decouple import config


DEBUG = config('DEBUG', cast=bool)
SAML_DIR = os.path.dirname(__file__)

LOGIN_URL = '/saml2/login/'
LOGIN_REDIRECT_URL = '/admin/'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

AUTHENTICATION_BACKENDS = (
    'djangosaml2.backends.Saml2Backend',
)

SAML_SSO_URL = config('SAML_SSO_URL')
SAML_ENTITY_ID = config('SAML_ENTITY_ID')
SAML_SP_NAME = config('SAML_SP_NAME', 'SP')
SAML_REMOTE_METADATA = os.path.join(
    SAML_DIR, config('SAML_REMOTE_METADATA', default='remote_metadata.xml'))
SAML_CREATE_UNKNOWN_USER = config('SAML_CREATE_USER', default=False, cast=bool)
SAML_ATTRIBUTE_MAPPING = {
    'uid': ('username', ),
    'email': ('email', ),
    'firstName': ('first_name', ),
    'lastName': ('last_name', ),
}
SAML_CONFIG = {
    'debug': DEBUG,
    'xmlsec_binary': '/usr/bin/xmlsec1',
    'attribute_map_dir': os.path.join(SAML_DIR, 'attribute-maps'),
    'entityid': SAML_ENTITY_ID,
    'valid_for': 24,  # how long is our metadata valid (hours)
    'service': {
        'sp': {
            # Allow Okta to initiate the login.
            'allow_unsolicited': 'true',
            'name': SAML_SP_NAME,
            'endpoints': {
                'assertion_consumer_service': [
                    (SAML_SSO_URL, saml2.BINDING_HTTP_POST),
                ],
            },
            'required_attributes': ['uid'],
            'idp': {
                # Configured by remote_metadata
            },
        }
    },
    # where the remote metadata is stored
    'metadata': {
        'local': [SAML_REMOTE_METADATA],
    },
}
