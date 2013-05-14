from django.contrib import admin

from snippets.base import models


class SnippetAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'disabled', 'publish_start',
                    'publish_end', 'created', 'modified')
    list_filter = ('disabled', 'client_match_rules')
    readonly_fields = ('created', 'modified')

    filter_horizontal = ('client_match_rules',)

    fieldsets = (
        (None, {'fields': ('name', 'body', 'priority', 'disabled',
                           'created', 'modified')}),
        ('Publish Duration', {
            'description': 'When will this snippet be available? (Optional)',
            'fields': ('publish_start', 'publish_end'),
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
        }),
    )
admin.site.register(models.Snippet, SnippetAdmin)


class ClientMatchRuleAdmin(admin.ModelAdmin):
    pass
admin.site.register(models.ClientMatchRule, ClientMatchRuleAdmin)
