from urllib.parse import urljoin

from decouple import config

MEDIA_BUNDLES_PREGEN_ROOT = config('MEDIA_BUNDLES_PREGEN_ROOT', default='bundles-pregen/')
SITE_URL = config('SITE_URL', default='')
CDN_URL = config('CDN_URL', default='')


def calculate_redirect(*args, **kwargs):
    product = 'Firefox'
    locale = kwargs['locale'].lower()

    # Distribution populated by client's distribution if it starts with
    # `experiment-`. Otherwise default to `default`.
    #
    # This is because non-Mozilla distributors of Firefox (e.g. Linux
    # Distributions) override the distribution field with their identification.
    # We want all Firefox clients to get the default bundle for locale, unless
    # they are part of an experiment.
    distribution = kwargs['distribution'].lower()
    if distribution.startswith('experiment-'):
        distribution = distribution[11:]
    else:
        distribution = 'default'

    filename = (
        f'{MEDIA_BUNDLES_PREGEN_ROOT}/{product}/'
        f'{locale}/{distribution}.json'
    )

    full_url = urljoin(CDN_URL or SITE_URL, filename)

    # Return calculated locale, distribution, full_url
    return locale, distribution, full_url
