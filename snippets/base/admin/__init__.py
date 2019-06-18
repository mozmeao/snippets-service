from django.contrib import admin

from snippets.base import models

from .adminmodels import (AddonAdmin, ASRSnippetAdmin, CampaignAdmin, CategoryAdmin,
                          ClientMatchRuleAdmin, LogEntryAdmin, IconAdmin,
                          SnippetTemplateAdmin, TargetAdmin, LocaleAdmin)
from .legacy import (SnippetAdmin, SearchProviderAdmin, TargetedCountryAdmin,
                     TargetedLocaleAdmin)


# Legacy
admin.site.register(models.Snippet, SnippetAdmin)
admin.site.register(models.SearchProvider, SearchProviderAdmin)
admin.site.register(models.TargetedCountry, TargetedCountryAdmin)
admin.site.register(models.TargetedLocale, TargetedLocaleAdmin)

# Current
admin.site.register(models.Addon, AddonAdmin)
admin.site.register(models.ASRSnippet, ASRSnippetAdmin)
admin.site.register(models.Campaign, CampaignAdmin)
admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.ClientMatchRule, ClientMatchRuleAdmin)
admin.site.register(admin.models.LogEntry, LogEntryAdmin)
admin.site.register(models.SnippetTemplate, SnippetTemplateAdmin)
admin.site.register(models.Target, TargetAdmin)
admin.site.register(models.Icon, IconAdmin)
admin.site.register(models.Locale, LocaleAdmin)
