#####
## Script for Snippet Metrics
##
## This is not meant to be fast or pretty. But it does the job and
## it's easy to update.
##
##
## Use:
##  - ./manage.py runscript metrics --script-args 2020-01-01 2020-03-31
##
## Copy / Paste the results into a SpreadSheet and split text by
## semicolon. On Google Sheets after pasting, click on the paste icon
## at the bottom right corner of the paste area, then select "Split
## text to columns" and finally select Semicolon.
##
## Example spreadsheet: https://bit.ly/2JO8Fmq
##
####
import sys
import collections

from django.db.models import Sum

from product_details import product_details

from snippets.base.models import *


def pprint(d):
     print(
          "  Impressions; "
          "Adj Impressions; "
          "Clicks; "
          "Blocks;"
     )
     print(
          f"  {d['impressions']}; "
          f"{d['adj_impressions']}; "
          f"{d['clicks']}; "
          f"{d['blocks']};"
     )

def pprint_cat(cat):
     print(
          "  Name; "
          "Impressions; "
          "Adj Impressions; "
          "Clicks; "
          "Blocks;"
     )

     for k, v in sorted(cat.items()):
          print(
               f"  {k}; "
               f"{v['impressions']}; "
               f"{v['adj_impressions']}; "
               f"{v['clicks']}; "
               f"{v['blocks']};"
          )


def run(bdate, edate):
     print(f'Metrics for {bdate} - {edate}')

     query = JobDailyPerformance.objects.filter(date__gte=bdate, date__lte=edate)

     # Totals
     print('Totals')
     pprint(
          query.aggregate(impressions=Sum('impression'),
                          adj_impressions=Sum('adj_impression'),
                          clicks=Sum('click'),
                          blocks=Sum('block'))
     )

     # Find Snippets without Links
     jobs_ids = query.values_list('job_id', flat=True).distinct()
     links = []
     for snippet in ASRSnippet.objects.filter(jobs__in=jobs_ids):
          r = snippet.render()
          if not r['template'] == 'simple_snippet':
              continue
          if r['content']['links'] or r['content'].get('button_label'):
              continue
          links += [snippet]

     print('Impressions of snippets without links')
     pprint(
          query.filter(job__snippet__in=links).aggregate(
               impressions=Sum('impression'),
               adj_impressions=Sum('adj_impression'),
               clicks=Sum('click'),
               blocks=Sum('block')
          )
     )

     # Find Simple Snippets button vs link
     jobs_ids = query.values_list('job_id', flat=True).distinct()
     button_snippet = []
     link_snippet = []
     for snippet in ASRSnippet.objects.filter(jobs__in=jobs_ids).distinct():
          r = snippet.render()
          if not r['template'] == 'simple_snippet':
              continue
          if r['content'].get('button_label'):
               button_snippet += [snippet]
          else:
               link_snippet += [snippet]

     print('Simple Snippets using Buttons')
     pprint(
          query.filter(job__snippet__in=button_snippet).aggregate(
               impressions=Sum('impression'),
               adj_impressions=Sum('adj_impression'),
               clicks=Sum('click'),
               blocks=Sum('block'),
          )
     )
     print('Simple Snippets using Links')
     pprint(
          query.filter(job__snippet__in=link_snippet).aggregate(
               impressions=Sum('impression'),
               adj_impressions=Sum('adj_impression'),
               clicks=Sum('click'),
               blocks=Sum('block'),
          )
     )

     # by category
     cat = collections.defaultdict(lambda: dict(adj_impressions=0, impressions=0, clicks=0, blocks=0))
     for item in query.values('job__id', 'impression', 'adj_impression', 'click', 'block', 'job__snippet__category__name'):
       cat[item['job__snippet__category__name']]['jobs'] = cat[item['job__snippet__category__name']].get('jobs', []) + [item['job__id']]
       cat[item['job__snippet__category__name']]['impressions'] += item['impression']
       cat[item['job__snippet__category__name']]['adj_impressions'] += item['adj_impression']
       cat[item['job__snippet__category__name']]['clicks'] += item['click']
       cat[item['job__snippet__category__name']]['blocks'] += item['block']

     print('By Category')
     pprint_cat(cat)


     # By locale
     locale = collections.defaultdict(lambda: dict(adj_impressions=0, impressions=0, clicks=0, blocks=0))
     for item in query.values('job__id', 'impression', 'adj_impression', 'click', 'block', 'job__snippet__locale__name'):
       locale[item['job__snippet__locale__name']]['jobs'] = locale[item['job__snippet__locale__name']].get('jobs', []) + [item['job__id']]
       locale[item['job__snippet__locale__name']]['impressions'] += item['impression']
       locale[item['job__snippet__locale__name']]['adj_impressions'] += item['adj_impression']
       locale[item['job__snippet__locale__name']]['clicks'] += item['click']
       locale[item['job__snippet__locale__name']]['blocks'] += item['block']

     print('By Locale')
     pprint_cat(locale)


     # By template type
     template_relation = collections.defaultdict(lambda: dict(adj_impressions=0, impressions=0, clicks=0, blocks=0))
     for item in query.values('job__id', 'adj_impression', 'impression', 'click', 'block', 'job__snippet__template_relation'):
       template_type = Template.objects.filter(id=item['job__snippet__template_relation'])[0].subtemplate.NAME
       template_relation[template_type]['jobs'] = template_relation[template_type].get('jobs', []) + [item['job__id']]
       template_relation[template_type]['impressions'] += item['impression']
       template_relation[template_type]['adj_impressions'] += item['adj_impression']
       template_relation[template_type]['clicks'] += item['click']
       template_relation[template_type]['blocks'] += item['block']

     print('By Template Type')
     pprint_cat(template_relation)

     # By Channel
     channel = collections.defaultdict(lambda: dict(adj_impressions=0, impressions=0, clicks=0, blocks=0))
     for jdp in query:
       ratio = (jdp.adj_impression / jdp.impression) if jdp.impression else 0
       for item in jdp.details:
         if item['event'] in ['impression', 'click', 'block']:
           channel[item['channel']][item['event'] + 's'] += item['counts']
           if item['event']  == 'impression':
                channel[item['channel']]['adj_impressions'] += round(item['counts'] * ratio)
           if 'jobs' in channel[item['channel']]:
                if jdp.job_id not in channel[item['channel']]['jobs']:
                     channel[item['channel']]['jobs'] += [jdp.job_id]
           else:
                channel[item['channel']]['jobs'] = [jdp.job_id]

     print('By Channel')
     pprint_cat(channel)


     # By Country
     _tmp_countries = collections.defaultdict(lambda: dict(adj_impressions=0, impressions=0, clicks=0, blocks=0))
     for jdp in query:
       ratio = (jdp.adj_impression / jdp.impression) if jdp.impression else 0
       country_name = item['country']
       for item in jdp.details:
         if item['event'] in ['impression', 'click', 'block']:
           _tmp_countries[country_name][item['event'] + 's'] += item['counts']
           if item['event']  == 'impression':
                _tmp_countries[country_name]['adj_impressions'] += round(item['counts'] * ratio)
           if 'jobs' in _tmp_countries[country_name]:
                if jdp.job_id not in _tmp_countries[country_name]['jobs']:
                     _tmp_countries[country_name]['jobs'] += [jdp.job_id]
           else:
                _tmp_countries[country_name]['jobs'] = [jdp.job_id]

     countries = {}
     for item in _tmp_countries:
          new_name = f'{product_details.get_regions("en-US").get(item.lower(), item)} ({item})'
          countries[new_name] = _tmp_countries[item]

     print('By Country')
     pprint_cat(countries)


     # By Product
     products = collections.defaultdict(lambda: dict(adj_impressions=0, impressions=0, clicks=0, blocks=0))
     for item in query.values('job__id', 'impression', 'adj_impression', 'click', 'block', 'job__snippet__product__name'):
       products[item['job__snippet__product__name']]['jobs'] = products[item['job__snippet__product__name']].get('jobs', []) + [item['job__id']]
       products[item['job__snippet__product__name']]['impressions'] += item['impression']
       products[item['job__snippet__product__name']]['adj_impressions'] += item['adj_impression']
       products[item['job__snippet__product__name']]['clicks'] += item['click']
       products[item['job__snippet__product__name']]['blocks'] += item['block']

     print('By Product')
     pprint_cat(products)
