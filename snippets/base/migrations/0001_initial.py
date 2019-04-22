# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import snippets.base.fields
import snippets.base.models
import snippets.base.storage


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ClientMatchRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(unique=True, max_length=255)),
                ('is_exclusion', models.BooleanField(default=False)),
                ('startpage_version', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('name', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('version', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('appbuildid', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('build_target', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('locale', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('channel', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('os_version', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('distribution', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('distribution_version', snippets.base.fields.RegexField(blank=True, max_length=255, validators=[snippets.base.fields.validate_regex])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('-modified',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='JSONSnippet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('priority', models.IntegerField(default=0, blank=True)),
                ('disabled', models.BooleanField(default=True)),
                ('icon', models.TextField(help_text=b'Icon should be a 96x96px PNG.')),
                ('text', models.CharField(help_text=b'Maximum length 140 characters.', max_length=140)),
                ('url', models.CharField(max_length=500)),
                ('publish_start', models.DateTimeField(null=True, blank=True)),
                ('publish_end', models.DateTimeField(null=True, blank=True)),
                ('on_release', models.BooleanField(default=True, verbose_name=b'Release')),
                ('on_beta', models.BooleanField(default=False, verbose_name=b'Beta')),
                ('on_aurora', models.BooleanField(default=False, verbose_name=b'Aurora')),
                ('on_nightly', models.BooleanField(default=False, verbose_name=b'Nightly')),
                ('on_startpage_1', models.BooleanField(default=True, verbose_name=b'Version 1')),
                ('weight', models.IntegerField(default=100, help_text=b'How often should this snippet be shown to users?', verbose_name=b'Prevalence', choices=[(33, b'Appear 1/3rd as often as an average snippet'), (50, b'Appear half as often as an average snippet'), (66, b'Appear 2/3rds as often as an average snippet'), (100, b'Appear as often as an average snippet'), (150, b'Appear 1.5 times as often as an average snippet'), (200, b'Appear twice as often as an average snippet'), (300, b'Appear three times as often as an average snippet')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('client_match_rules', models.ManyToManyField(to='base.ClientMatchRule', verbose_name=b'Client Match Rules', blank=True)),
            ],
            options={
                'ordering': ('-modified',),
                'verbose_name': 'JSON Snippet',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='JSONSnippetLocale',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('locale', models.CharField(default=b'en-us', max_length=32, choices=[('ach', 'ach (Acholi)'), ('af', 'af (Afrikaans)'), ('ak', 'ak (Akan)'), ('am-et', 'am-et (Amharic)'), ('an', 'an (Aragonese)'), ('ar', 'ar (Arabic)'), ('as', 'as (Assamese)'), ('ast', 'ast (Asturian)'), ('az', 'az (Azerbaijani)'), ('be', 'be (Belarusian)'), ('bg', 'bg (Bulgarian)'), ('bm', 'bm (Bambara)'), ('bn-bd', 'bn-BD (Bengali (Bangladesh))'), ('bn-in', 'bn-IN (Bengali (India))'), ('br', 'br (Breton)'), ('brx', 'brx (Bodo)'), ('bs', 'bs (Bosnian)'), ('ca', 'ca (Catalan)'), ('ca-valencia', 'ca-valencia (Catalan (Valencian))'), ('cak', 'cak (Kaqchikel)'), ('cs', 'cs (Czech)'), ('csb', 'csb (Kashubian)'), ('cy', 'cy (Welsh)'), ('da', 'da (Danish)'), ('dbg', 'dbg (Debug Robot)'), ('de', 'de (German)'), ('de-at', 'de-AT (German (Austria))'), ('de-ch', 'de-CH (German (Switzerland))'), ('de-de', 'de-DE (German (Germany))'), ('dsb', 'dsb (Lower Sorbian)'), ('ee', 'ee (Ewe)'), ('el', 'el (Greek)'), ('en-au', 'en-AU (English (Australian))'), ('en-ca', 'en-CA (English (Canadian))'), ('en-gb', 'en-GB (English (British))'), ('en-nz', 'en-NZ (English (New Zealand))'), ('en-us', 'en-US (English (US))'), ('en-za', 'en-ZA (English (South African))'), ('eo', 'eo (Esperanto)'), ('es', 'es (Spanish)'), ('es-ar', 'es-AR (Spanish (Argentina))'), ('es-cl', 'es-CL (Spanish (Chile))'), ('es-es', 'es-ES (Spanish (Spain))'), ('es-mx', 'es-MX (Spanish (Mexico))'), ('et', 'et (Estonian)'), ('eu', 'eu (Basque)'), ('fa', 'fa (Persian)'), ('ff', 'ff (Fulah)'), ('fi', 'fi (Finnish)'), ('fj-fj', 'fj-FJ (Fijian)'), ('fr', 'fr (French)'), ('fur-it', 'fur-IT (Friulian)'), ('fy-nl', 'fy-NL (Frisian)'), ('ga', 'ga (Irish)'), ('ga-ie', 'ga-IE (Irish)'), ('gd', 'gd (Gaelic (Scotland))'), ('gl', 'gl (Galician)'), ('gu', 'gu (Gujarati)'), ('gu-in', 'gu-IN (Gujarati (India))'), ('ha', 'ha (Hausa)'), ('he', 'he (Hebrew)'), ('hi', 'hi (Hindi)'), ('hi-in', 'hi-IN (Hindi (India))'), ('hr', 'hr (Croatian)'), ('hsb', 'hsb (Upper Sorbian)'), ('hu', 'hu (Hungarian)'), ('hy-am', 'hy-AM (Armenian)'), ('id', 'id (Indonesian)'), ('ig', 'ig (Igbo)'), ('is', 'is (Icelandic)'), ('it', 'it (Italian)'), ('ja', 'ja (Japanese)'), ('ja-jp-mac', 'ja-JP-mac (Japanese)'), ('ka', 'ka (Georgian)'), ('kk', 'kk (Kazakh)'), ('km', 'km (Khmer)'), ('kn', 'kn (Kannada)'), ('ko', 'ko (Korean)'), ('kok', 'kok (Konkani)'), ('ks', 'ks (Kashmiri)'), ('ku', 'ku (Kurdish)'), ('la', 'la (Latin)'), ('lg', 'lg (Luganda)'), ('lij', 'lij (Ligurian)'), ('ln', 'ln (Lingala)'), ('lo', 'lo (Lao)'), ('lt', 'lt (Lithuanian)'), ('lv', 'lv (Latvian)'), ('mai', 'mai (Maithili)'), ('mg', 'mg (Malagasy)'), ('mi', 'mi (Maori (Aotearoa))'), ('mk', 'mk (Macedonian)'), ('ml', 'ml (Malayalam)'), ('mn', 'mn (Mongolian)'), ('mr', 'mr (Marathi)'), ('ms', 'ms (Malay)'), ('my', 'my (Burmese)'), ('nb-no', 'nb-NO (Norwegian (Bokm\xe5l))'), ('ne-np', 'ne-NP (Nepali)'), ('nl', 'nl (Dutch)'), ('nn-no', 'nn-NO (Norwegian (Nynorsk))'), ('nr', 'nr (Ndebele, South)'), ('nso', 'nso (Northern Sotho)'), ('oc', 'oc (Occitan (Lengadocian))'), ('or', 'or (Oriya)'), ('pa', 'pa (Punjabi)'), ('pa-in', 'pa-IN (Punjabi (India))'), ('pl', 'pl (Polish)'), ('pt-br', 'pt-BR (Portuguese (Brazilian))'), ('pt-pt', 'pt-PT (Portuguese (Portugal))'), ('rm', 'rm (Romansh)'), ('ro', 'ro (Romanian)'), ('ru', 'ru (Russian)'), ('rw', 'rw (Kinyarwanda)'), ('sa', 'sa (Sanskrit)'), ('sah', 'sah (Sakha)'), ('sat', 'sat (Santali)'), ('si', 'si (Sinhala)'), ('sk', 'sk (Slovak)'), ('sl', 'sl (Slovenian)'), ('son', 'son (Songhai)'), ('sq', 'sq (Albanian)'), ('sr', 'sr (Serbian)'), ('sr-cyrl', 'sr-Cyrl (Serbian)'), ('sr-latn', 'sr-Latn (Serbian)'), ('ss', 'ss (Siswati)'), ('st', 'st (Southern Sotho)'), ('sv-se', 'sv-SE (Swedish)'), ('sw', 'sw (Swahili)'), ('ta', 'ta (Tamil)'), ('ta-in', 'ta-IN (Tamil (India))'), ('ta-lk', 'ta-LK (Tamil (Sri Lanka))'), ('te', 'te (Telugu)'), ('th', 'th (Thai)'), ('tl', 'tl (Tagalog)'), ('tn', 'tn (Tswana)'), ('tr', 'tr (Turkish)'), ('ts', 'ts (Tsonga)'), ('tsz', 'tsz (Pur\xe9pecha)'), ('tt-ru', 'tt-RU (Tatar)'), ('uk', 'uk (Ukrainian)'), ('ur', 'ur (Urdu)'), ('uz', 'uz (Uzbek)'), ('ve', 've (Venda)'), ('vi', 'vi (Vietnamese)'), ('wo', 'wo (Wolof)'), ('x-testing', 'x-testing (Testing)'), ('xh', 'xh (Xhosa)'), ('yo', 'yo (Yoruba)'), ('zh-cn', 'zh-CN (Chinese (Simplified))'), ('zh-tw', 'zh-TW (Chinese (Traditional))'), ('zu', 'zu (Zulu)')])),
                ('snippet', models.ForeignKey(related_name='locale_set', on_delete='models.CASCADE', to='base.JSONSnippet')),
            ],
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SearchProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('identifier', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ('id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Snippet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('data', models.TextField(default=b'{}', validators=[snippets.base.validators.validate_xml_variables])),
                ('priority', models.IntegerField(default=0, blank=True)),
                ('disabled', models.BooleanField(default=True)),
                ('publish_start', models.DateTimeField(null=True, blank=True)),
                ('publish_end', models.DateTimeField(null=True, blank=True)),
                ('on_release', models.BooleanField(default=True, verbose_name=b'Release')),
                ('on_beta', models.BooleanField(default=False, verbose_name=b'Beta')),
                ('on_aurora', models.BooleanField(default=False, verbose_name=b'Aurora')),
                ('on_nightly', models.BooleanField(default=False, verbose_name=b'Nightly')),
                ('on_startpage_1', models.BooleanField(default=False, verbose_name=b'Version 1')),
                ('on_startpage_2', models.BooleanField(default=True, verbose_name=b'Version 2')),
                ('on_startpage_3', models.BooleanField(default=True, verbose_name=b'Version 3')),
                ('on_startpage_4', models.BooleanField(default=True, verbose_name=b'Version 4')),
                ('weight', models.IntegerField(default=100, help_text=b'How often should this snippet be shown to users?', verbose_name=b'Prevalence', choices=[(33, b'Appear 1/3rd as often as an average snippet'), (50, b'Appear half as often as an average snippet'), (66, b'Appear 2/3rds as often as an average snippet'), (100, b'Appear as often as an average snippet'), (150, b'Appear 1.5 times as often as an average snippet'), (200, b'Appear twice as often as an average snippet'), (300, b'Appear three times as often as an average snippet')])),
                ('campaign', models.CharField(default=b'', help_text=b'Optional campaign name. Will be added in the stats ping.', max_length=255, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('client_match_rules', models.ManyToManyField(to='base.ClientMatchRule', verbose_name=b'Client Match Rules', blank=True)),
            ],
            options={
                'ordering': ('-modified',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SnippetLocale',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('locale', models.CharField(default=b'en-us', max_length=32, choices=[('ach', 'ach (Acholi)'), ('af', 'af (Afrikaans)'), ('ak', 'ak (Akan)'), ('am-et', 'am-et (Amharic)'), ('an', 'an (Aragonese)'), ('ar', 'ar (Arabic)'), ('as', 'as (Assamese)'), ('ast', 'ast (Asturian)'), ('az', 'az (Azerbaijani)'), ('be', 'be (Belarusian)'), ('bg', 'bg (Bulgarian)'), ('bm', 'bm (Bambara)'), ('bn-bd', 'bn-BD (Bengali (Bangladesh))'), ('bn-in', 'bn-IN (Bengali (India))'), ('br', 'br (Breton)'), ('brx', 'brx (Bodo)'), ('bs', 'bs (Bosnian)'), ('ca', 'ca (Catalan)'), ('ca-valencia', 'ca-valencia (Catalan (Valencian))'), ('cak', 'cak (Kaqchikel)'), ('cs', 'cs (Czech)'), ('csb', 'csb (Kashubian)'), ('cy', 'cy (Welsh)'), ('da', 'da (Danish)'), ('dbg', 'dbg (Debug Robot)'), ('de', 'de (German)'), ('de-at', 'de-AT (German (Austria))'), ('de-ch', 'de-CH (German (Switzerland))'), ('de-de', 'de-DE (German (Germany))'), ('dsb', 'dsb (Lower Sorbian)'), ('ee', 'ee (Ewe)'), ('el', 'el (Greek)'), ('en-au', 'en-AU (English (Australian))'), ('en-ca', 'en-CA (English (Canadian))'), ('en-gb', 'en-GB (English (British))'), ('en-nz', 'en-NZ (English (New Zealand))'), ('en-us', 'en-US (English (US))'), ('en-za', 'en-ZA (English (South African))'), ('eo', 'eo (Esperanto)'), ('es', 'es (Spanish)'), ('es-ar', 'es-AR (Spanish (Argentina))'), ('es-cl', 'es-CL (Spanish (Chile))'), ('es-es', 'es-ES (Spanish (Spain))'), ('es-mx', 'es-MX (Spanish (Mexico))'), ('et', 'et (Estonian)'), ('eu', 'eu (Basque)'), ('fa', 'fa (Persian)'), ('ff', 'ff (Fulah)'), ('fi', 'fi (Finnish)'), ('fj-fj', 'fj-FJ (Fijian)'), ('fr', 'fr (French)'), ('fur-it', 'fur-IT (Friulian)'), ('fy-nl', 'fy-NL (Frisian)'), ('ga', 'ga (Irish)'), ('ga-ie', 'ga-IE (Irish)'), ('gd', 'gd (Gaelic (Scotland))'), ('gl', 'gl (Galician)'), ('gu', 'gu (Gujarati)'), ('gu-in', 'gu-IN (Gujarati (India))'), ('ha', 'ha (Hausa)'), ('he', 'he (Hebrew)'), ('hi', 'hi (Hindi)'), ('hi-in', 'hi-IN (Hindi (India))'), ('hr', 'hr (Croatian)'), ('hsb', 'hsb (Upper Sorbian)'), ('hu', 'hu (Hungarian)'), ('hy-am', 'hy-AM (Armenian)'), ('id', 'id (Indonesian)'), ('ig', 'ig (Igbo)'), ('is', 'is (Icelandic)'), ('it', 'it (Italian)'), ('ja', 'ja (Japanese)'), ('ja-jp-mac', 'ja-JP-mac (Japanese)'), ('ka', 'ka (Georgian)'), ('kk', 'kk (Kazakh)'), ('km', 'km (Khmer)'), ('kn', 'kn (Kannada)'), ('ko', 'ko (Korean)'), ('kok', 'kok (Konkani)'), ('ks', 'ks (Kashmiri)'), ('ku', 'ku (Kurdish)'), ('la', 'la (Latin)'), ('lg', 'lg (Luganda)'), ('lij', 'lij (Ligurian)'), ('ln', 'ln (Lingala)'), ('lo', 'lo (Lao)'), ('lt', 'lt (Lithuanian)'), ('lv', 'lv (Latvian)'), ('mai', 'mai (Maithili)'), ('mg', 'mg (Malagasy)'), ('mi', 'mi (Maori (Aotearoa))'), ('mk', 'mk (Macedonian)'), ('ml', 'ml (Malayalam)'), ('mn', 'mn (Mongolian)'), ('mr', 'mr (Marathi)'), ('ms', 'ms (Malay)'), ('my', 'my (Burmese)'), ('nb-no', 'nb-NO (Norwegian (Bokm\xe5l))'), ('ne-np', 'ne-NP (Nepali)'), ('nl', 'nl (Dutch)'), ('nn-no', 'nn-NO (Norwegian (Nynorsk))'), ('nr', 'nr (Ndebele, South)'), ('nso', 'nso (Northern Sotho)'), ('oc', 'oc (Occitan (Lengadocian))'), ('or', 'or (Oriya)'), ('pa', 'pa (Punjabi)'), ('pa-in', 'pa-IN (Punjabi (India))'), ('pl', 'pl (Polish)'), ('pt-br', 'pt-BR (Portuguese (Brazilian))'), ('pt-pt', 'pt-PT (Portuguese (Portugal))'), ('rm', 'rm (Romansh)'), ('ro', 'ro (Romanian)'), ('ru', 'ru (Russian)'), ('rw', 'rw (Kinyarwanda)'), ('sa', 'sa (Sanskrit)'), ('sah', 'sah (Sakha)'), ('sat', 'sat (Santali)'), ('si', 'si (Sinhala)'), ('sk', 'sk (Slovak)'), ('sl', 'sl (Slovenian)'), ('son', 'son (Songhai)'), ('sq', 'sq (Albanian)'), ('sr', 'sr (Serbian)'), ('sr-cyrl', 'sr-Cyrl (Serbian)'), ('sr-latn', 'sr-Latn (Serbian)'), ('ss', 'ss (Siswati)'), ('st', 'st (Southern Sotho)'), ('sv-se', 'sv-SE (Swedish)'), ('sw', 'sw (Swahili)'), ('ta', 'ta (Tamil)'), ('ta-in', 'ta-IN (Tamil (India))'), ('ta-lk', 'ta-LK (Tamil (Sri Lanka))'), ('te', 'te (Telugu)'), ('th', 'th (Thai)'), ('tl', 'tl (Tagalog)'), ('tn', 'tn (Tswana)'), ('tr', 'tr (Turkish)'), ('ts', 'ts (Tsonga)'), ('tsz', 'tsz (Pur\xe9pecha)'), ('tt-ru', 'tt-RU (Tatar)'), ('uk', 'uk (Ukrainian)'), ('ur', 'ur (Urdu)'), ('uz', 'uz (Uzbek)'), ('ve', 've (Venda)'), ('vi', 'vi (Vietnamese)'), ('wo', 'wo (Wolof)'), ('x-testing', 'x-testing (Testing)'), ('xh', 'xh (Xhosa)'), ('yo', 'yo (Yoruba)'), ('zh-cn', 'zh-CN (Chinese (Simplified))'), ('zh-tw', 'zh-TW (Chinese (Traditional))'), ('zu', 'zu (Zulu)')])),
                ('snippet', models.ForeignKey(related_name='locale_set', on_delete='models.CASCADE', to='base.Snippet')),
            ],
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SnippetTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('code', models.TextField(validators=[snippets.base.validators.validate_xml_template])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SnippetTemplateVariable',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('type', models.IntegerField(default=0, choices=[(4, b'Main Text'), (0, b'Text'), (2, b'Small Text'), (1, b'Image'), (3, b'Checkbox')])),
                ('description', models.TextField(default=b'', blank=True)),
                ('template', models.ForeignKey(related_name='variable_set', on_delete='models.PROTECT', to='base.SnippetTemplate')),
            ],
            options={
                'ordering': ('name',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TargetedCountry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(default='us', unique=True, max_length=16, verbose_name=b'Geolocation Country', choices=[('af', 'Afghanistan (af)'), ('al', 'Albania (al)'), ('dz', 'Algeria (dz)'), ('as', 'American Samoa (as)'), ('ad', 'Andorra (ad)'), ('ao', 'Angola (ao)'), ('ai', 'Anguilla (ai)'), ('aq', 'Antarctica (aq)'), ('ag', 'Antigua and Barbuda (ag)'), ('ar', 'Argentina (ar)'), ('am', 'Armenia (am)'), ('aw', 'Aruba (aw)'), ('au', 'Australia (au)'), ('at', 'Austria (at)'), ('az', 'Azerbaijan (az)'), ('bs', 'Bahamas (bs)'), ('bh', 'Bahrain (bh)'), ('bd', 'Bangladesh (bd)'), ('bb', 'Barbados (bb)'), ('by', 'Belarus (by)'), ('be', 'Belgium (be)'), ('bz', 'Belize (bz)'), ('bj', 'Benin (bj)'), ('bm', 'Bermuda (bm)'), ('bt', 'Bhutan (bt)'), ('bo', 'Bolivia (bo)'), ('ba', 'Bosnia and Herzegovina (ba)'), ('bw', 'Botswana (bw)'), ('bv', 'Bouvet Island (bv)'), ('br', 'Brazil (br)'), ('io', 'British Indian Ocean Territory (io)'), ('vg', 'British Virgin Islands (vg)'), ('bn', 'Brunei Darussalam (bn)'), ('bg', 'Bulgaria (bg)'), ('bf', 'Burkina Faso (bf)'), ('bi', 'Burundi (bi)'), ('kh', 'Cambodia (kh)'), ('cm', 'Cameroon (cm)'), ('ca', 'Canada (ca)'), ('cv', 'Cape Verde (cv)'), ('ky', 'Cayman Islands (ky)'), ('cf', 'Central African Republic (cf)'), ('td', 'Chad (td)'), ('cl', 'Chile (cl)'), ('cn', 'China (cn)'), ('cx', 'Christmas Island (cx)'), ('cc', 'Cocos (Keeling) Islands (cc)'), ('co', 'Colombia (co)'), ('km', 'Comoros (km)'), ('cg', 'Congo-Brazzaville (cg)'), ('cd', 'Congo-Kinshasa (cd)'), ('ck', 'Cook Islands (ck)'), ('cr', 'Costa Rica (cr)'), ('hr', 'Croatia (hr)'), ('cu', 'Cuba (cu)'), ('cy', 'Cyprus (cy)'), ('cz', 'Czech Republic (cz)'), ('dk', 'Denmark (dk)'), ('dj', 'Djibouti (dj)'), ('dm', 'Dominica (dm)'), ('do', 'Dominican Republic (do)'), ('ec', 'Ecuador (ec)'), ('eg', 'Egypt (eg)'), ('sv', 'El Salvador (sv)'), ('gq', 'Equatorial Guinea (gq)'), ('er', 'Eritrea (er)'), ('ee', 'Estonia (ee)'), ('et', 'Ethiopia (et)'), ('fk', 'Falkland Islands (Malvinas) (fk)'), ('fo', 'Faroe Islands (fo)'), ('fj', 'Fiji (fj)'), ('fi', 'Finland (fi)'), ('fr', 'France (fr)'), ('gf', 'French Guiana (gf)'), ('pf', 'French Polynesia (pf)'), ('tf', 'French Southern Territories (tf)'), ('ga', 'Gabon (ga)'), ('gm', 'Gambia (gm)'), ('ge', 'Georgia (ge)'), ('de', 'Germany (de)'), ('gh', 'Ghana (gh)'), ('gi', 'Gibraltar (gi)'), ('gr', 'Greece (gr)'), ('gl', 'Greenland (gl)'), ('gd', 'Grenada (gd)'), ('gp', 'Guadeloupe (gp)'), ('gu', 'Guam (gu)'), ('gt', 'Guatemala (gt)'), ('gg', 'Guernsey (gg)'), ('gn', 'Guinea (gn)'), ('gw', 'Guinea-Bissau (gw)'), ('gy', 'Guyana (gy)'), ('ht', 'Haiti (ht)'), ('hm', 'Heard Island and McDonald Islands (hm)'), ('hn', 'Honduras (hn)'), ('hk', 'Hong Kong (hk)'), ('hu', 'Hungary (hu)'), ('is', 'Iceland (is)'), ('in', 'India (in)'), ('id', 'Indonesia (id)'), ('ir', 'Iran (ir)'), ('iq', 'Iraq (iq)'), ('ie', 'Ireland (ie)'), ('im', 'Isle of Man (im)'), ('il', 'Israel (il)'), ('it', 'Italy (it)'), ('ci', 'Ivory Coast (ci)'), ('jm', 'Jamaica (jm)'), ('jp', 'Japan (jp)'), ('je', 'Jersey (je)'), ('jo', 'Jordan (jo)'), ('kz', 'Kazakhstan (kz)'), ('ke', 'Kenya (ke)'), ('ki', 'Kiribati (ki)'), ('kw', 'Kuwait (kw)'), ('kg', 'Kyrgyzstan (kg)'), ('la', 'Laos (la)'), ('lv', 'Latvia (lv)'), ('lb', 'Lebanon (lb)'), ('ls', 'Lesotho (ls)'), ('lr', 'Liberia (lr)'), ('ly', 'Libya (ly)'), ('li', 'Liechtenstein (li)'), ('lt', 'Lithuania (lt)'), ('lu', 'Luxembourg (lu)'), ('mo', 'Macao (mo)'), ('mk', 'Macedonia, F.Y.R. of (mk)'), ('mg', 'Madagascar (mg)'), ('mw', 'Malawi (mw)'), ('my', 'Malaysia (my)'), ('mv', 'Maldives (mv)'), ('ml', 'Mali (ml)'), ('mt', 'Malta (mt)'), ('mh', 'Marshall Islands (mh)'), ('mq', 'Martinique (mq)'), ('mr', 'Mauritania (mr)'), ('mu', 'Mauritius (mu)'), ('yt', 'Mayotte (yt)'), ('mx', 'Mexico (mx)'), ('fm', 'Micronesia (fm)'), ('md', 'Moldova (md)'), ('mc', 'Monaco (mc)'), ('mn', 'Mongolia (mn)'), ('me', 'Montenegro (me)'), ('ms', 'Montserrat (ms)'), ('ma', 'Morocco (ma)'), ('mz', 'Mozambique (mz)'), ('mm', 'Myanmar (mm)'), ('na', 'Namibia (na)'), ('nr', 'Nauru (nr)'), ('np', 'Nepal (np)'), ('nl', 'Netherlands (nl)'), ('an', 'Netherlands Antilles (an)'), ('nc', 'New Caledonia (nc)'), ('nz', 'New Zealand (nz)'), ('ni', 'Nicaragua (ni)'), ('ne', 'Niger (ne)'), ('ng', 'Nigeria (ng)'), ('nu', 'Niue (nu)'), ('nf', 'Norfolk Island (nf)'), ('kp', 'North Korea (kp)'), ('mp', 'Northern Mariana Islands (mp)'), ('no', 'Norway (no)'), ('ps', 'Occupied Palestinian Territory (ps)'), ('om', 'Oman (om)'), ('pk', 'Pakistan (pk)'), ('pw', 'Palau (pw)'), ('pa', 'Panama (pa)'), ('pg', 'Papua New Guinea (pg)'), ('py', 'Paraguay (py)'), ('pe', 'Peru (pe)'), ('ph', 'Philippines (ph)'), ('pn', 'Pitcairn (pn)'), ('pl', 'Poland (pl)'), ('pt', 'Portugal (pt)'), ('pr', 'Puerto Rico (pr)'), ('qa', 'Qatar (qa)'), ('re', 'Reunion (re)'), ('ro', 'Romania (ro)'), ('ru', 'Russian Federation (ru)'), ('rw', 'Rwanda (rw)'), ('bl', 'Saint Barth\xe9lemy (bl)'), ('sh', 'Saint Helena (sh)'), ('kn', 'Saint Kitts and Nevis (kn)'), ('lc', 'Saint Lucia (lc)'), ('mf', 'Saint Martin (mf)'), ('pm', 'Saint Pierre and Miquelon (pm)'), ('vc', 'Saint Vincent and the Grenadines (vc)'), ('ws', 'Samoa (ws)'), ('sm', 'San Marino (sm)'), ('st', 'Sao Tome and Principe (st)'), ('sa', 'Saudi Arabia (sa)'), ('sn', 'Senegal (sn)'), ('rs', 'Serbia (rs)'), ('sc', 'Seychelles (sc)'), ('sl', 'Sierra Leone (sl)'), ('sg', 'Singapore (sg)'), ('sk', 'Slovakia (sk)'), ('si', 'Slovenia (si)'), ('sb', 'Solomon Islands (sb)'), ('so', 'Somalia (so)'), ('za', 'South Africa (za)'), ('gs', 'South Georgia and the South Sandwich Islands (gs)'), ('kr', 'South Korea (kr)'), ('es', 'Spain (es)'), ('lk', 'Sri Lanka (lk)'), ('sd', 'Sudan (sd)'), ('sr', 'Suriname (sr)'), ('sj', 'Svalbard and Jan Mayen (sj)'), ('sz', 'Swaziland (sz)'), ('se', 'Sweden (se)'), ('ch', 'Switzerland (ch)'), ('sy', 'Syria (sy)'), ('tw', 'Taiwan (tw)'), ('tj', 'Tajikistan (tj)'), ('tz', 'Tanzania (tz)'), ('th', 'Thailand (th)'), ('tl', 'Timor-Leste (tl)'), ('tg', 'Togo (tg)'), ('tk', 'Tokelau (tk)'), ('to', 'Tonga (to)'), ('tt', 'Trinidad and Tobago (tt)'), ('tn', 'Tunisia (tn)'), ('tr', 'Turkey (tr)'), ('tm', 'Turkmenistan (tm)'), ('tc', 'Turks and Caicos Islands (tc)'), ('tv', 'Tuvalu (tv)'), ('ae', 'U.A.E. (ae)'), ('vi', 'U.S. Virgin Islands (vi)'), ('ug', 'Uganda (ug)'), ('ua', 'Ukraine (ua)'), ('gb', 'United Kingdom (gb)'), ('us', 'United States (us)'), ('um', 'United States Minor Outlying Islands (um)'), ('uy', 'Uruguay (uy)'), ('uz', 'Uzbekistan (uz)'), ('vu', 'Vanuatu (vu)'), ('va', 'Vatican City (va)'), ('ve', 'Venezuela (ve)'), ('vn', 'Vietnam (vn)'), ('wf', 'Wallis and Futuna (wf)'), ('eh', 'Western Sahara (eh)'), ('ye', 'Yemen (ye)'), ('zm', 'Zambia (zm)'), ('zw', 'Zimbabwe (zw)'), ('ax', '\xc5land Islands (ax)')])),
            ],
            options={
                'ordering': ('id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.FileField(storage=snippets.base.storage.OverwriteStorage(), upload_to=snippets.base.models._generate_filename)),
                ('name', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='snippet',
            name='countries',
            field=models.ManyToManyField(to='base.TargetedCountry', verbose_name=b'Targeted Countries', blank=True),
        ),
        migrations.AddField(
            model_name='snippet',
            name='exclude_from_search_providers',
            field=models.ManyToManyField(to='base.SearchProvider', verbose_name=b'Excluded Search Providers', blank=True),
        ),
        migrations.AddField(
            model_name='snippet',
            name='template',
            field=models.ForeignKey(to='base.SnippetTemplate', on_delete='models.PROTECT'),
        ),
        migrations.AddField(
            model_name='jsonsnippet',
            name='countries',
            field=models.ManyToManyField(to='base.TargetedCountry', verbose_name=b'Targeted Countries', blank=True),
        ),
    ]
