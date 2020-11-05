import hashlib
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.functional import cached_property

import brotli

from snippets.base import models


ONE_DAY = 60 * 60 * 24

# On application load combine all the version strings of all available
# templates into one. To be used in ASRSnippetBundle.key method to calculate
# the bundle key. The point is that this string should change when the Template
# schema changes.
TEMPLATES_NG_VERSIONS = '-'.join([
    model.VERSION
    for model in apps.get_models()
    if issubclass(model, models.Template) and not model.__name__ == 'Template'
])


class ASRSnippetBundle():
    def __init__(self, client):
        self.client = client

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
    def url(self):
        bundle_url = default_storage.url(self.filename)
        full_url = urljoin(settings.SITE_URL, bundle_url).split('?')[0]
        cdn_url = getattr(settings, 'CDN_URL', None)
        if cdn_url:
            full_url = urljoin(cdn_url, urlparse(bundle_url).path)

        return full_url

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
        for job in self.jobs:
            attributes = [
                job.id,
                job.snippet.modified.isoformat(),
            ]

            key_properties.append('-'.join([str(x) for x in attributes]))

        # Additional values used to calculate the key are the templates and the
        # variables used to render them besides snippets.
        key_properties.extend([
            str(self.client.startpage_version),
            self.client.locale,
            str(settings.BUNDLE_BROTLI_COMPRESS),
            TEMPLATES_NG_VERSIONS,
        ])

        key_string = '_'.join(key_properties)
        return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

    @property
    def empty(self):
        return len(self.jobs) == 0

    @property
    def filename(self):
        return urljoin(settings.MEDIA_BUNDLES_ROOT, 'bundle_{0}.json'.format(self.key))

    @cached_property
    def jobs(self):
        return (models.Job.objects.filter(status=models.Job.PUBLISHED)
                .select_related('snippet')
                .match_client(self.client))

    def generate(self):
        """Generate and save the code for this snippet bundle."""
        # Generate the new AS Router bundle format
        data = [job.render() for job in self.jobs]
        bundle_content = json.dumps({
            'messages': data,
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'number_of_snippets': len(data),
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
