from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from redash_dynamic_query import RedashDynamicQuery

from snippets.base import etl
from snippets.base.models import DailyJobMetrics, Job


class Command(BaseCommand):
    args = "(no args)"
    help = "Fetch daily Job metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            help='Fetch data for date. Defaults to yesterday. In YYYY-MM-DD format.',
        )

    def handle(self, *args, **options):
        if not options['date']:
            now = datetime.utcnow()
            date = (
                datetime(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0) -
                timedelta(days=1)
            ).date()

        else:
            date = datetime.strptime(options['date'], '%Y-%m-%d').date()

        last_week = date - timedelta(days=7)  # date - 7 since we 're fetching data for yesterday.
        date_next_day = date + timedelta(days=1)

        if not settings.REDASH_API_KEY:
            raise CommandError('Enviroment variable REDASH_API_KEY is required.')

        redash = RedashDynamicQuery(
            endpoint=settings.REDASH_ENDPOINT,
            apikey=settings.REDASH_API_KEY,
            max_wait=settings.REDASH_MAX_WAIT,
        )
        jobs = (
            Job.objects
            .filter(status__in=[Job.PUBLISHED, Job.COMPLETED])
            .filter(
                # Publish start before the end of day of interest and still
                # not completed.
                (Q(publish_start__lt=date_next_day) & Q(completed_on=None)) |
                # Or running in the day of interest.
                (Q(publish_start__lt=date_next_day) & Q(publish_end__gt=date)) |
                # Or completed during the last 7 days before EOD of the day of interest.
                (Q(completed_on__gte=last_week) & Q(completed_on__lt=date_next_day))
            )
        ).order_by('id')

        if not jobs:
            self.stdout.write(f'No jobs to fetch data for.')
            return

        self.stdout.write(f'Fetching data for {date} for {jobs.count()} jobs.')

        bind_data = {'date': str(date)}
        rows = []
        for query in [settings.REDASH_DAILY_QUERY_ID, settings.REDASH_DAILY_QUERY_BIGQUERY_ID]:
            result = redash.query(query, bind_data)
            rows += result['query_result']['data']['rows']

        data_fetched = False
        for job in jobs:
            impressions = 0
            clicks = 0
            blocks = 0

            job_rows = [row for row in rows if row['message_id'] == str(job.id)]
            for row in job_rows:
                if row['event'] == 'IMPRESSION':
                    impressions += row['counts']
                elif row['event'] == 'BLOCK':
                    blocks += row['counts']
                elif row['event'] in ['CLICK', 'CLICK_BUTTON']:
                    clicks += row['counts']

            if not any([impressions, blocks, clicks]):
                # Job has no metrics for date, ignore
                continue

            data_fetched = True

            DailyJobMetrics.objects.update_or_create(date=date, job=job)
            DailyJobMetrics.objects.filter(date=date, job=job).update(
                impressions=impressions,
                blocks=blocks,
                clicks=clicks,
                data_fetched_on=datetime.utcnow(),
            )

        if jobs and not data_fetched:
            # We didn't manage to fetch data for any of the jobs. Something is
            # wrong.
            raise CommandError('Cannot fetch data from Telemetry.')

        etl.update_channel_metrics(date, date)
        etl.update_country_metrics(date, date)
        self.stdout.write(self.style.SUCCESS('Done'))
