# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding M2M table for field countries on 'JSONSnippet'
        db.create_table(u'base_jsonsnippet_countries', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('jsonsnippet', models.ForeignKey(orm[u'base.jsonsnippet'], null=False)),
            ('targetedcountry', models.ForeignKey(orm[u'base.targetedcountry'], null=False))
        ))
        db.create_unique(u'base_jsonsnippet_countries', ['jsonsnippet_id', 'targetedcountry_id'])


    def backwards(self, orm):
        # Removing M2M table for field countries on 'JSONSnippet'
        db.delete_table('base_jsonsnippet_countries')


    models = {
        u'base.clientmatchrule': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'ClientMatchRule'},
            'appbuildid': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'build_target': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'channel': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'distribution': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'distribution_version': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_exclusion': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locale': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'os_version': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'startpage_version': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'}),
            'version': ('snippets.base.fields.RegexField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'base.jsonsnippet': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'JSONSnippet'},
            'client_match_rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.ClientMatchRule']", 'symmetrical': 'False', 'blank': 'True'}),
            'countries': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.TargetedCountry']", 'symmetrical': 'False', 'blank': 'True'}),
            'country': ('snippets.base.fields.CountryField', [], {'default': "''", 'max_length': '16', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'icon': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'on_aurora': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_beta': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_nightly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_release': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_1': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'publish_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'publish_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        },
        u'base.jsonsnippetlocale': {
            'Meta': {'object_name': 'JSONSnippetLocale'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('snippets.base.fields.LocaleField', [], {'default': "'en-US'", 'max_length': '32'}),
            'snippet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locale_set'", 'to': u"orm['base.JSONSnippet']"})
        },
        u'base.searchprovider': {
            'Meta': {'ordering': "('id',)", 'object_name': 'SearchProvider'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'base.snippet': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'Snippet'},
            'client_match_rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.ClientMatchRule']", 'symmetrical': 'False', 'blank': 'True'}),
            'countries': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.TargetedCountry']", 'symmetrical': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exclude_from_search_providers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.SearchProvider']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'on_aurora': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_beta': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_nightly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_release': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_1': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_startpage_2': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_3': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_4': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'publish_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'publish_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.SnippetTemplate']"}),
            'weight': ('django.db.models.fields.IntegerField', [], {'default': '100'})
        },
        u'base.snippetlocale': {
            'Meta': {'object_name': 'SnippetLocale'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('snippets.base.fields.LocaleField', [], {'default': "'en-US'", 'max_length': '32'}),
            'snippet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locale_set'", 'to': u"orm['base.Snippet']"})
        },
        u'base.snippettemplate': {
            'Meta': {'object_name': 'SnippetTemplate'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'base.snippettemplatevariable': {
            'Meta': {'object_name': 'SnippetTemplateVariable'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'variable_set'", 'to': u"orm['base.SnippetTemplate']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'base.targetedcountry': {
            'Meta': {'ordering': "('id',)", 'object_name': 'TargetedCountry'},
            'code': ('snippets.base.fields.CountryField', [], {'default': "u'us'", 'unique': 'True', 'max_length': '16'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'base.uploadedfile': {
            'Meta': {'object_name': 'UploadedFile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['base']