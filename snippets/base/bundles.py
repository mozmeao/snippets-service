import itertools
import json
import os
from datetime import datetime
from io import StringIO

import brotli
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from product_details import product_details

from snippets.base import models


def generate_bundles(timestamp=None, limit_to_locale=None,
                     limit_to_distribution_bundle=None, save_to_disk=True,
                     stdout=StringIO()):
    if not timestamp:
        stdout.write('Generating all bundles.')
        total_jobs = models.Job.objects.all()
    else:
        stdout.write(
            'Generating bundles with Jobs modified on or after {}'.format(timestamp)
        )
        total_jobs = models.Job.objects.filter(
            Q(snippet__modified__gte=timestamp) |
            Q(distribution__distributionbundle__modified__gte=timestamp)
        ).distinct()

    stdout.write('Processing bundles…')
    if limit_to_locale:
        all_locales_to_process = [
            limit_to_locale,
        ]
    else:
        all_locales_to_process = set(
            itertools.chain.from_iterable(
                job.snippet.locale.code.strip(',').split(',')
                for job in total_jobs
            )
        )
    distribution_bundles_to_process = models.DistributionBundle.objects.filter(
        distributions__jobs__in=total_jobs
    ).distinct().order_by('id')

    if limit_to_distribution_bundle:
        distribution_bundles_to_process = distribution_bundles_to_process.filter(
            name__iexact=limit_to_distribution_bundle
        )

    for distribution_bundle in distribution_bundles_to_process:
        distributions = distribution_bundle.distributions.all()

        for locale in all_locales_to_process:

            all_jobs = (models.Job.objects
                        .filter(status=models.Job.PUBLISHED)
                        .filter(distribution__in=distributions))

            locales_to_process = [
                key.lower() for key in product_details.languages.keys()
                if key.lower().startswith(locale)
            ]

            for locale_to_process in locales_to_process:
                filename = 'Firefox/{locale}/{distribution}.json'.format(
                    locale=locale_to_process,
                    distribution=distribution_bundle.code_name,
                )
                filename = os.path.join(settings.MEDIA_BUNDLES_PREGEN_ROOT, filename)
                full_locale = ',{},'.format(locale_to_process.lower())
                splitted_locale = ',{},'.format(locale_to_process.lower().split('-', 1)[0])
                bundle_jobs = all_jobs.filter(
                    Q(snippet__locale__code__contains=splitted_locale) |
                    Q(snippet__locale__code__contains=full_locale)).distinct()

                # If DistributionBundle is not enabled, or if there are no
                # Published Jobs for the locale / distribution
                # combination, delete the current bundle file if it exists.
                if save_to_disk and not distribution_bundle.enabled or not bundle_jobs.exists():
                    if default_storage.exists(filename):
                        stdout.write('Removing {}'.format(filename))
                        default_storage.delete(filename)
                    continue

                data = [
                    job.render() for job in bundle_jobs
                ]
                bundle_content = json.dumps({
                    'messages': data,
                    'metadata': {
                        'generated_at': datetime.utcnow().isoformat(),
                        'number_of_snippets': len(data),
                        'locale': locale_to_process,
                        'distribution_bundle': distribution_bundle.code_name,
                    }
                })

                # Convert str to bytes.
                if isinstance(bundle_content, str):
                    bundle_content = bundle_content.encode('utf-8')

                if settings.BUNDLE_BROTLI_COMPRESS:
                    content_file = ContentFile(brotli.compress(bundle_content))
                    content_file.content_encoding = 'br'
                else:
                    content_file = ContentFile(bundle_content)

                if save_to_disk is True:
                    default_storage.save(filename, content_file)
                    stdout.write('Writing bundle {}'.format(filename))
                else:
                    return content_file

    # If save_to_disk is False and we reach this point, it means that we didn't
    # have any Jobs to return for the locale, channel, distribution combination.
    # Return an empty bundle
    if save_to_disk is False:
        return ContentFile(
            json.dumps({
                'messages': [],
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'number_of_snippets': 0,
                    'locale': limit_to_locale,
                    'distribution_bundle': limit_to_distribution_bundle,
                }
            })
        )
