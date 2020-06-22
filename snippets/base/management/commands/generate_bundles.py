import os
import json
import itertools
from datetime import datetime

import brotli
from product_details import product_details

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.core.files.storage import default_storage

from snippets.base.models import DistributionBundle, Job


class Command(BaseCommand):
    args = '(no args)'
    help = 'Generate bundles'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--timestamp',
            help='Parse Jobs last modified after <timestamp>',
        )

    def handle(self, *args, **options):
        if not options['timestamp']:
            self.stdout.write('Generating all bundles.')
            total_jobs = Job.objects.all()
        else:
            self.stdout.write(
                'Generating bundles with Jobs modified on or after {}'.format(options['timestamp'])
            )
            total_jobs = Job.objects.filter(
                Q(snippet__modified__gte=options['timestamp']) |
                Q(distribution__distributionbundle__modified__gte=options['timestamp'])
            ).distinct()

        if not total_jobs:
            self.stdout.write('Nothing to do…')
            return

        self.stdout.write('Processing bundles…')

        combinations_to_process = set(
            itertools.chain.from_iterable(
                itertools.product(
                    job.channels,
                    job.snippet.locale.code.strip(',').split(',')
                )
                for job in total_jobs
            )
        )
        distribution_bundles_to_process = DistributionBundle.objects.filter(
            distributions__jobs__in=total_jobs
        ).distinct().order_by('id')

        for distribution_bundle in distribution_bundles_to_process:
            distributions = distribution_bundle.distributions.all()

            for channel, locale in combinations_to_process:
                additional_jobs = []
                if channel == 'nightly' and settings.NIGHTLY_INCLUDES_RELEASE:
                    additional_jobs = Job.objects.filter(
                        status=Job.PUBLISHED).filter(**{
                            'targets__on_release': True,
                            'distribution__in': distributions,
                        })

                channel_jobs = Job.objects.filter(
                    status=Job.PUBLISHED).filter(
                        Q(**{
                            'targets__on_{}'.format(channel): True,
                            'distribution__in': distributions,
                        }))

                all_jobs = Job.objects.filter(
                    Q(id__in=additional_jobs) | Q(id__in=channel_jobs)
                )

                locales_to_process = [
                    key.lower() for key in product_details.languages.keys()
                    if key.lower().startswith(locale)
                ]

                for locale_to_process in locales_to_process:
                    filename = 'Firefox/{channel}/{locale}/{distribution}.json'.format(
                        channel=channel,
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
                    # Published Jobs for the channel / locale / distribution
                    # combination, delete the current bundle file if it exists.
                    if not distribution_bundle.enabled or not bundle_jobs.exists():
                        if default_storage.exists(filename):
                            self.stdout.write('Removing {}'.format(filename))
                            default_storage.delete(filename)
                        continue

                    data = []
                    channel_job_ids = list(channel_jobs.values_list('id', flat=True))
                    for job in bundle_jobs:
                        if job.id in channel_job_ids:
                            render = job.render()
                        else:
                            render = job.render(always_eval_to_false=True)
                        data.append(render)

                    bundle_content = json.dumps({
                        'messages': data,
                        'metadata': {
                            'generated_at': datetime.utcnow().isoformat(),
                            'number_of_snippets': len(data),
                            'channel': channel,
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

                    default_storage.save(filename, content_file)
                    self.stdout.write(self.style.SUCCESS('Writing bundle {}'.format(filename)))
