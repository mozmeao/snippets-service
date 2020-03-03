from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from snippets.base import etl, models

METRICS_START_DATE = date(2019, 10, 1)


class Command(BaseCommand):
    args = "(no args)"
    help = "Fetch daily Job metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            help='Fetch data for date. Defaults to yesterday. In YYYY-MM-DD format.',
        )

    def handle(self, *args, **options):
        if not settings.REDASH_API_KEY:
            raise CommandError('Enviroment variable REDASH_API_KEY is required.')

        dates = []

        if options['date']:
            dates.append(datetime.strptime(options['date'], '%Y-%m-%d').date())
        else:
            today = date.today()
            try:
                fetched_dates = models.JobDailyPerformance.objects.values_list('date', flat=True)
            except models.JobDailyPerformance.DoesNotExist:
                fetched_dates = []

            check_date = METRICS_START_DATE
            while check_date < today:
                if check_date not in fetched_dates:
                    dates.append(check_date)
                check_date += timedelta(days=1)

        for d in dates:
            self.stdout.write(f'Fetching data for {d}.')

            if not all([
                    etl.update_impressions(d),
                    etl.update_job_metrics(d),
            ]):
                # We didn't manage to fetch all data, something is wrong.
                raise CommandError('Cannot fetch data from Telemetry.')

        self.stdout.write(self.style.SUCCESS('Done'))
