import csv
import io
import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile

from snippets.base.models import ASRSnippet


class Command(BaseCommand):
    args = '(no args)'
    help = 'Export snippets to CSV'

    def handle(self, *args, **options):
        snippets = ASRSnippet.objects.filter(for_qa=False).order_by('id')

        csvfile = io.StringIO()
        csvwriter = csv.writer(csvfile, dialect=csv.excel, quoting=csv.QUOTE_ALL)
        for snippet in snippets:
            csvwriter.writerow(snippet.analytics_export().values())

        now = timezone.now()
        filename = os.path.join(settings.CSV_EXPORT_ROOT,
                                now.strftime('snippets_metadata_%Y%m%d.csv'))

        default_storage.save(filename, ContentFile(csvfile.getvalue().encode('utf-8')))

        self.stdout.write('Done exporting')
