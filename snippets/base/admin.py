import re
from datetime import datetime, timedelta

from django.contrib import admin
from django.db import transaction
from django.db.models import TextField, Q
from django.template.loader import get_template
from django.utils.encoding import force_text

from advanced_filters.admin import AdminAdvancedFiltersMixin
from django_ace import AceWidget
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django_statsd.clients import statsd
from jinja2.meta import find_undeclared_variables
from reversion.admin import VersionAdmin
from quickedit.admin import QuickEditAdmin

from snippets.base import forms, models
from snippets.base.models import JINJA_ENV


MATCH_LOCALE_REGEX = re.compile('(\w+(?:-\w+)*)')
RESERVED_VARIABLES = ('_', 'snippet_id')


@transaction.atomic
def duplicate_snippets_action(modeladmin, request, queryset):
    for snippet in queryset:
        snippet.duplicate()
duplicate_snippets_action.short_description = 'Duplicate selected snippets'  # noqa


class ModifiedFilter(admin.SimpleListFilter):
    title = 'Last modified'
    parameter_name = 'last_modified'

    def lookups(self, request, model_admin):
        return (
            ('24', '24 hours'),
            ('168', '7 days'),
            ('336', '14 days'),
            ('720', '30 days'),
            ('all', 'All'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value or value == 'all':
            return queryset

        when = datetime.utcnow() - timedelta(hours=int(value))
        return queryset.exclude(modified__lt=when)

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == force_text(lookup),
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }


class ReleaseFilter(admin.SimpleListFilter):
    title = 'Release'
    parameter_name = 'release'

    def lookups(self, request, model_admin):
        return (
            ('on_release', 'Release'),
            ('on_beta', 'Beta'),
            ('on_aurora', 'Aurora'),
            ('on_nightly', 'Nightly'),
            ('on_esr', 'ESR'),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        return queryset.filter(**{self.value(): True})


class TemplateNameFilter(admin.AllValuesFieldListFilter):
    def __init__(self, *args, **kwargs):
        super(TemplateNameFilter, self).__init__(*args, **kwargs)
        self.title = 'template'


class DefaultFilterMixIn(admin.ModelAdmin):
    def changelist_view(self, request, *args, **kwargs):
        if self.default_filters and not request.GET:
            q = request.GET.copy()
            for filtr in self.default_filters:
                key, value = filtr.split('=')
                q[key] = value
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(DefaultFilterMixIn, self).changelist_view(request, *args, **kwargs)


class BaseSnippetAdmin(AdminAdvancedFiltersMixin, VersionAdmin,
                       DefaultFilterMixIn, admin.ModelAdmin):
    default_filters = ('last_modified=336',)
    list_display_links = (
        'id',
        'name',
    )
    list_display = (
        'id',
        'name',
        'disabled',
        'locale_list',
        'modified',
    )
    list_editable = (
        'disabled',
    )
    readonly_fields = ('created', 'modified', 'uuid')
    save_on_top = True
    save_as = True

    filter_horizontal = ('client_match_rules', 'locales', 'countries')
    actions = (duplicate_snippets_action,)

    advanced_filter_fields = (
        ('name', 'Snippet Name'),
        'campaign',
        ('on_release', 'Channel Release'),
        ('on_beta', 'Channel Beta'),
        ('on_aurora', 'Channel Aurora'),
        ('on_nightly', 'Channel Nightly'),
        ('on_esr', 'Channel ESR'),
        ('on_startpage_4', 'Page About:Home'),
        ('on_startpage_5', 'Page Activity Stream'),
        ('countries__name', 'Country'),
        ('locales__name', 'Language'),
    )

    def change_view(self, request, *args, **kwargs):
        if request.method == 'POST' and '_saveasnew' in request.POST:
            # Always saved cloned snippets as disabled.
            post_data = request.POST.copy()
            post_data['disabled'] = u'on'
            request.POST = post_data
        return super(BaseSnippetAdmin, self).change_view(request, *args, **kwargs)

    def locale_list(self, obj):
        num_locales = obj.locales.count()
        locales = obj.locales.all()[:3]
        active_locales = ', '.join([str(locale) for locale in locales])
        if num_locales > 3:
            active_locales += ' and {0} more.'.format(num_locales - 3)
        return active_locales


class SnippetAdmin(QuickEditAdmin, BaseSnippetAdmin):
    def get_changelist_form(self, request, **kwargs):
        return forms.SnippetChangeListForm

    form = forms.SnippetAdminForm
    readonly_fields = BaseSnippetAdmin.readonly_fields + ('preview_url',)
    search_fields = ('name', 'client_match_rules__description',
                     'template__name', 'campaign')
    list_filter = (
        ModifiedFilter,
        'disabled',
        ReleaseFilter,
        ('locales', RelatedDropdownFilter),
        ('client_match_rules', RelatedDropdownFilter),
        ('template', RelatedDropdownFilter),
    )
    change_list_template = 'quickedit/change_list.html'
    quick_editable = (
        'name',
        'weight',
        'publish_start',
        'publish_end',
        'body',
    )
    filter_horizontal = (BaseSnippetAdmin.filter_horizontal +
                         ('exclude_from_search_providers', 'client_match_rules'))

    fieldsets = (
        (None, {'fields': ('name', 'disabled', 'campaign', 'preview_url', 'created', 'modified')}),
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
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly', 'on_esr'),)
        }),
        ('Startpage Versions', {
            'fields': (('on_startpage_1', 'on_startpage_2', 'on_startpage_3',
                        'on_startpage_4', 'on_startpage_5'),),
        }),
        ('Client Filtering', {
            'fields': (
                'client_option_version_lower_bound',
                'client_option_version_upper_bound',
                'client_option_has_fxaccount',
                'client_option_has_testpilot',
                'client_option_is_developer',
                'client_option_is_default_browser',
                'client_option_screen_resolutions',
                'client_option_sessionage_lower_bound',
                'client_option_sessionage_upper_bound',
                'client_option_profileage_lower_bound',
                'client_option_profileage_upper_bound',
                'client_option_addon_check_type',
                'client_option_addon_name',
            )
        }),
        ('Country and Locale', {
            'description': ('What countries and locales will this snippet be '
                            'available in?'),
            'fields': (('countries', 'locales'))
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
        }),
        ('Search Providers', {
            'description': ('Would you like to <strong>exclude</strong> '
                            'any search providers from this snippet?'),
            'fields': (('exclude_from_search_providers',),)
        }),
        ('Other Info', {
            'fields': (('uuid',),),
            'classes': ('collapse',)
        }),
    )

    actions = (duplicate_snippets_action,)

    class Media:
        css = {
            'all': ('css/admin.css',)
        }

    def save_model(self, request, obj, form, change):
        statsd.incr('save.snippet')
        super(SnippetAdmin, self).save_model(request, obj, form, change)

    def lookup_allowed(self, key, value):
        if key == 'template__name':
            return True
        return super(SnippetAdmin, self).lookup_allowed(key, value)

    def preview_url(self, obj):
        url = obj.get_preview_url()
        template = '<a href="{url}" target=_blank>{url}</a>'.format(url=url)
        return template
    preview_url.allow_tags = True

    def queryset(self, request):
        return (super(SnippetAdmin, self)
                .queryset(request).prefetch_related('locales').select_related('template'))


class ClientMatchRuleAdmin(VersionAdmin, admin.ModelAdmin):
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
    formset = forms.SnippetTemplateVariableInlineFormset
    max_num = 0
    can_delete = False
    readonly_fields = ('name',)
    fields = ('name', 'type', 'order', 'description')


class SnippetTemplateAdmin(VersionAdmin, admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'priority', 'hidden')
    list_filter = ('hidden',)
    inlines = (SnippetTemplateVariableInline,)
    formfield_overrides = {
        TextField: {'widget': AceWidget(mode='html', theme='github',
                                        width='1200px', height='500px')},
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

        # Parse the template code and find any undefined variables.
        ast = JINJA_ENV.env.parse(form.instance.code)
        new_vars = find_undeclared_variables(ast)
        var_manager = form.instance.variable_set

        # Filter out reserved variable names.
        new_vars = filter(lambda x: x not in RESERVED_VARIABLES, new_vars)

        # Delete variables not in the new set.
        var_manager.filter(~Q(name__in=new_vars)).delete()

        # Create variables that don't exist.
        for i, variable in enumerate(new_vars, start=1):
            obj, _ = models.SnippetTemplateVariable.objects.get_or_create(
                template=form.instance, name=variable)
            if obj.order == 0:
                obj.order = i * 10
                obj.save()


class JSONSnippetAdmin(BaseSnippetAdmin):
    form = forms.JSONSnippetAdminForm
    search_fields = ('name', 'client_match_rules__description')
    list_filter = (
        ModifiedFilter,
        'disabled',
        ReleaseFilter,
        ('locales', RelatedDropdownFilter),
        ('client_match_rules', RelatedDropdownFilter),
    )

    fieldsets = (
        (None, {'fields': ('name', 'disabled', 'created', 'modified')}),
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
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly', 'on_esr'),)
        }),
        ('Country and Locale', {
            'description': ('What country and locales will this snippet be '
                            'available in?'),
            'fields': (('countries', 'locales'))
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
        }),
        ('Startpage Versions', {
            'fields': (('on_startpage_1',),),
            'classes': ('collapse',)
        }),
        ('Other Info', {
            'fields': (('uuid',),),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        statsd.incr('save.json_snippet')
        super(JSONSnippetAdmin, self).save_model(request, obj, form, change)


class UploadedFileAdmin(admin.ModelAdmin):
    readonly_fields = ('url', 'preview', 'snippets')
    list_display = ('name', 'url', 'preview', 'modified')
    prepopulated_fields = {'name': ('file',)}
    form = forms.UploadedFileAdminForm

    def preview(self, obj):
        template = get_template('base/uploadedfile_preview.jinja')
        return template.render({'file': obj})
    preview.allow_tags = True

    def snippets(self, obj):
        """Snippets using this file."""
        template = get_template('base/uploadedfile_snippets.jinja')
        return template.render({'snippets': obj.snippets})
    snippets.allow_tags = True


class SearchProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier')


class TargetedCountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority')
    list_filter = ('priority',)
    list_editable = ('priority',)


class TargetedLocaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority')
    list_filter = ('priority',)
    list_editable = ('priority',)


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'object_repr', 'change_message')
    list_filter = ('user', 'content_type')


admin.site.register(models.Snippet, SnippetAdmin)
admin.site.register(models.ClientMatchRule, ClientMatchRuleAdmin)
admin.site.register(models.SnippetTemplate, SnippetTemplateAdmin)
admin.site.register(models.JSONSnippet, JSONSnippetAdmin)
admin.site.register(models.UploadedFile, UploadedFileAdmin)
admin.site.register(models.SearchProvider, SearchProviderAdmin)
admin.site.register(models.TargetedCountry, TargetedCountryAdmin)
admin.site.register(models.TargetedLocale, TargetedLocaleAdmin)
admin.site.register(admin.models.LogEntry, LogEntryAdmin)
