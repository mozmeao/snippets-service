from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

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

        if not settings.REDASH_API_KEY:
            raise CommandError('Enviroment variable REDASH_API_KEY is required.')

        redash = RedashDynamicQuery(
            endpoint=settings.REDASH_ENDPOINT,
            apikey=settings.REDASH_API_KEY,
            max_wait=settings.REDASH_MAX_WAIT,
        )

        jobs = Job.objects.filter(status=Job.PUBLISHED).exclude(
            limit_impressions=0,
            limit_clicks=0,
            limit_blocks=0,
        ).order_by('id')

        self.stdout.write(f'Fetching Updates for {jobs.count()} Jobs.')

        data_fetched_global = False
        for job in jobs:
            impressions = 0
            clicks = 0
            blocks = 0
            bind_data = {
                'start_date': job.publish_start.strftime('%Y-%m-%d'),
                'end_date': now.strftime('%Y-%m-%d'),
                'message_id': job.id,
            }

            data_fetched = 0
            # We need to fetch metrics from two different data sources
            # (RedShift and BigQuery) to capture all metrics. Firefox
            # switched to BigQuery on Firefox 72. We expect to be able
            # to remove RedShift querying in a year from 72's launch
            # (Jan 2021). Issue #1285
            for query in [settings.REDASH_JOB_QUERY_ID, settings.REDASH_JOB_QUERY_BIGQUERY_ID]:
                try:
                    result = redash.query(query, bind_data)
                except Exception as exp:
                    # Capture the exception but don't quit
                    sentry_sdk.capture_exception(exp)
                    continue

                try:
                    for row in result['query_result']['data']['rows']:
                        if row['event'] == 'IMPRESSION':
                            impressions += row['counts']
                        elif row['event'] == 'BLOCK':
                            blocks += row['counts']
                        elif row['event'] in ['CLICK', 'CLICK_BUTTON']:
                            clicks += row['counts']
                except KeyError as exp:
                    # Capture the exception but don't quit
                    sentry_sdk.capture_exception(exp)
                    continue
                else:
                    data_fetched += 1

            # We didn't fetch data from both data sources for this job, don't
            # save it.
            if data_fetched != 2:
                continue

            # We fetched data for job, mark the ETL job `working` to update
            # DeadMansSnitch.
            data_fetched_global = True

            # Use update to avoid triggering Django signals and updating Job's
            # and ASRSnippet's modified date.
            Job.objects.filter(id=job.id).update(
                metric_impressions=impressions,
                metric_blocks=blocks,
                metric_clicks=clicks,
                metric_last_update=now,
            )

        if jobs and not data_fetched_global:
            # We didn't manage to fetch data for any of the jobs. Something is
            # wrong.
            raise CommandError('Cannot fetch data from Telemetry.')

        self.stdout.write(self.style.SUCCESS('Done'))
