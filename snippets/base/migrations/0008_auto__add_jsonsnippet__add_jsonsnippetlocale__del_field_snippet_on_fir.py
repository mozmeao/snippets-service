# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'JSONSnippet'
        db.create_table('base_jsonsnippet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('priority', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('disabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('icon', self.gf('django.db.models.fields.TextField')()),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('country', self.gf('snippets.base.fields.CountryField')(default='', max_length=16, blank=True)),
            ('publish_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('publish_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('on_release', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('on_beta', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('on_aurora', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('on_nightly', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('on_startpage_1', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('base', ['JSONSnippet'])

        # Adding M2M table for field client_match_rules on 'JSONSnippet'
        db.create_table('base_jsonsnippet_client_match_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('jsonsnippet', models.ForeignKey(orm['base.jsonsnippet'], null=False)),
            ('clientmatchrule', models.ForeignKey(orm['base.clientmatchrule'], null=False))
        ))
        db.create_unique('base_jsonsnippet_client_match_rules', ['jsonsnippet_id', 'clientmatchrule_id'])

        # Adding model 'JSONSnippetLocale'
        db.create_table('base_jsonsnippetlocale', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('snippet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='locale_set', to=orm['base.JSONSnippet'])),
            ('locale', self.gf('snippets.base.fields.LocaleField')(default='en-US', max_length=32)),
        ))
        db.send_create_signal('base', ['JSONSnippetLocale'])

        # Deleting field 'Snippet.on_firefox'
        db.delete_column('base_snippet', 'on_firefox')

        # Deleting field 'Snippet.on_fennec'
        db.delete_column('base_snippet', 'on_fennec')


    def backwards(self, orm):
        # Deleting model 'JSONSnippet'
        db.delete_table('base_jsonsnippet')

        # Removing M2M table for field client_match_rules on 'JSONSnippet'
        db.delete_table('base_jsonsnippet_client_match_rules')

        # Deleting model 'JSONSnippetLocale'
        db.delete_table('base_jsonsnippetlocale')

        # Adding field 'Snippet.on_firefox'
        db.add_column('base_snippet', 'on_firefox',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'Snippet.on_fennec'
        db.add_column('base_snippet', 'on_fennec',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


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
        'base.jsonsnippet': {
            'Meta': {'ordering': "('-modified',)", 'object_name': 'JSONSnippet'},
            'client_match_rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['base.ClientMatchRule']", 'symmetrical': 'False', 'blank': 'True'}),
            'country': ('snippets.base.fields.CountryField', [], {'default': "''", 'max_length': '16', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'icon': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
            'url': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'base.jsonsnippetlocale': {
            'Meta': {'object_name': 'JSONSnippetLocale'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('snippets.base.fields.LocaleField', [], {'default': "'en-US'", 'max_length': '32'}),
            'snippet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locale_set'", 'to': "orm['base.JSONSnippet']"})
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