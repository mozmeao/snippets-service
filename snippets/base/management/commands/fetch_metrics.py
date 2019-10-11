from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

import sentry_sdk
from redash_dynamic_query import RedashDynamicQuery

from snippets.base.models import Job


class Command(BaseCommand):
    args = "(no args)"
    help = "Fetch metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Ignore last update timestamp and update all Jobs.',
        )

    def handle(self, *args, **options):
        now = datetime.utcnow()
        today = datetime(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0)
        before_seven_days = today - timedelta(days=7)

        if not settings.REDASH_API_KEY:
            raise CommandError('Enviroment variable REDASH_API_KEY is required.')

        redash = RedashDynamicQuery(
            endpoint=settings.REDASH_ENDPOINT,
            apikey=settings.REDASH_API_KEY,
            max_wait=settings.REDASH_MAX_WAIT,
        )

        if options['force_update']:
            jobs = Job.objects.exclude(Q(publish_end=None))
        else:
            # Update Jobs if when PUBLISHED haven't been updated for
            # REDASH_UPDATE_INTERVAL seconds or when COMPLETED haven't been
            # updated for 8 hours. Typically we need 15 seconds of Telemetry
            # time per Job, so that's more than 10 minutes for 50 Jobs. With
            # this trick we reduce the number of queries made in 24 hours
            # against Telemetry, while still maintaining good enough data
            # freshness.
            last_update_timestamp_published = (
                now - timedelta(seconds=settings.REDASH_UPDATE_INTERVAL))
            last_update_timestamp_completed = now - timedelta(hours=8)
            jobs = Job.objects.filter(
                Q(id__in=(
                    Job.objects.exclude(
                        Q(publish_end=None) |
                        Q(metric_last_update__gte=last_update_timestamp_published)
                    ) .filter(
                        Q(status=Job.PUBLISHED)
                    )
                )) |
                Q(id__in=(
                    Job.objects.exclude(
                        Q(publish_end=None) |
                        Q(metric_last_update__gte=last_update_timestamp_completed)
                    ) .filter(
                        (Q(status=Job.COMPLETED) & Q(publish_end__gte=before_seven_days))
                    )
                ))
            ).order_by('id')

        self.stdout.write(f'Fetching Updates for {jobs.count()} Jobs.')

        data_fetched = False
        for job in jobs:
            bind_data = {
                'start_date': job.publish_start.strftime('%Y%m%d'),
                # Publish end date plus 7 days to include delayed metrics
                # received with delay.
                'end_date': (job.publish_end + timedelta(days=7)).strftime('%Y%m%d'),
                'message_id': job.id,
            }
            try:
                result = redash.query(settings.REDASH_QUERY_ID, bind_data)
            except Exception as exp:
                # Capture the exception but don't quit
                sentry_sdk.capture_exception(exp)
                continue

            impressions = 0
            clicks = 0
            blocks = 0
            try:
                for row in result['query_result']['data']['rows']:
                    if row['event'] == 'IMPRESSION':
                        impressions = row['counts']
                    elif row['event'] == 'BLOCK':
                        blocks = row['counts']
                    elif row['event'] in ['CLICK', 'CLICK_BUTTON']:
                        clicks += row['counts']
            except KeyError as exp:
                # Capture the exception but don't quit
                sentry_sdk.capture_exception(exp)
                continue
            else:
                data_fetched = True

            # Use update to avoid triggering Django signals and updating Job's
            # and ASRSnippet's modified date.
            Job.objects.filter(id=job.id).update(
                metric_impressions=impressions,
                metric_blocks=blocks,
                metric_clicks=clicks,
                metric_last_update=now,
            )

        if jobs and not data_fetched:
            # We didn't manage to fetch data for any of the jobs. Something is
            # wrong.
            raise CommandError('Cannot fetch data from Telemetry.')

        self.stdout.write(self.style.SUCCESS('Done'))
