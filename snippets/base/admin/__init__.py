from django.contrib import admin

from snippets.base import models

from .adminmodels import (ClientMatchRuleAdmin, LogEntryAdmin, SnippetTemplateAdmin,
                          UploadedFileAdmin)
from .legacy import (SnippetAdmin, JSONSnippetAdmin, SearchProviderAdmin, TargetedCountryAdmin,
                     TargetedLocaleAdmin)


# Legacy
admin.site.register(models.Snippet, SnippetAdmin)
admin.site.register(models.JSONSnippet, JSONSnippetAdmin)
admin.site.register(models.SearchProvider, SearchProviderAdmin)
admin.site.register(models.TargetedCountry, TargetedCountryAdmin)
admin.site.register(models.TargetedLocale, TargetedLocaleAdmin)

# Current
admin.site.register(models.ClientMatchRule, ClientMatchRuleAdmin)
admin.site.register(admin.models.LogEntry, LogEntryAdmin)
admin.site.register(models.SnippetTemplate, SnippetTemplateAdmin)
admin.site.register(models.UploadedFile, UploadedFileAdmin)
