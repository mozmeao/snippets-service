import re

from django.contrib import admin
from django.db.models import TextField, Q
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from reversion.admin import VersionAdmin
from django_ace import AceWidget
from django_statsd.clients import statsd
from jinja2.meta import find_undeclared_variables
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from snippets.base import forms, models
from snippets.base.models import JINJA_ENV
from snippets.base.admin.filters import ModifiedFilter, ReleaseFilter


MATCH_LOCALE_REGEX = re.compile('(\w+(?:-\w+)*)')
RESERVED_VARIABLES = ('_', 'snippet_id')


class ClientMatchRuleAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ('description', 'is_exclusion', 'startpage_version', 'name',
                    'version', 'locale', 'appbuildid', 'build_target',
                    'channel', 'os_version', 'distribution',
                    'distribution_version', 'modified')
    list_filter = ('name', 'version', 'os_version', 'appbuildid',
                   'build_target', 'channel', 'distribution', 'locale')
    save_on_top = True
    search_fields = ('description',)


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'object_repr', 'change_message')
    list_filter = ('user', 'content_type')


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
    list_filter = ('hidden', 'startpage')
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
        new_vars = [x for x in new_vars if x not in RESERVED_VARIABLES]

        # Delete variables not in the new set.
        var_manager.filter(~Q(name__in=new_vars)).delete()

        # Create variables that don't exist.
        for i, variable in enumerate(new_vars, start=1):
            obj, _ = models.SnippetTemplateVariable.objects.get_or_create(
                template=form.instance, name=variable)
            if obj.order == 0:
                obj.order = i * 10
                obj.save()


class UploadedFileAdmin(admin.ModelAdmin):
    readonly_fields = ('url', 'preview', 'snippets')
    list_display = ('name', 'url', 'preview', 'modified')
    prepopulated_fields = {'name': ('file',)}
    form = forms.UploadedFileAdminForm

    def preview(self, obj):
        template = get_template('base/uploadedfile_preview.jinja')
        return mark_safe(template.render({'file': obj}))

    def snippets(self, obj):
        """Snippets using this file."""
        template = get_template('base/uploadedfile_snippets.jinja')
        return mark_safe(template.render({'snippets': obj.snippets}))


class AddonAdmin(admin.ModelAdmin):
    list_display = ('name', 'guid')


class ASRSnippetAdmin(admin.ModelAdmin):
    form = forms.ASRSnippetAdminForm

    list_display_links = (
        'id',
        'name',
    )
    list_display = (
        'id',
        'name',
        'status',
        'modified',
    )
    list_filter = (
        ModifiedFilter,
        'status',
        ReleaseFilter,
        ('template', RelatedDropdownFilter),
    )
    search_fields = (
        'name',
    )
    autocomplete_fields = (
        'campaign',
    )
    preserve_filters = True
    readonly_fields = (
        'created',
        'modified',
        'uuid',
        'creator',
        'preview_url',
    )
    filter_horizontal = ('locales',)
    save_on_top = True
    save_as = True
    view_on_site = False

    fieldsets = (
        ('ID', {'fields': ('creator', 'name', 'status', 'preview_url')}),
        ('Content', {
            'description': (
                '''
                <strong>Available deep links:</strong><br/>
                <ol>
                  <li><code>special:accounts</code> to open Firefox Accounts</li>
                  <li><code>special:appMenu</code> to open the hamburger menu</li>
                </ol><br/>
                <strong>Automatically add Snippet ID:</strong><br/>
                You can use <code>[[snippet_id]]</code> in any field and it
                will be automatically replaced by Snippet ID when served to users.
                <br/>
                Example: This is a <code>&lt;a href=&quot;https://example.com?utm_term=[[snippet_id]]&quot;&gt;link&lt;/a&gt;</code>  # noqa
                <br/>
                '''
            ),
            'fields': ('template', 'data'),
        }),
        ('Publishing Options', {
            'fields': ('campaign', 'target', ('publish_start', 'publish_end'), 'locales', 'weight',)
        }),
        ('Other Info', {
            'fields': ('uuid', ('created', 'modified')),
            'classes': ('collapse',)
        }),
    )

    class Media:
        css = {
            'all': ('css/admin/ASRSnippetAdmin.css',)
        }

    def save_model(self, request, obj, form, change):
        obj.creator = request.user
        statsd.incr('save.asrsnippet')
        super().save_model(request, obj, form, change)

    def preview_url(self, obj):
        return obj.get_preview_url()


class CampaignAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'creator',)
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('ID', {'fields': ('name', 'slug')}),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified')),
        }),
    )
    search_fields = (
        'name',
    )

    def save_model(self, request, obj, form, change):
        obj.creator = request.user
        statsd.incr('save.campaign')
        super().save_model(request, obj, form, change)


class TargetAdmin(admin.ModelAdmin):
    form = forms.TargetAdminForm
    readonly_fields = ('created', 'modified', 'creator', 'jexl_expr')

    fieldsets = (
        ('ID', {'fields': ('name',)}),
        ('Product channels', {
            'description': 'What channels will this snippet be available in?',
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly', 'on_esr'),)
        }),
        ('Targeting', {
            'fields': (
                'filtr_is_default_browser',
                'filtr_updates_enabled',
                'filtr_updates_autodownload_enabled',
                'filtr_profile_age_created',
                'filtr_firefox_version',
                'filtr_previous_session_end',
                'filtr_uses_firefox_sync',
                'filtr_is_developer',
                'filtr_current_search_engine',
                'filtr_browser_addon',
                'filtr_total_bookmarks_count',
            )
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified'), 'jexl_expr'),
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.creator = request.user
        statsd.incr('save.target')
        super().save_model(request, obj, form, change)
