##
#
# Script to produce CSVs per locale with currently running F100s
#
# To be used upon request from the OMN team. Copy / paste resulting
# CSVs to a Google Spreadsheet. Example
# https://docs.google.com/spreadsheets/d/13N8oqMx1QOqe0V572j2VqX6gwYioO5o4cLQk1y_iGnk/edit?usp=sharing
##

import csv
import io
import itertools

from snippets.base.models import ASRSnippet, Job


def writeRowCSV(csvwriter, snippet):
    csvwriter.writerow(
        [
            snippet.id,
            snippet.name,
            snippet.template_ng.get_main_body(bleached=True),
            f'https://snippets-admin.mozilla.org/admin/base/asrsnippet/{snippet.id}/change/',
            snippet.get_preview_url()
        ]
    )


def run():
    for locale in {'de', 'en', 'es', 'id', 'pl', 'pt-br', 'ru', 'zh-cn', 'zh-tw', 'fr'}:
        csvfile = io.StringIO()
        csvwriter = csv.writer(csvfile, dialect=csv.excel, quoting=csv.QUOTE_ALL)
        s = ASRSnippet.objects.filter(locale__code__contains=f',{locale}',
                                      name__icontains='f100',
                                      jobs__status=Job.PUBLISHED)
        snippets = {}
        count = 0
        for i in range(1, 18):
            ss = s.filter(name__icontains=f'week{i}_')
            snippets[i] = list(ss)
            count += ss.count()
        no_week_snippets = set(s) - set(itertools.chain(*snippets.values()))

        for number, weekly_snippets in snippets.items():
            csvwriter.writerow([f'Week {number}'])
            for snippet in weekly_snippets:
                writeRowCSV(csvwriter, snippet)

        csvwriter.writerow([f'No Week in Name'])
        for snippet in no_week_snippets:
            writeRowCSV(csvwriter, snippet)

        with open(f'{locale}.csv', 'w') as f:
            f.write(csvfile.getvalue())

        print(f'Done writing {locale}.csv')
    print('All Done')
