# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'SnippetTemplateVariable.description'
        db.add_column('base_snippettemplatevariable', 'description',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


        # Changing field 'Snippet.country'
        db.alter_column('base_snippet', 'country', self.gf('snippets.base.fields.CountryField')(max_length=16))

        # Changing field 'ClientMatchRule.appbuildid'
        db.alter_column('base_clientmatchrule', 'appbuildid', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.locale'
        db.alter_column('base_clientmatchrule', 'locale', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.distribution_version'
        db.alter_column('base_clientmatchrule', 'distribution_version', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.startpage_version'
        db.alter_column('base_clientmatchrule', 'startpage_version', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.os_version'
        db.alter_column('base_clientmatchrule', 'os_version', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.version'
        db.alter_column('base_clientmatchrule', 'version', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.distribution'
        db.alter_column('base_clientmatchrule', 'distribution', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.build_target'
        db.alter_column('base_clientmatchrule', 'build_target', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.channel'
        db.alter_column('base_clientmatchrule', 'channel', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.name'
        db.alter_column('base_clientmatchrule', 'name', self.gf('snippets.base.fields.RegexField')(max_length=64))

        # Changing field 'SnippetLocale.locale'
        db.alter_column('base_snippetlocale', 'locale', self.gf('snippets.base.fields.LocaleField')(max_length=32))

    def backwards(self, orm):
        # Deleting field 'SnippetTemplateVariable.description'
        db.delete_column('base_snippettemplatevariable', 'description')


        # Changing field 'Snippet.country'
        db.alter_column('base_snippet', 'country', self.gf('snippets.base.models.CountryField')(max_length=16))

        # Changing field 'ClientMatchRule.appbuildid'
        db.alter_column('base_clientmatchrule', 'appbuildid', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.locale'
        db.alter_column('base_clientmatchrule', 'locale', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.distribution_version'
        db.alter_column('base_clientmatchrule', 'distribution_version', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.startpage_version'
        db.alter_column('base_clientmatchrule', 'startpage_version', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.os_version'
        db.alter_column('base_clientmatchrule', 'os_version', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.version'
        db.alter_column('base_clientmatchrule', 'version', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.distribution'
        db.alter_column('base_clientmatchrule', 'distribution', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.build_target'
        db.alter_column('base_clientmatchrule', 'build_target', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.channel'
        db.alter_column('base_clientmatchrule', 'channel', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'ClientMatchRule.name'
        db.alter_column('base_clientmatchrule', 'name', self.gf('snippets.base.models.RegexField')(max_length=64))

        # Changing field 'SnippetLocale.locale'
        db.alter_column('base_snippetlocale', 'locale', self.gf('snippets.base.models.LocaleField')(max_length=32))

    models = {
        'base.clientmatchrule': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'ClientMatchRule'},
            'appbuildid': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'build_target': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'channel': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'distribution': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'distribution_version': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_exclusion': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locale': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'os_version': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'startpage_version': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'version': ('snippets.base.fields.RegexField', [], {'max_length': '64', 'blank': 'True'})
        },
        'base.snippet': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'Snippet'},
            'client_match_rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['base.ClientMatchRule']", 'symmetrical': 'False', 'blank': 'True'}),
            'country': ('snippets.base.fields.CountryField', [], {'default': "''", 'max_length': '16', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'on_aurora': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_beta': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_fennec': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_firefox': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_nightly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_release': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_1': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'on_startpage_2': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_3': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'on_startpage_4': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'publish_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'publish_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['base.SnippetTemplate']"})
        },
        'base.snippetlocale': {
            'Meta': {'object_name': 'SnippetLocale'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('snippets.base.fields.LocaleField', [], {'default': "'en-US'", 'max_length': '32'}),
            'snippet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locale_set'", 'to': "orm['base.Snippet']"})
        },
        'base.snippettemplate': {
            'Meta': {'object_name': 'SnippetTemplate'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'base.snippettemplatevariable': {
            'Meta': {'object_name': 'SnippetTemplateVariable'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'variable_set'", 'to': "orm['base.SnippetTemplate']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['base']