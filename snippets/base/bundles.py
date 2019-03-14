import hashlib
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.utils.functional import cached_property

import brotli

from snippets.base import util
from snippets.base.models import STATUS_CHOICES, ASRSnippet, Snippet


ONE_DAY = 60 * 60 * 24

SNIPPET_FETCH_TEMPLATE_HASH = hashlib.sha1(
    render_to_string(
        'base/fetch_snippets.jinja',
        {
            'date': '',
            'snippet_ids': [],
            'snippets_json': '',
            'locale': 'xx',
            'settings': settings,
            'current_firefox_major_version': '00',
            'metrics_url': settings.METRICS_URL,
        }
    ).encode('utf-8')).hexdigest()

SNIPPET_FETCH_TEMPLATE_AS_HASH = hashlib.sha1(
    render_to_string(
        'base/fetch_snippets_as.jinja',
        {
            'date': '',
            'snippet_ids': [],
            'snippets_json': '',
            'locale': 'xx',
            'settings': settings,
            'current_firefox_major_version': '00',
            'metrics_url': settings.METRICS_URL,
        }
    ).encode('utf-8')).hexdigest()


class SnippetBundle(object):
    """
    Group of snippets to be sent to a particular client configuration.
    """
    def __init__(self, client):
        self.client = client

    @cached_property
    def key(self):
        """A unique key for this bundle as a sha1 hexdigest."""
        # Key should consist of snippets that are in the bundle. This part
        # accounts for all the properties sent by the Client, since the
        # self.snippets lists snippets are all filters and CMRs have been
        # applied.
        key_properties = [
            '{id}-{date}-{templatedate}'.format(id=snippet.id,
                                                date=snippet.modified.isoformat(),
                                                templatedate=snippet.template.modified.isoformat())
            for snippet in self.snippets]

        # Additional values used to calculate the key are the templates and the
        # variables used to render them besides snippets.
        key_properties.extend([
            str(self.client.startpage_version),
            self.client.locale,
            util.current_firefox_major_version(),
            str(settings.BUNDLE_BROTLI_COMPRESS),
        ])
        if self.client.startpage_version >= 5:
            key_properties.append(SNIPPET_FETCH_TEMPLATE_AS_HASH)
        else:
            key_properties.append(SNIPPET_FETCH_TEMPLATE_HASH)

        key_string = '_'.join(key_properties)
        return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

    @property
    def empty(self):
        return len(self.snippets) == 0

    @property
    def cache_key(self):
        return 'bundle_' + self.key

    @property
    def cached(self):
        if cache.get(self.cache_key):
            return True

        # Check if available on S3 already.
        if default_storage.exists(self.filename):
            cache.set(self.cache_key, True, ONE_DAY)
            return True

        return False

    @property
    def expired(self):
        """
        If True, the code for this bundle should be re-generated before
        use.
        """
        return not cache.get(self.cache_key)

    @property
    def filename(self):
        return urljoin(settings.MEDIA_BUNDLES_ROOT, 'bundle_{0}.html'.format(self.key))

    @property
    def url(self):
        bundle_url = default_storage.url(self.filename)
        full_url = urljoin(settings.SITE_URL, bundle_url).split('?')[0]
        cdn_url = getattr(settings, 'CDN_URL', None)
        if cdn_url:
            full_url = urljoin(cdn_url, urlparse(bundle_url).path)

        return full_url

    @cached_property
    def snippets(self):
        return (Snippet.objects
                .filter(published=True)
                .match_client(self.client)
                .select_related('template')
                .prefetch_related('countries', 'exclude_from_search_providers')
                .filter_by_available())

    def generate(self):
        """Generate and save the code for this snippet bundle."""
        template = 'base/fetch_snippets.jinja'
        if self.client.startpage_version == 5:
            template = 'base/fetch_snippets_as.jinja'
        bundle_content = render_to_string(template, {
            'snippet_ids': [snippet.id for snippet in self.snippets],
            'snippets_json': json.dumps([s.to_dict() for s in self.snippets]),
            'client': self.client,
            'locale': self.client.locale,
            'settings': settings,
            'current_firefox_major_version': util.current_firefox_major_version(),
        })

        if isinstance(bundle_content, str):
            bundle_content = bundle_content.encode('utf-8')

        if (settings.BUNDLE_BROTLI_COMPRESS and self.client.startpage_version >= 5):
            content_file = ContentFile(brotli.compress(bundle_content))
            content_file.content_encoding = 'br'
        else:
            content_file = ContentFile(bundle_content)

        default_storage.save(self.filename, content_file)
        cache.set(self.cache_key, True, ONE_DAY)


class ASRSnippetBundle(SnippetBundle):

    @cached_property
    def key(self):
        """A unique key for this bundle as a sha1 hexdigest."""
        # Key should consist of snippets that are in the bundle. This part
        # accounts for all the properties sent by the Client, since the
        # self.snippets lists snippets are all filters and CMRs have been
        # applied.
        #
        # Key must change when Snippet or related Template, Campaign or Target
        # get updated.
        key_properties = []
        for snippet in self.snippets:
            attributes = [
                snippet.id,
                snippet.modified.isoformat(),
                snippet.template_ng.version,
            ]

            attributes.extend(
                [target.modified.isoformat() for target in snippet.targets.all()]
            )

            if snippet.campaign:
                attributes.append(snippet.campaign.modified.isoformat())

            key_properties.append('-'.join([str(x) for x in attributes]))

        # Additional values used to calculate the key are the templates and the
        # variables used to render them besides snippets.
        key_properties.extend([
            str(self.client.startpage_version),
            self.client.locale,
            str(settings.BUNDLE_BROTLI_COMPRESS),
        ])

        key_string = '_'.join(key_properties)
        return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

    @property
    def filename(self):
        return urljoin(settings.MEDIA_BUNDLES_ROOT, 'bundle_{0}.json'.format(self.key))

    @cached_property
    def snippets(self):
        return (ASRSnippet.objects
                .filter(status=STATUS_CHOICES['Published'])
                .select_related('template', 'campaign')
                .match_client(self.client)
                .filter_by_available())

    def generate(self):
        """Generate and save the code for this snippet bundle."""
        # Generate the new AS Router bundle format
        data = [snippet.render() for snippet in self.snippets]
        bundle_content = json.dumps({
            'messages': data,
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'number_of_snippets': len(self.snippets),
            }
        })

        if isinstance(bundle_content, str):
            bundle_content = bundle_content.encode('utf-8')

        if settings.BUNDLE_BROTLI_COMPRESS:
            content_file = ContentFile(brotli.compress(bundle_content))
            content_file.content_encoding = 'br'
        else:
            content_file = ContentFile(bundle_content)

        default_storage.save(self.filename, content_file)
        cache.set(self.cache_key, True, ONE_DAY)
