from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Q

from snippets.base.models import Job


class Command(BaseCommand):
    args = "(no args)"
    help = "Update Jobs"

    @transaction.atomic
    def handle(self, *args, **options):
        now = datetime.utcnow()
        user = get_user_model().objects.get_or_create(username='snippets_bot')[0]
        count_total_completed = 0

        # Publish Scheduled Jobs with `publish_start` before now or without
        # publish_start.
        jobs = Job.objects.filter(status=Job.SCHEDULED).filter(
            Q(publish_start__lte=now - timedelta(minutes=settings.SNIPPETS_PUBLICATION_OFFSET)) |
            Q(publish_start=None)
        )

        count_published = jobs.count()
        for job in jobs:
            job.change_status(
                status=Job.PUBLISHED,
                user=user,
                reason='Published start date reached.',
            )

        # Disable Published Jobs with `publish_end` before now.
        jobs = Job.objects.filter(status=Job.PUBLISHED, publish_end__lte=now)
        count_publication_end = jobs.count()
        count_total_completed += count_publication_end

        for job in jobs:
            job.change_status(
                status=Job.COMPLETED,
                user=user,
                reason='Publication end date reached.',
            )

        # Disable Jobs that reached Impression, Click or Block limits.
        count_limit = {}
        for limit in ['impressions', 'clicks', 'blocks']:
            jobs = (Job.objects
                    .filter(status=Job.PUBLISHED)
                    .exclude(**{f'limit_{limit}': 0})
                    .filter(**{f'limit_{limit}__lte': F(f'metric_{limit}')}))
            for job in jobs:
                job.change_status(
                    status=Job.COMPLETED,
                    user=user,
                    reason=f'Limit reached: {limit}.',
                )

            count_limit[limit] = jobs.count()
            count_total_completed += count_limit[limit]

        # Disable Jobs that have Impression, Click or Block limits but don't
        # have metrics data for at least 24h. This is to handle cases where the
        # Metrics Pipeline is broken.
        yesterday = datetime.utcnow() - timedelta(days=1)
        jobs = (Job.objects
                .filter(status=Job.PUBLISHED)
                .exclude(limit_impressions=0, limit_clicks=0, limit_blocks=0)
                # Exclude Jobs with limits which haven't been updated once yet.
                .exclude(metric_last_update='1970-01-01')
                .filter(metric_last_update__lt=yesterday))
        for job in jobs:
            job.change_status(
                status=Job.COMPLETED,
                user=user,
                reason=f'Premature termination due to missing metrics.',
            )
        count_premature_termination = jobs.count()
        count_total_completed += count_premature_termination

        count_running = Job.objects.filter(status=Job.PUBLISHED).count()

        self.stdout.write(
            f'Jobs Published: {count_published}\n'
            f'Jobs Completed: {count_total_completed}\n'
            f'  - Reached Publication End Date: {count_publication_end}\n'
            f'  - Reached Impressions Limit: {count_limit["impressions"]}\n'
            f'  - Reached Clicks Limit: {count_limit["clicks"]}\n'
            f'  - Reached Blocks Limit: {count_limit["blocks"]}\n'
            f'  - Premature Termination due to missing metrics: {count_premature_termination}\n'
            f'Total Jobs Running: {count_running}\n'
        )
