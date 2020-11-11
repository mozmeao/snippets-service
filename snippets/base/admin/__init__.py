from django.contrib import admin

from snippets.base import models

import snippets.base.admin.adminmodels as adminmodels

admin.site.register(models.Addon, adminmodels.AddonAdmin)
admin.site.register(models.ASRSnippet, adminmodels.ASRSnippetAdmin)
admin.site.register(models.Campaign, adminmodels.CampaignAdmin)
admin.site.register(models.Category, adminmodels.CategoryAdmin)
admin.site.register(models.Product, adminmodels.ProductAdmin)
admin.site.register(admin.models.LogEntry, adminmodels.LogEntryAdmin)
admin.site.register(models.Target, adminmodels.TargetAdmin)
admin.site.register(models.Icon, adminmodels.IconAdmin)
admin.site.register(models.Locale, adminmodels.LocaleAdmin)
admin.site.register(models.Job, adminmodels.JobAdmin)
admin.site.register(models.Distribution, adminmodels.DistributionAdmin)
admin.site.register(models.DistributionBundle, adminmodels.DistributionBundleAdmin)
admin.site.register(models.JobDailyPerformance, adminmodels.JobDailyPerformanceAdmin)
admin.site.register(models.DailyImpressions, adminmodels.DailyImpressionsAdmin)
