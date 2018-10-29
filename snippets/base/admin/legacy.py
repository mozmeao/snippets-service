from django.contrib import admin

from reversion.admin import VersionAdmin
from quickedit.admin import QuickEditAdmin
from django.utils.safestring import mark_safe

from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django_statsd.clients import statsd

from snippets.base import forms
from snippets.base.admin.actions import duplicate_snippets_action
from snippets.base.admin.filters import ModifiedFilter, ReleaseFilter


class BaseSnippetAdmin(VersionAdmin, admin.ModelAdmin):
    default_filters = ('last_modified=336',)
    list_display_links = (
        'id',
        'name',
    )
    list_display = (
        'id',
        'name',
        'published',
        'locale_list',
        'modified',
    )
    list_editable = (
        'published',
    )
    readonly_fields = ('created', 'modified', 'uuid')
    save_on_top = True
    save_as = True

    filter_horizontal = ('client_match_rules', 'locales', 'countries')
    actions = (duplicate_snippets_action,)

    def change_view(self, request, *args, **kwargs):
        if request.method == 'POST' and '_saveasnew' in request.POST:
            # Always saved cloned snippets as un-published and un-check ready for review.
            post_data = request.POST.copy()
            post_data.pop('published', None)
            post_data.pop('ready_for_review', None)
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
    form = forms.SnippetAdminForm
    readonly_fields = BaseSnippetAdmin.readonly_fields + ('preview_url', 'creator')
    search_fields = ('name', 'client_match_rules__description',
                     'template__name', 'campaign')
    list_filter = (
        ModifiedFilter,
        'published',
        'ready_for_review',
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
        (None, {'fields': ('creator', 'name', ('ready_for_review', 'published'), 'campaign',
                           'preview_url', 'created', 'modified')}),
        ('Content', {
            'description': ('In Activity Stream Templates you can use the special links:<br/>'
                            '<ol><li>about:accounts : To open Firefox Accounts</li>'
                            '<li>uitour:showMenu:appMenu : To open the hamburger menu</li></ol>'),
            'fields': ('template', 'data'),
        }),
        ('Publish Duration', {
            'description': ('When will this snippet be available? (Optional)'
                            '<br>Publish times are in UTC. '
                            '<a href="http://time.is/UTC" target="_blank" '
                            'rel="noopener noreferrer">'
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
                'client_option_is_developer',
                'client_option_is_default_browser',
                'client_option_screen_resolutions',
                'client_option_sessionage_lower_bound',
                'client_option_sessionage_upper_bound',
                'client_option_profileage_lower_bound',
                'client_option_profileage_upper_bound',
                'client_option_addon_check_type',
                'client_option_addon_name',
                'client_option_bookmarks_count_lower_bound',
                'client_option_bookmarks_count_upper_bound',
            )
        }),
        ('Country and Locale', {
            'description': ('What countries and locales will this snippet be '
                            'available in?'),
            'fields': (('countries', 'locales'))
        }),
        ('Search Providers', {
            'description': ('Would you like to <strong>exclude</strong> '
                            'any search providers from this snippet?'),
            'fields': (('exclude_from_search_providers',),)
        }),
        ('Client Match Rules', {
            'fields': ('client_match_rules',),
            'classes': ('collapse',)
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

    def get_form(self, request, obj=None, **kwargs):
        form = super(SnippetAdmin, self).get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form

    def get_changelist_form(self, request, **kwargs):
        form = forms.SnippetChangeListForm
        form.current_user = request.user
        return form

    def save_model(self, request, obj, form, change):
        statsd.incr('save.snippet')
        super(SnippetAdmin, self).save_model(request, obj, form, change)

    def lookup_allowed(self, key, value):
        if key == 'template__name':
            return True
        return super(SnippetAdmin, self).lookup_allowed(key, value)

    def preview_url(self, obj):
        url = obj.get_preview_url()
        template = mark_safe('<a href="{url}" target=_blank>{url}</a>'.format(url=url))
        return template

    def get_queryset(self, request):
        query = super(SnippetAdmin, self).get_queryset(request)
        return query.prefetch_related('locales')


class JSONSnippetAdmin(BaseSnippetAdmin):
    form = forms.JSONSnippetAdminForm
    search_fields = ('name', 'client_match_rules__description')
    list_filter = (
        ModifiedFilter,
        'published',
        ReleaseFilter,
        ('locales', RelatedDropdownFilter),
        ('client_match_rules', RelatedDropdownFilter),
    )

    fieldsets = (
        (None, {'fields': ('name', 'published', 'created', 'modified')}),
        ('Content', {
            'fields': ('icon', 'text', 'url'),
        }),
        ('Publish Duration', {
            'description': ('When will this snippet be available? (Optional)'
                            '<br>Publish times are in UTC. '
                            '<a href="http://time.is/UTC" target="_blank" '
                            'rel="noopener noreferrer">'
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


class SearchProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier')


class TargetedCountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority')
    list_filter = ('priority',)
    list_editable = ('priority',)
    search_fields = (
        'name',
        'code',
    )


class TargetedLocaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority')
    list_filter = ('priority',)
    list_editable = ('priority',)
    search_fields = (
        'name',
        'code',
    )
