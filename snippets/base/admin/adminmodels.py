import re

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import TextField, Q
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from reversion.admin import VersionAdmin
from django_ace import AceWidget
from django_statsd.clients import statsd
from jinja2.meta import find_undeclared_variables
from django_admin_listfilter_dropdown.filters import (RelatedDropdownFilter,
                                                      RelatedOnlyDropdownFilter)

from snippets.base import forms, models, slack
from snippets.base.admin import actions, filters


MATCH_LOCALE_REGEX = re.compile(r'(\w+(?:-\w+)*)')
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

    def save_related(self, request, form, formsets, change):
        """
        After saving the related objects, remove and add
        SnippetTemplateVariables depending on how the template code changed.
        """
        super(SnippetTemplateAdmin, self).save_related(request, form, formsets,
                                                       change)

        # Parse the template code and find any undefined variables.
        ast = models.JINJA_ENV.env.parse(form.instance.code)
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


class AddonAdmin(admin.ModelAdmin):
    list_display = ('name', 'guid')


class IconAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'image',
    ]
    readonly_fields = [
        'height',
        'width',
        'preview',
        'creator',
        'created',
        'snippets',
    ]
    list_display_links = [
        'id',
        'name',
    ]
    list_display = [
        'id',
        'name',
        'width',
        'height',
        'preview',
    ]

    class Media:
        css = {
            'all': (
                'css/admin/IconListSnippets.css',
            )
        }

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def preview(self, obj):
        text = f'<img style="max-width:120px; max-height:120px;" src="{obj.image.url}"/>'
        return mark_safe(text)

    def snippets(self, obj):
        """Snippets using this icon."""
        template = get_template('base/snippets_related_with_icon.jinja')
        return mark_safe(template.render({'snippets': obj.snippets}))


class SimpleTemplateInline(admin.StackedInline):
    model = models.SimpleTemplate
    form = forms.SimpleTemplateForm
    can_delete = False
    classes = [
        'inline-template',
        'simple_snippet',
    ]
    raw_id_fields = [
        'section_title_icon',
        'title_icon',
        'icon',
    ]

    fieldsets = (
        ('Title', {
            'fields': ('title_icon', 'title'),
        }),
        ('Section', {
            'fields': ('section_title_icon', 'section_title_text', 'section_title_url',),
        }),
        ('Main', {
            'fields': ('icon', 'text', 'button_label', 'button_color', 'button_url'),
        }),
        ('Extra', {
            'fields': ('block_button_text', 'tall', 'do_not_autoblock'),
        })

    )


class FundraisingTemplateInline(admin.StackedInline):
    model = models.FundraisingTemplate
    form = forms.FundraisingTemplateForm
    can_delete = False
    classes = [
        'inline-template',
        'eoy_snippet',
    ]
    raw_id_fields = [
        'title_icon',
        'icon',
    ]

    fieldsets = (
        ('Title', {
            'fields': (
                'title_icon',
                'title'
            ),
        }),
        ('Main', {
            'fields': (
                'icon',
                'text',
                'text_color',
                'background_color',
                'highlight_color',
            )
        }),
        ('Form Configuration', {
            'fields': (
                'donation_form_url',
                'currency_code',
                'locale',
                'selected_button',
                'button_label',
                'button_color',
                'button_background_color',
                'monthly_checkbox_label_text',
            )
        }),
        ('Donation', {
            'fields': (
                ('donation_amount_first', 'donation_amount_second',
                 'donation_amount_third', 'donation_amount_fourth',),
            )
        }),
        ('Extra', {
            'fields': ('block_button_text', 'test', 'do_not_autoblock'),
        })

    )


class FxASignupTemplateInline(admin.StackedInline):
    model = models.FxASignupTemplate
    form = forms.FxASignupTemplateForm
    can_delete = False
    classes = [
        'inline-template',
        'fxa_signup_snippet',
    ]
    raw_id_fields = [
        'scene1_title_icon',
        'scene1_icon',
    ]

    fieldsets = (
        ('Scene 1 Title', {
            'fields': (
                'scene1_title_icon',
                'scene1_title'
            ),
        }),
        ('Scene 1 Main', {
            'fields': (
                'scene1_icon',
                'scene1_text',
                'scene1_button_label',
                'scene1_button_color',
                'scene1_button_background_color',
            )
        }),
        ('Scene 2 Title', {
            'fields': ('scene2_title',),
        }),
        ('Scene 2 Main', {
            'fields': (
                'scene2_text',
                'scene2_button_label',
                'scene2_email_placeholder_text',
                'scene2_dismiss_button_text',
            )
        }),

        ('Extra', {
            'fields': (
                'utm_term',
                'utm_campaign',
                'block_button_text',
                'do_not_autoblock'
            ),
        })
    )


class NewsletterTemplateInline(admin.StackedInline):
    model = models.NewsletterTemplate
    form = forms.NewsletterTemplateForm
    can_delete = False
    classes = [
        'inline-template',
        'newsletter_snippet',
    ]
    raw_id_fields = [
        'scene1_title_icon',
        'scene1_icon',
    ]

    fieldsets = (
        ('Scene 1 Title', {
            'fields': (
                'scene1_title_icon',
                'scene1_title'
            ),
        }),
        ('Scene 1 Main', {
            'fields': (
                'scene1_icon',
                'scene1_text',
                'scene1_button_label',
                'scene1_button_color',
                'scene1_button_background_color',
            )
        }),
        ('Scene 2 Title', {
            'fields': ('scene2_title',),
        }),
        ('Scene 2 Main', {
            'fields': (
                'scene2_text',
                'scene2_button_label',
                'scene2_email_placeholder_text',
                'scene2_privacy_html',
                'scene2_newsletter',
                'scene2_dismiss_button_text',
                'locale',
                'success_text',
                'error_text',
            )
        }),

        ('Extra', {
            'fields': (
                'block_button_text',
                'do_not_autoblock'
            ),
        })
    )


class SendToDeviceTemplateInline(admin.StackedInline):
    model = models.SendToDeviceTemplate
    form = forms.SendToDeviceTemplateForm
    can_delete = False
    classes = [
        'inline-template',
        'send_to_device_snippet',
    ]
    raw_id_fields = [
        'scene1_title_icon',
        'scene1_icon',
        'scene2_icon',
    ]

    fieldsets = (
        ('Scene 1 Title', {
            'fields': (
                'scene1_title_icon',
                'scene1_title'
            ),
        }),
        ('Scene 1 Main', {
            'fields': (
                'scene1_icon',
                'scene1_text',
                'scene1_button_label',
                'scene1_button_color',
                'scene1_button_background_color',
            )
        }),
        ('Scene 2 Title', {
            'fields': ('scene2_title',),
        }),
        ('Scene 2 Main', {
            'fields': (
                'scene2_icon',
                'scene2_text',

                'scene2_button_label',
                'scene2_input_placeholder',
                'scene2_disclaimer_html',
                'scene2_dismiss_button_text',

                'locale',
                'country',
                ('include_sms', 'message_id_sms',),
                'message_id_email',
                'success_title',
                'success_text',
                'error_text',
            )
        }),

        ('Extra', {
            'fields': (
                'block_button_text',
                'do_not_autoblock'
            ),
        })
    )


class SimpleBelowSearchTemplateInline(admin.StackedInline):
    model = models.SimpleBelowSearchTemplate
    form = forms.SimpleBelowSearchTemplateForm
    can_delete = False
    classes = [
        'inline-template',
        'simple_below_search_snippet',
    ]
    raw_id_fields = [
        'icon',
    ]

    fieldsets = (
        ('Main', {
            'fields': ('icon', 'text'),
        }),
        ('Extra', {
            'fields': ('block_button_text', 'do_not_autoblock'),
        })

    )


class ASRSnippetAdmin(admin.ModelAdmin):
    form = forms.ASRSnippetAdminForm
    inlines = [
        SimpleTemplateInline,
        FundraisingTemplateInline,
        FxASignupTemplateInline,
        NewsletterTemplateInline,
        SendToDeviceTemplateInline,
        SimpleBelowSearchTemplateInline,
    ]
    list_display_links = (
        'id',
        'name',
    )
    list_display = (
        'id',
        'name',
        'status',
        'locale_list',
        'modified',
    )
    list_filter = (
        filters.ModifiedFilter,
        ('locales', RelatedOnlyDropdownFilter),
        'status',
        filters.ChannelFilter,
        ('campaign', RelatedDropdownFilter),
        ('category', RelatedDropdownFilter),
        filters.ScheduledFilter,
    )
    search_fields = (
        'name',
        'id',
        'campaign__name',
        'targets__name',
        'category__name',
    )
    autocomplete_fields = (
        'campaign',
        'category',
    )
    preserve_filters = True
    readonly_fields = (
        'id',
        'created',
        'modified',
        'uuid',
        'creator',
        'preview_url_light_theme',
        'preview_url_dark_theme',

    )
    filter_horizontal = (
        'targets',
        'locales',
    )
    save_on_top = True
    save_as = True
    view_on_site = False
    actions = (
        actions.duplicate_snippets_action,
        'make_published',
    )

    fieldsets = (
        ('ID', {
            'fields': (
                'id',
                'name',
                'status',
                'creator',
                'preview_url_light_theme',
                'preview_url_dark_theme',
            )
        }),
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
                Example: This is a <code>&lt;a href=&quot;https://example.com?utm_term=[[snippet_id]]&quot;&gt;link&lt;/a&gt;</code>
                <br/>
                '''  # noqa
            ),
            'fields': ('template_chooser',),
            'classes': ('template-fieldset',)
        }),
        ('Publishing Options', {
            'fields': (
                'campaign',
                'category',
                'targets',
                ('publish_start', 'publish_end'),
                'locales',
                'weight',)
        }),
        ('Other Info', {
            'fields': ('uuid', ('created', 'modified'), 'for_qa'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        css = {
            'all': (
                'css/admin/ASRSnippetAdmin.css',
                'css/admin/IDFieldHighlight.css',
                'css/admin/InlineTemplates.css',
            )
        }
        js = (
            'js/admin/clipboard.min.js',
            'js/admin/copy_preview.js',
        )

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.asrsnippet')
        super().save_model(request, obj, form, change)

    def preview_url_light_theme(self, obj):
        text = f'''
        <span id="previewLinkUrlLight">{obj.get_preview_url()}</span>
        <button id="copyPreviewLink" class="btn"
                data-clipboard-target="#previewLinkUrlLight"
                originalText="Copy to Clipboard" type="button">
          Copy to Clipboard
        </button>
        '''
        return mark_safe(text)
    preview_url_light_theme.short_description = 'Light Themed Preview URL'

    def preview_url_dark_theme(self, obj):
        text = f'''
        <span id="previewLinkUrlDark">{obj.get_preview_url(dark=True)}</span>
        <button id="copyPreviewLink" class="btn"
                data-clipboard-target="#previewLinkUrlDark"
                originalText="Copy to Clipboard" type="button">
          Copy to Clipboard
        </button>
        '''
        return mark_safe(text)
    preview_url_dark_theme.short_description = 'Dark Themed Preview URL'

    def change_view(self, request, *args, **kwargs):
        if request.method == 'POST' and '_saveasnew' in request.POST:
            # Always saved cloned snippets as un-published and un-check ready for review.
            post_data = request.POST.copy()
            post_data['status'] = models.STATUS_CHOICES['Draft']
            request.POST = post_data
        return super().change_view(request, *args, **kwargs)

    def get_readonly_fields(self, request, obj):
        if not request.user.is_superuser:
            return self.readonly_fields + ('for_qa',)
        return self.readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(for_qa=False)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form

    def make_published(self, request, queryset):
        clean_queryset = queryset.exclude(status=models.STATUS_CHOICES['Published'])
        no_snippets = clean_queryset.count()
        no_already_published_snippets = queryset.count() - no_snippets

        snippets = []
        with transaction.atomic():
            for snippet in clean_queryset:
                snippet.status = models.STATUS_CHOICES['Published']
                snippet.save()
                snippets.append(snippet)

        for snippet in snippets:
            slack.send_slack('asr_published', snippet)

        if no_already_published_snippets:
            messages.warning(
                request, f'Skipped {no_already_published_snippets} already published snippets.')
        messages.success(request, f'Published {no_snippets} snippets.')

    make_published.short_description = 'Publish selected snippets'

    # Only users with Publishing permissions on all channels are allowed to
    # mark snippets for publication in bulk.
    make_published.allowed_permissions = (
        'global_publish',
    )

    def has_global_publish_permission(self, request):
        return request.user.has_perms([
            'base.%s' % perm for perm in [
                'publish_on_release',
                'publish_on_beta',
                'publish_on_aurora',
                'publish_on_nightly',
                'publish_on_esr',
            ]
        ])

    def locale_list(self, obj):
        num_locales = obj.locales.count()
        locales = obj.locales.all()[:3]
        active_locales = ', '.join([str(locale) for locale in locales])
        if num_locales > 3:
            active_locales += ' and {0} more.'.format(num_locales - 3)
        return active_locales


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
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.campaign')
        super().save_model(request, obj, form, change)


class CategoryAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'creator',
                       'published_snippets_in_category', 'total_snippets_in_category')

    fieldsets = (
        ('ID', {
            'fields': (
                'name',
                'description',
                'published_snippets_in_category',
                'total_snippets_in_category',
            )
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified')),
        }),
    )
    search_fields = (
        'name',
        'description',
    )

    list_display = (
        'name',
        'published_snippets_in_category',
        'total_snippets_in_category',
    )

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.category')
        super().save_model(request, obj, form, change)

    def published_snippets_in_category(self, obj):
        return obj.asrsnippets.filter(status=models.STATUS_CHOICES['Published']).count()

    def total_snippets_in_category(self, obj):
        return obj.asrsnippets.count()


class TargetAdmin(admin.ModelAdmin):
    form = forms.TargetAdminForm
    save_on_top = True
    readonly_fields = ('created', 'modified', 'creator', 'jexl_expr')
    filter_horizontal = (
        'client_match_rules',
    )
    search_fields = (
        'name',
    )
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
                'filtr_country',
                'filtr_is_developer',
                'filtr_current_search_engine',
                'filtr_browser_addon',
                'filtr_total_bookmarks_count',
            )
        }),
        ('Advanced Targeting', {
            'fields': (
                'client_match_rules',
            )
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified'), 'jexl_expr'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.target')
        super().save_model(request, obj, form, change)
