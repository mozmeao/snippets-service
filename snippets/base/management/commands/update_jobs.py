from datetime import datetime

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
            Q(publish_start__lte=now) | Q(publish_start=None)
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

        count_running = Job.objects.filter(status=Job.PUBLISHED).count()

        self.stdout.write(
            f'Jobs Published: {count_published}\n'
            f'Jobs Completed: {count_total_completed}\n'
            f'  - Reached Publication End Date: {count_publication_end}\n'
            f'  - Reached Impressions Limit: {count_limit["impressions"]}\n'
            f'  - Reached Clicks Limit: {count_limit["clicks"]}\n'
            f'  - Reached Blocks Limit: {count_limit["blocks"]}\n'
            f'Total Jobs Running: {count_running}\n'
        )
