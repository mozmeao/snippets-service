from django.contrib import admin
from django.db.models import TextField, Q

from django_ace import AceWidget
from jingo import env, load_helpers
from jinja2.meta import find_undeclared_variables

from snippets.base import forms, models


class SnippetAdmin(admin.ModelAdmin):
    form = forms.SnippetAdminForm

    list_display = ('name', 'priority', 'disabled', 'publish_start',
                    'publish_end', 'modified')
    list_filter = ('disabled', 'client_match_rules')
    list_editable = ('disabled', 'priority', 'publish_start', 'publish_end')

    readonly_fields = ('created', 'modified')
    save_on_top = True
    search_fields = ('name', 'client_match_rules__description',
                     'template__name')

    filter_horizontal = ('client_match_rules',)

    fieldsets = (
        (None, {'fields': ('name', 'priority', 'disabled',
                           'created', 'modified')}),
        ('Content', {
            'fields': ('template', 'data'),
        }),
        ('Publish Duration', {
            'description': 'When will this snippet be available? (Optional)',
            'fields': ('publish_start', 'publish_end'),
        }),
        ('Products', {
            'fields': (('on_firefox', 'on_fennec'),)
        }),
        ('Product channels', {
            'description': 'What channels will this snippet be available in?',
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly'),)
        }),
        ('Startpage Versions', {
            'fields': (('on_startpage_1', 'on_startpage_2', 'on_startpage_3',
                        'on_startpage_4'),),
            'classes': ('collapse',)
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
            'classes': ('collapse',)
        }),
    )
admin.site.register(models.Snippet, SnippetAdmin)


class ClientMatchRuleAdmin(admin.ModelAdmin):
    list_display = ('description', 'startpage_version', 'name',
                    'version', 'locale', 'appbuildid', 'build_target',
                    'channel', 'os_version', 'distribution', 'distribution_version',
                    'modified')
    list_filter = ('name', 'version', 'os_version', 'appbuildid', 'build_target',
                   'channel', 'distribution', 'locale')
    save_on_top = True
    search_fields = ('description',)
admin.site.register(models.ClientMatchRule, ClientMatchRuleAdmin)


class SnippetTemplateVariableInline(admin.TabularInline):
    model = models.SnippetTemplateVariable
    max_num = 0
    can_delete = False
    readonly_fields = ('name',)
    fields = ('name', 'type',)


RESERVED_VARIABLES = ('_',)


class SnippetTemplateAdmin(admin.ModelAdmin):
    save_on_top = True
    inlines = (SnippetTemplateVariableInline,)
    formfield_overrides = {
        TextField: {'widget': AceWidget(mode='html', theme='github', attrs={'cols': 500})},
    }

    class Media:
        css = {
            'all': ('css/admin.css',)
        }

    def save_related(self, request, form, formsets, change):
        """
        After saving the related objects, remove and add
        SnippetTemplateVariables depending on how the template code changed.
        """
        super(SnippetTemplateAdmin, self).save_related(request, form, formsets,
                                                       change)
        load_helpers()  # Ensure jingo helpers are loaded.

        # Parse the template code and find any undefined variables.
        ast = env.parse(form.instance.code)
        new_vars = find_undeclared_variables(ast)
        var_manager = form.instance.variable_set

        # Filter out reserved variable names.
        new_vars = filter(lambda x: not x in RESERVED_VARIABLES, new_vars)

        # Delete variables not in the new set.
        var_manager.filter(~Q(name__in=new_vars)).delete()

        # Create variables that don't exist.
        for variable in new_vars:
            var_manager.get_or_create(name=variable)
admin.site.register(models.SnippetTemplate, SnippetTemplateAdmin)
