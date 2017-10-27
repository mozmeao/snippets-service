from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from snippets.base.models import Snippet


class Command(BaseCommand):
    args = '(no args)'
    help = 'Disable snippets past publish date'

    @transaction.atomic
    def handle(self, *args, **options):
        now = datetime.utcnow()
        snippets = Snippet.objects.filter(disabled=False, publish_end__lte=now)
        disabled = snippets.update(disabled=True)
        running = Snippet.objects.filter(disabled=False).count()

        self.stdout.write(
            'Snippets Disabled: {disabled}\n'
            'Snippets Running: {running}\n'.format(disabled=disabled,
                                                   running=running))
