from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from redash_dynamic_query import RedashDynamicQuery

from snippets.base.models import DailyJobMetrics, Job


class Command(BaseCommand):
    args = "(no args)"
    help = "Fetch daily Job metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            help='Fetch data for date. Defaults to yesterday. In YYYYMMDD format.',
        )

    def handle(self, *args, **options):
        if not options['date']:
            now = datetime.utcnow()
            date = (
                datetime(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0) -
                timedelta(days=1)
            )

        else:
            date = datetime.strptime(options['date'], '%Y%m%d')

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
                # Or completed during the last 7 days before EOD of the day of interest.
                (Q(completed_on__gte=last_week) & Q(completed_on__lt=date_next_day))
            )
        ).order_by('id')

        if not jobs:
            self.stdout.write(f'No jobs to fetch data for.')
            return

        self.stdout.write(f'Fetching data for {date} for {jobs.count()} jobs.')

        bind_data = {
            'date': date.strftime('%Y%m%d'),
        }
        result = redash.query(settings.REDASH_DAILY_QUERY_ID, bind_data)

        data_fetched = False
        rows = result['query_result']['data']['rows']
        for job in jobs:
            impressions = 0
            clicks = 0
            blocks = 0

            job_rows = [row for row in rows if row['message_id'] == str(job.id)]
            for row in job_rows:
                if row['event'] == 'IMPRESSION':
                    impressions = row['counts']
                elif row['event'] == 'BLOCK':
                    blocks = row['counts']
                elif row['event'] in ['CLICK', 'CLICK_BUTTON']:
                    clicks += row['counts']

            if not any([impressions, blocks, clicks]):
                # Job has no metrics for date, ignore
                continue

            data_fetched = True

            DailyJobMetrics.objects.update_or_create(
                date=date,
                job=job,
                impressions=impressions,
                blocks=blocks,
                clicks=clicks,
            )

        if jobs and not data_fetched:
            # We didn't manage to fetch data for any of the jobs. Something is
            # wrong.
            raise CommandError('Cannot fetch data from Telemetry.')

        self.stdout.write(self.style.SUCCESS('Done'))
