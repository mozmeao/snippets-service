# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SnippetLocale'
        db.create_table('base_snippetlocale', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('snippet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='locale_set', to=orm['base.Snippet'])),
            ('locale', self.gf('snippets.base.models.LocaleField')(default='en-US', max_length=32)),
        ))
        db.send_create_signal('base', ['SnippetLocale'])

        # Adding field 'Snippet.country'
        db.add_column('base_snippet', 'country',
                      self.gf('snippets.base.models.CountryField')(default='', max_length=16, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'SnippetLocale'
        db.delete_table('base_snippetlocale')

        # Deleting field 'Snippet.country'
        db.delete_column('base_snippet', 'country')


    models = {
        'base.clientmatchrule': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'ClientMatchRule'},
            'appbuildid': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'build_target': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'channel': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'distribution': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'distribution_version': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_exclusion': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'locale': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'os_version': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'startpage_version': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'}),
            'version': ('snippets.base.models.RegexField', [], {'max_length': '64', 'blank': 'True'})
        },
        'base.snippet': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'Snippet'},
            'client_match_rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['base.ClientMatchRule']", 'symmetrical': 'False', 'blank': 'True'}),
            'country': ('snippets.base.models.CountryField', [], {'default': "''", 'max_length': '16', 'blank': 'True'}),
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
            'locale': ('snippets.base.models.LocaleField', [], {'default': "'en-US'", 'max_length': '32'}),
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'variable_set'", 'to': "orm['base.SnippetTemplate']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['base']