from django.db import transaction


@transaction.atomic
def duplicate_snippets_action(modeladmin, request, queryset):
    for snippet in queryset:
        snippet.duplicate(request.user)
duplicate_snippets_action.short_description = 'Duplicate selected snippets'  # noqa
