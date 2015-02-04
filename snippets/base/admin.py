import json
import re
from textwrap import wrap

from django.contrib import admin
from django.db import transaction
from django.db.models import TextField, Q

from django_ace import AceWidget
from jingo import env, load_helpers
from jinja2.meta import find_undeclared_variables

from snippets.base import LANGUAGE_VALUES, forms, models


MATCH_LOCALE_REGEX = re.compile('(\w+(?:-\w+)*)')


@transaction.commit_on_success
def cmr_to_locales_action(modeladmin, request, queryset):
    """Convert Locale ClientMatchRules to the new Locale format.

    If the ClientMatchRule only defines Locale and we successfully
    migrate that value to the new Locale format, we remove the rule
    from the snippet.

    """
    for snippet in queryset:
        snippet.locale_set.all().delete()
        for cmr in snippet.client_match_rules.exclude(locale=''):
            if cmr.is_exclusion:
                for locale in LANGUAGE_VALUES:
                    models.SnippetLocale.objects.create(snippet=snippet,
                                                        locale=locale)

            for locale in re.findall(MATCH_LOCALE_REGEX, cmr.locale):
                locale = locale.lower()
                if locale not in LANGUAGE_VALUES:
                    continue
                if cmr.is_exclusion:
                    snippet.locale_set.filter(locale=locale).delete()
                else:
                    models.SnippetLocale.objects.create(snippet=snippet,
                                                        locale=locale)

            cmr.locale = ''
            for field in models.Client._fields:
                if getattr(cmr, field, False):
                    break
            else:
                snippet.client_match_rules.remove(cmr)

cmr_to_locales_action.short_description = ('Convert ClientMatchRules '
                                           'to Locale Rules')



@transaction.commit_on_success
def duplicate_snippets_action(modeladmin, request, queryset):
    for snippet in queryset:
        snippet.duplicate()
duplicate_snippets_action.short_description = 'Duplicate selected snippets'



class TemplateNameFilter(admin.AllValuesFieldListFilter):
    def __init__(self, *args, **kwargs):
        super(TemplateNameFilter, self).__init__(*args, **kwargs)
        self.title = 'template'


class BaseModelAdmin(admin.ModelAdmin):
    """Holds customizations shared by every ModelAdmin in the site."""
    change_list_template = 'smuggler/change_list.html'


class BaseSnippetAdmin(BaseModelAdmin):

    list_display = (
        'name',
        'id',
        'disabled',
        'text',
        'locales',
        'publish_start',
        'publish_end',
        'modified',
    )
    list_filter = (
        'disabled',
        'on_release',
        'on_beta',
        'on_aurora',
        'on_nightly',
        'locale_set__locale',
        'client_match_rules',
    )
    list_editable = (
        'disabled',
        'publish_start',
        'publish_end'
    )

    readonly_fields = ('created', 'modified')
    save_on_top = True
    save_as = True

    filter_horizontal = ('client_match_rules',)
    actions = (duplicate_snippets_action,)

    def save_model(self, request, obj, form, change):
        """Save locale changes as well as the snippet itself."""
        super(BaseSnippetAdmin, self).save_model(request, obj, form, change)

        try:
            locales = form.cleaned_data['locales']
            obj.locale_set.all().delete()
            for locale in locales:
                obj.locale_set.create(locale=locale)
        except KeyError:
            pass  # If the locales weren't even specified, do nothing.

    def change_view(self, request, *args, **kwargs):
        if request.method == 'POST' and '_saveasnew' in request.POST:
            # Always saved cloned snippets as disabled.
            request.POST['disabled'] = u'on'
        return super(BaseSnippetAdmin, self).change_view(request, *args, **kwargs)

    def locales(self, obj):
        return ', '.join([locale.get_locale_display() for locale in obj.locale_set.all()])


class SnippetAdmin(BaseSnippetAdmin):
    form = forms.SnippetAdminForm

    search_fields = ('name', 'client_match_rules__description',
                     'template__name')
    list_filter = BaseSnippetAdmin.list_filter + (
        'template',
        'exclude_from_search_providers',
    )
    filter_horizontal = ('exclude_from_search_providers', 'client_match_rules',)

    fieldsets = (
        (None, {'fields': ('name', 'priority', 'disabled',
                           'created', 'modified')}),
        ('Content', {
            'fields': ('template', 'data'),
        }),
        ('Publish Duration', {
            'description': ('When will this snippet be available? (Optional)'
                            '<br>Publish times are in UTC. '
                            '<a href="http://time.is/UTC" target="_blank">'
                            'Click here to see the current time in UTC</a>.'),
            'fields': ('publish_start', 'publish_end'),
        }),
        ('Prevalence', {
            'fields': ('weight',)
        }),
        ('Product channels', {
            'description': 'What channels will this snippet be available in?',
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly'),)
        }),
        ('Search Providers', {
            'description': 'Would you like to <strong>exclude</strong> any search providers from this snippet?',
            'fields': (('exclude_from_search_providers',),)
        }),
        ('Country and Locale', {
            'description': ('What country and locales will this snippet be '
                            'available in?'),
            'fields': (('country', 'locales'))
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
        }),
        ('Startpage Versions', {
            'fields': (('on_startpage_1', 'on_startpage_2', 'on_startpage_3',
                        'on_startpage_4'),),
            'classes': ('collapse',)
        }),
    )

    actions = (cmr_to_locales_action, duplicate_snippets_action)

    class Media:
        css = {
            'all': ('css/admin.css',)
        }

    def lookup_allowed(self, key, value):
        if key == 'template__name':
            return True
        return super(SnippetAdmin, self).lookup_allowed(key, value)

    def text(self, obj):
        text = []
        data = json.loads(obj.data)
        text_keys = (obj.template.variable_set
                        .filter(type=models.SnippetTemplateVariable.TEXT)
                        .values_list('name', flat=True))

        return ' '.join(wrap('\n'.join([data[key][:500] for key in text_keys if data.get(key)])))


class ClientMatchRuleAdmin(BaseModelAdmin):
    list_display = ('description', 'is_exclusion', 'startpage_version', 'name',
                    'version', 'locale', 'appbuildid', 'build_target',
                    'channel', 'os_version', 'distribution',
                    'distribution_version', 'modified')
    list_filter = ('name', 'version', 'os_version', 'appbuildid',
                   'build_target', 'channel', 'distribution', 'locale')
    save_on_top = True
    search_fields = ('description',)


class SnippetTemplateVariableInline(admin.TabularInline):
    model = models.SnippetTemplateVariable
    max_num = 0
    can_delete = False
    readonly_fields = ('name',)
    fields = ('name', 'type', 'description')


RESERVED_VARIABLES = ('_', 'snippet_id')


class SnippetTemplateAdmin(BaseModelAdmin):
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
            models.SnippetTemplateVariable.objects.get_or_create(
                template=form.instance, name=variable)


class JSONSnippetAdmin(BaseSnippetAdmin):
    form = forms.JSONSnippetAdminForm
    search_fields = ('name', 'client_match_rules__description')

    fieldsets = (
        (None, {'fields': ('name', 'priority', 'disabled',
                           'created', 'modified')}),
        ('Content', {
            'fields': ('icon', 'text', 'url'),
        }),
        ('Publish Duration', {
            'description': ('When will this snippet be available? (Optional)'
                            '<br>Publish times are in UTC. '
                            '<a href="http://time.is/UTC" target="_blank">'
                            'Click here to see the current time in UTC</a>.'),
            'fields': ('publish_start', 'publish_end'),
        }),
        ('Prevalence', {
            'fields': ('weight',)
        }),
        ('Product channels', {
            'description': 'What channels will this snippet be available in?',
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly'),)
        }),
        ('Country and Locale', {
            'description': ('What country and locales will this snippet be '
                            'available in?'),
            'fields': (('country', 'locales'))
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
        }),
        ('Startpage Versions', {
            'fields': (('on_startpage_1',),),
            'classes': ('collapse',)
        }),
    )


class UploadedFileAdmin(admin.ModelAdmin):
    readonly_fields = ('url', 'preview', 'snippets')
    list_display = ('name', 'url', 'preview', 'modified')
    prepopulated_fields = {'name': ('file',)}
    form = forms.UploadedFileAdminForm

    def preview(self, obj):
        template = env.get_template('base/uploadedfile_preview.html')
        return template.render({'file': obj})
    preview.allow_tags = True

    def snippets(self, obj):
        """Snippets using this file."""
        template = env.get_template('base/uploadedfile_snippets.html')
        return template.render({'snippets': obj.snippets})
    snippets.allow_tags = True


class SearchProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier')


admin.site.register(models.Snippet, SnippetAdmin)
admin.site.register(models.ClientMatchRule, ClientMatchRuleAdmin)
admin.site.register(models.SnippetTemplate, SnippetTemplateAdmin)
admin.site.register(models.JSONSnippet, JSONSnippetAdmin)
admin.site.register(models.UploadedFile, UploadedFileAdmin)
admin.site.register(models.SearchProvider, SearchProviderAdmin)
