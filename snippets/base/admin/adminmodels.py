import copy
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Sum, TextField, Q
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from django_ace import AceWidget
from django_admin_listfilter_dropdown.filters import (RelatedDropdownFilter,
                                                      RelatedOnlyDropdownFilter)
from django_statsd.clients import statsd
from jinja2.meta import find_undeclared_variables
from reversion.admin import VersionAdmin
from taggit_helpers.admin import TaggitListFilter

from snippets.base import forms, models
from snippets.base.admin import actions, filters


MATCH_LOCALE_REGEX = re.compile(r'(\w+(?:-\w+)*)')
RESERVED_VARIABLES = ('_', 'snippet_id')


class RelatedJobsMixin():
    def related_published_jobs(self, obj):
        return obj.jobs.filter(status=models.Job.PUBLISHED).count()

    def related_total_jobs(self, obj):
        return obj.jobs.count()

    def jobs_list(self, obj):
        """List Related Jobs."""
        template = get_template('base/jobs_related_with_obj.jinja')
        return mark_safe(
            template.render({
                'jobs': obj.jobs.all().order_by('-id')
            })
        )


class RelatedSnippetsMixin():
    def related_published_jobs(self, obj):
        return models.Job.objects.filter(
            status=models.Job.PUBLISHED, snippet__in=obj.snippets.all()).count()

    def related_total_snippets(self, obj):
        return obj.snippets.count()

    def snippet_list(self, obj):
        """List Related Snippets."""
        template = get_template('base/snippets_related_with_obj.jinja')
        return mark_safe(
            template.render({
                'snippets': obj.snippets.all().order_by('-id')
            })
        )


class ClientMatchRuleAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ('description', 'is_exclusion', 'startpage_version', 'name',
                    'version', 'locale', 'appbuildid', 'build_target',
                    'channel', 'os_version', 'distribution',
                    'distribution_version', 'modified')
    list_filter = ('name', 'version', 'os_version', 'appbuildid',
                   'build_target', 'channel', 'distribution', 'locale')
    save_on_top = True
    search_fields = ('description',)

    class Media:
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )


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

    class Media:
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )


class IconAdmin(RelatedSnippetsMixin, admin.ModelAdmin):
    search_fields = [
        'name',
        'image',
        'id',
    ]
    readonly_fields = [
        'height',
        'width',
        'size',
        'preview',
        'creator',
        'created',
        'snippet_list',
        'related_total_snippets',
        'related_published_jobs',
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
        'related_total_snippets',
        'related_published_jobs',
        'preview',
    ]
    list_filter = [
        filters.IconRelatedPublishedASRSnippetFilter,
    ]

    class Media:
        css = {
            'all': (
                'css/admin/ListSnippetsJobs.css',
            )
        }
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )

    def size(self, obj):
        return '{:.0f} KiB'.format(obj.image.size / 1024)

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def preview(self, obj):
        template = get_template('base/preview_image.jinja')
        return mark_safe(template.render({'image': obj.image}))


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
            'fields': ('icon', 'text', 'button_label',
                       'button_url', 'button_color', 'button_background_color'),
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
        'scene1_section_title_icon',
        'scene1_title_icon',
        'scene1_icon',
    ]

    fieldsets = (
        ('Scene 1 Section', {
            'fields': (
                'scene1_section_title_icon',
                'scene1_section_title_text',
                'scene1_section_title_url',
            )
        }),
        ('Scene 1 Title', {
            'fields': (
                'scene1_title_icon',
                'scene1_title',
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
                'do_not_autoblock',
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
        'scene1_section_title_icon',
        'scene1_title_icon',
        'scene1_icon',
    ]

    fieldsets = (
        ('Scene 1 Section', {
            'fields': (
                'scene1_section_title_icon',
                'scene1_section_title_text',
                'scene1_section_title_url',
            )
        }),
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
                'retry_button_label',
            )
        }),

        ('Extra', {
            'fields': (
                'block_button_text',
                'do_not_autoblock',
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
        'scene1_section_title_icon',
        'scene1_title_icon',
        'scene1_icon',
        'scene2_icon',
    ]

    fieldsets = (
        ('Scene 1 Section', {
            'fields': (
                'scene1_section_title_icon',
                'scene1_section_title_text',
                'scene1_section_title_url',
            )
        }),
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
                ('include_sms', 'message_id_sms',),
                'country',
                'message_id_email',
                'success_title',
                'success_text',
                'error_text',
                'retry_button_label',
            )
        }),

        ('Extra', {
            'fields': (
                'block_button_text',
                'do_not_autoblock',
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
            'fields': ('icon', 'title', 'text', 'button_label',
                       'button_url', 'button_color', 'button_background_color'),
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
    list_display_links = [
        'id',
    ]
    list_display = [
        'id',
        'custom_name_with_tags',
        'snippet_status',
        'locale',
        'modified',
    ]
    list_filter = [
        filters.TemplateFilter,
        ['locale', RelatedDropdownFilter],
        ['jobs__targets', RelatedOnlyDropdownFilter],
        'jobs__status',
        ['jobs__campaign', RelatedDropdownFilter],
        TaggitListFilter,
        ['category', RelatedDropdownFilter],
        ['product', RelatedDropdownFilter],
        filters.ModifiedFilter,
    ]
    search_fields = [
        'name',
        'id',
        'jobs__campaign__name',
        'jobs__targets__name',
        'category__name',
        'product__name',
    ]
    autocomplete_fields = [
        'category',
        'product',
    ]
    preserve_filters = True
    readonly_fields = [
        'id',
        'created',
        'modified',
        'uuid',
        'creator',
        'preview_url_light_theme',
        'preview_url_dark_theme',
        'job_status',
        'snippet_status',
    ]
    actions = [
        actions.duplicate_snippets_action,
    ]
    save_on_top = True
    save_as = True
    view_on_site = False

    fieldsets = (
        ('ID', {
            'fields': (
                'id',
                'name',
                'tags',
                'creator',
                'category',
                'product',
                'preview_url_light_theme',
                'preview_url_dark_theme',
            )
        }),
        ('Status', {
            'fields': (
                'snippet_status',
                'job_status',
            )
        }),
        ('Content', {
            'description': (
                '''
                <strong>Available deep links:</strong><br/>
                <ol>
                  <li><code>special:accounts</code> opens Firefox Accounts</li>
                  <li><code>special:monitor</code> links User to Firefox Monitor and directly authenticates them. Works only in buttons. Works only after Firefox 69.</li>
                  <li><code>special:about:ABOUT_PAGE</code> links to an About page. Get a list of About pages by typing <code>about:about</code> in your awesome bar. Example: <code>special:about:protections</code>.
                  <li><code>special:preferences</code> opens the Firefox Preferences tab. Example: <code>special:preferences</code>.
                  <li><code>special:highlight:HIGHLIGHT</code> highlights a button in the browser chrome. Get a list of <a href="https://firefox-source-docs.mozilla.org/browser/components/uitour/docs/UITour-lib.html#Mozilla.UITour.Target">available highlights</a>. Example: <code>special:highlight:logins</code>. Works only after Firefox 71.
                  <li><code>special:menu:MENU</code> opens a targeted menu in the browser chrome. Get a list of <a href="https://firefox-source-docs.mozilla.org/browser/components/uitour/docs/UITour-lib.html#Mozilla.UITour.MenuName">available menus</a>. Example: <code>special:menu:appMenu</code>.
                </ol><br/>
                <strong>Content Variables:</strong><br/>
                You can use <code>[[snippet_id]]</code> in any field and it
                will be automatically replaced by Snippet ID when served to users.
                Similarly <code>[[campaign_slug]]</code> gets replaced by Campaign Slug,
                <code>[[channels]]</code> by targeted channels, <code>[[job_id]]</code>
                by Job ID.
                <br/>
                Example: This is a <code>&lt;a href=&quot;https://example.com?utm_term=[[snippet_id]]&quot;&gt;link&lt;/a&gt;</code>
                <br/>
                '''  # noqa
            ),
            'fields': (
                'status',
                'locale',
                'template_chooser',
            ),
            'classes': ('template-fieldset',)
        }),
        ('Other Info', {
            'fields': ('uuid', ('created', 'modified')),
            'classes': ('collapse',)
        }),
    )

    class Media:
        css = {
            'all': (
                'css/admin/ASRSnippetAdmin.css',
                'css/admin/descriptionColorize.css',
                'css/admin/IDFieldHighlight.css',
                'css/admin/InlineTemplates.css',
                'css/admin/CustomNameWithTags.css',
            )
        }
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
            'js/clipboard.min.js',
            'js/copy_preview.js',
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

    def snippet_status(self, obj):
        if obj.jobs.filter(status=models.Job.PUBLISHED).exists():
            msg = 'Published'
        elif obj.jobs.filter(status=models.Job.SCHEDULED).exists():
            msg = 'Scheduled'
        else:
            msg = 'Not Scheduled'
        return mark_safe(
            '<span id="snippet_status" class={color_class}>{msg}</span>'.format(
                color_class=msg.lower(), msg=msg
            )
        )
    snippet_status.short_description = 'Status'

    def job_status(self, obj):
        changelist_url = '{reverse}?snippet__id__exact={id}'.format(
            reverse=reverse('admin:base_job_changelist'),
            id=obj.id,
        )
        draft_jobs_count = scheduled_jobs_count = published_jobs_count = 0
        # Count job types in Python to avoid multiple DB queries.
        for job in obj.jobs.all():
            if job.status == models.Job.DRAFT:
                draft_jobs_count += 1
            elif job.status == models.Job.SCHEDULED:
                scheduled_jobs_count += 1
            elif job.status == models.Job.PUBLISHED:
                published_jobs_count += 1

        msg = '''
        <a href="{draft_jobs_link}">{draft_jobs_count} Draft Jobs</a>
        -
        <a href="{scheduled_jobs_link}">{scheduled_jobs_count} Scheduled Jobs</a>
        -
        <a href="{published_jobs_link}">{published_jobs_count} Published Jobs</a>
        -
        <a href="{all_jobs_link}">All Jobs</a>
        <a href="{add_job_link}" id="addJobButton">Add Job</a>

        '''.format(
            draft_jobs_link=changelist_url + '&status__exact={}'.format(models.Job.DRAFT),
            draft_jobs_count=draft_jobs_count,
            scheduled_jobs_link=changelist_url + '&status__exact={}'.format(models.Job.SCHEDULED),
            scheduled_jobs_count=scheduled_jobs_count,
            published_jobs_link=changelist_url + '&status__exact={}'.format(models.Job.PUBLISHED),
            published_jobs_count=published_jobs_count,
            all_jobs_link=changelist_url,
            add_job_link=reverse('admin:base_job_add') + '?snippet={}'.format(obj.id),
        )
        return mark_safe(msg)
    job_status.short_description = 'Jobs'

    def change_view(self, request, *args, **kwargs):
        if request.method == 'POST' and '_saveasnew' in request.POST:
            # Always saved cloned snippets as un-published and un-check ready for review.
            post_data = request.POST.copy()
            post_data['status'] = models.STATUS_CHOICES['Draft']
            request.POST = post_data
        return super().change_view(request, *args, **kwargs)

    def get_readonly_fields(self, request, obj):
        fields = copy.copy(self.readonly_fields)
        if obj is None:
            fields.append('status')
        return fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request).prefetch_related('tags')
        return queryset

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form

    def custom_name_with_tags(self, obj):
        template = get_template('base/snippets_custom_name_with_tags.jinja')
        return mark_safe(template.render({'obj': obj}))
    custom_name_with_tags.short_description = 'Name'


class CampaignAdmin(RelatedJobsMixin, admin.ModelAdmin):
    readonly_fields = [
        'created',
        'modified',
        'creator',
        'related_published_jobs',
        'related_total_jobs',
        'jobs_list',
    ]
    prepopulated_fields = {
        'slug': ('name',)
    }
    fieldsets = (
        ('ID', {'fields': ('name', 'slug')}),
        ('Jobs', {
            'fields': (
                'related_published_jobs',
                'related_total_jobs',
                'jobs_list',
            ),
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified')),
        }),
    )
    search_fields = [
        'name',
    ]
    list_display = [
        'name',
        'related_total_jobs',
        'related_published_jobs',
    ]
    list_filter = [
        filters.RelatedPublishedASRSnippetFilter,
        filters.ChannelFilter,
    ]

    class Media:
        css = {
            'all': (
                'css/admin/ListSnippetsJobs.css',
            )
        }
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.campaign')
        super().save_model(request, obj, form, change)


class CategoryAdmin(RelatedSnippetsMixin, admin.ModelAdmin):
    readonly_fields = [
        'created',
        'modified',
        'creator',
        'snippet_list',
        'related_total_snippets',
        'related_published_jobs',
    ]
    fieldsets = [
        ('ID', {
            'fields': (
                'name',
                'description',
            )
        }),
        ('Snippets', {
            'fields': (
                'related_published_jobs',
                'related_total_snippets',
                'snippet_list',
            ),
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified')),
        }),
    ]
    search_fields = [
        'name',
        'description',
    ]
    list_display = [
        'name',
        'related_published_jobs',
        'related_total_snippets',
    ]
    list_filter = [
        filters.RelatedPublishedASRSnippetFilter,
    ]

    class Media:
        css = {
            'all': (
                'css/admin/ListSnippetsJobs.css',
            )
        }
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.category')
        super().save_model(request, obj, form, change)


class ProductAdmin(RelatedSnippetsMixin, admin.ModelAdmin):
    readonly_fields = [
        'created',
        'modified',
        'creator',
        'snippet_list',
        'related_total_snippets',
        'related_published_jobs',
    ]
    fieldsets = [
        ('ID', {
            'fields': (
                'name',
                'description',
            )
        }),
        ('Snippets', {
            'fields': (
                'related_published_jobs',
                'related_total_snippets',
                'snippet_list',
            ),
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified')),
        }),
    ]
    search_fields = [
        'name',
        'description',
    ]
    list_display = [
        'name',
        'related_published_jobs',
        'related_total_snippets',
    ]
    list_filter = [
        filters.RelatedPublishedASRSnippetFilter,
    ]

    class Media:
        css = {
            'all': (
                'css/admin/ListSnippetsJobs.css',
            )
        }
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.product')
        super().save_model(request, obj, form, change)


class TargetAdmin(RelatedJobsMixin, admin.ModelAdmin):
    change_list_template = 'admin/base/target/change_list.html'
    form_custom = forms.TargetAdminCustomForm
    form_full = forms.TargetAdminForm
    save_on_top = True
    readonly_fields = [
        'created',
        'modified',
        'creator',
        'jobs_list',
        'related_total_jobs',
        'related_published_jobs',
    ]
    search_fields = [
        'name',
    ]
    list_display = [
        'name',
        'related_published_jobs',
        'related_total_jobs',
    ]
    list_filter = [
        filters.RelatedPublishedASRSnippetFilter,
    ]
    fieldsets_custom = [
        ('ID', {'fields': ('name',)}),
        ('Product channels', {
            'description': 'What channels will this snippet be available in?',
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly', 'on_esr'),)
        }),
        ('Targeting', {'fields': ('jexl_expr',)}),
    ]
    fieldsets_full = [
        ('ID', {'fields': ('name',)}),
        ('Product channels', {
            'description': 'What channels will this snippet be available in?',
            'fields': (('on_release', 'on_beta', 'on_aurora', 'on_nightly', 'on_esr'),)
        }),
        ('Targeting', {
            'fields': (
                'filtr_is_default_browser',
                'filtr_needs_update',
                'filtr_updates_enabled',
                'filtr_updates_autodownload_enabled',
                'filtr_profile_age_created',
                'filtr_firefox_version',
                'filtr_previous_session_end',
                'filtr_country',
                'filtr_is_developer',
                'filtr_current_search_engine',
                'filtr_total_bookmarks_count',
                'filtr_operating_system',
            )
        }),
        ('Addons', {
            'fields': (
                'filtr_can_install_addons',
                'filtr_total_addons',
                'filtr_browser_addon',
            )
        }),
        ('Accounts and Sync', {
            'fields': (
                'filtr_uses_firefox_sync',
                'filtr_desktop_devices_count',
                'filtr_mobile_devices_count',
                'filtr_total_devices_count',
                'filtr_firefox_service',
            ),
        }),
        ('Jobs', {
            'fields': (
                'related_published_jobs',
                'related_total_jobs',
                'jobs_list',
            )
        }),
        ('Other Info', {
            'fields': ('creator', ('created', 'modified'), 'jexl_expr'),
        }),
    ]

    class Media:
        css = {
            'all': (
                'css/admin/ListSnippetsJobs.css',
            )
        }
        js = (
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        )

    def _wants_custom_form(self, request, obj):
        return request.GET.get('custom') == 'true' or (obj and obj.is_custom)

    def get_form(self, request, obj=None, **kwargs):
        if self._wants_custom_form(request, obj):
            return self.form_custom
        return self.form_full

    def get_readonly_fields(self, request, obj=None, **kwargs):
        if self._wants_custom_form(request, obj):
            return self.readonly_fields
        return self.readonly_fields + ['jexl_expr']

    def get_fieldsets(self, request, obj=None, **kwargs):
        if self._wants_custom_form(request, obj):
            return self.fieldsets_custom
        return self.fieldsets_full

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        statsd.incr('save.target')
        super().save_model(request, obj, form, change)


class LocaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = (
        'name',
        'code',
    )


class JobAdmin(admin.ModelAdmin):
    form = forms.JobAdminForm
    save_on_top = True
    preserve_filters = True
    filter_horizontal = [
        'targets',
    ]
    list_display = [
        'id',
        'snippet_name',
        'target_list',
        'job_status',
        'publish_start',
        'publish_end',
        'adj_impressions_humanized',
        'clicks_humanized',
        'clicks_ctr',
        'blocks_humanized',
        'blocks_ctr',
    ]
    list_display_links = [
        'id',
        'snippet_name',
    ]
    list_filter = [
        'status',
        ('campaign', RelatedDropdownFilter),
        ('targets', RelatedOnlyDropdownFilter),
        ('snippet__locale', RelatedOnlyDropdownFilter),
        filters.ChannelFilter,
    ]
    search_fields = [
        'id',
        'uuid',
        'snippet__id',
        'snippet__name',
        'campaign__name',
    ]
    autocomplete_fields = [
        'snippet',
        'campaign',
    ]
    readonly_fields = [
        'snippet_name_linked',
        'creator',
        'job_status',
        'uuid',
        'id',
        'created',
        'modified',
        'impressions_humanized',
        'adj_impressions_humanized',
        'adj_impressions_total_clients_humanized',
        'adj_impressions_per_client_humanized',
        'impressions_total_clients_humanized',
        'impressions_per_client_humanized',
        'clicks_humanized',
        'blocks_humanized',
        'clicks_ctr',
        'blocks_ctr',
        'redash_link',
        'completed_on',
    ]
    fieldsets = [
        ('ID', {
            'fields': ('id', ('job_status', 'completed_on'), 'snippet_name_linked', 'creator')
        }),
        ('Content', {
            'fields': ('snippet', 'campaign')
        }),
        ('Targeting', {
            'fields': ('targets', 'weight',)
        }),
        ('Publishing Dates', {
            'fields': (('publish_start', 'publish_end'),)
        }),
        ('Global Limits', {
            'fields': ((
                'limit_impressions',
                'limit_clicks',
                'limit_blocks',
            ),),
        }),
        ('Client Limits', {
            'fields': (
                'client_limit_lifetime',
                ('client_limit_per_hour',
                 'client_limit_per_day',
                 'client_limit_per_week',
                 'client_limit_per_fortnight',
                 'client_limit_per_month',),
            ),
            'description': (
                '''
                Limit the number of impressions of this Job per Firefox Client.<br/><br/>
                Examples:<br/>
                <ol>
                  <li>If <code>Max Weekly Impressions</code> is set to 2, each user will see this Job <i>at most</i> 2 times within 7 days.</li>
                  <li>Limits can be combined: If <code>Max Weekly Impressions</code> is set to 2 and <code>Max Monthly Impressions</code> is set to 4,
                      each user will see this Job <i>at most</i> 2 times within 7 days and <i>at most</i> 4 times within 30 days.</li>
                </ol>
                <strong>Note</strong>: Counting starts from the time a user gets their first impression. For example when a user first time sees a Job on the 10th day of a month, the fortnight counter will expire on the 25th.<br/>
                <strong>Note</strong>: This functionality <i>does not</i> guaranty the minimum number of impressions per user but it enforces that a Job won't appear more than planned.
                '''),  # noqa
        }),
        ('Metrics', {
            'fields': (
                ('impressions_humanized', 'adj_impressions_humanized'),
                ('impressions_total_clients_humanized', 'adj_impressions_total_clients_humanized'),
                ('impressions_per_client_humanized', 'adj_impressions_per_client_humanized'),
                ('clicks_humanized', 'clicks_ctr'),
                ('blocks_humanized', 'blocks_ctr'),
                'redash_link',
            ),
        }),
        ('Other Info', {
            'fields': (('created', 'modified'),),
        }),
        ('Advanced', {
            'fields': ('distribution',),
        }),
    ]
    actions = [
        'action_schedule_job',
        'action_cancel_job',
        'action_delete_job',
    ]

    class Media:
        css = {
            'all': [
                'css/admin/JobAdmin.css',
                'css/admin/descriptionColorize.css',
                'css/admin/IDFieldHighlight.css',
            ]
        }
        js = [
            'js/admin/jquery.are-you-sure.js',
            'js/admin/alert-page-leaving.js',
        ]

    def snippet_name(self, obj):
        return obj.snippet.name

    def snippet_name_linked(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse('admin:base_asrsnippet_change', args=[obj.snippet.id]), obj.snippet.name)
        )
    snippet_name_linked.short_description = 'Link to Snippet'

    def get_readonly_fields(self, request, obj=None):
        fields = copy.copy(self.readonly_fields)
        if not obj:
            return fields

        # If Completed or Cancelled make all fields read-only.
        if obj.status in [models.Job.CANCELED, models.Job.COMPLETED]:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))

        # If Published only changing of Publish End, Client Impression
        # Limits and Global Impression, Click, Block Limits.
        if obj.status in [models.Job.PUBLISHED]:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
            for field in [
                    'publish_end', 'client_limit_lifetime',
                    'client_limit_per_hour', 'client_limit_per_day',
                    'client_limit_per_week', 'client_limit_per_fortnight',
                    'client_limit_per_month', 'limit_impressions', 'limit_clicks',
                    'limit_blocks']:
                fields.remove(field)
        return fields

    def target_list(self, obj):
        return mark_safe(
            '<ul>' +
            ''.join([
                f'<li> {target}' for target in obj.targets.values_list('name', flat=True)
            ]) +
            '</ul>'
        )
    target_list.short_description = 'Targets'

    def job_status(self, obj):
        msg = obj.get_status_display()
        return mark_safe(
            '<span id="job_status" class={color_class}>{msg}</span>'.format(
                color_class=msg.lower(), msg=msg
            )
        )
    job_status.short_description = 'Status'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            impressions=Sum('metrics__impression'),
            adj_impressions=Sum('metrics__adj_impression'),
            clicks=Sum('metrics__click'),
            blocks=Sum('metrics__block'),
            impressions_total_clients=Sum('metrics__impression_no_clients_total'),
            adj_impressions_total_clients=Sum('metrics__adj_impression_no_clients_total'),
        )
        return queryset

    def impressions_humanized(self, obj):
        return intcomma(obj.impressions or 0)
    impressions_humanized.short_description = 'Impressions'

    def adj_impressions_humanized(self, obj):
        return intcomma(obj.adj_impressions or 0)
    adj_impressions_humanized.short_description = 'Adjusted Impressions'

    def impressions_total_clients_humanized(self, obj):
        return intcomma(obj.impressions_total_clients or 0)
    impressions_total_clients_humanized.short_description = 'Total Unique Clients'

    def adj_impressions_total_clients_humanized(self, obj):
        return intcomma(obj.adj_impressions_total_clients or 0)
    adj_impressions_total_clients_humanized.short_description = 'Adjusted Total Unique Clients'

    def impressions_per_client_humanized(self, obj):
        if not obj.impressions_total_clients:
            return 'N/A'
        return f'{obj.impressions / obj.impressions_total_clients:.2f}'
    impressions_per_client_humanized.short_description = 'Impressions Per Client'

    def adj_impressions_per_client_humanized(self, obj):
        if not obj.adj_impressions_total_clients:
            return 'N/A'
        return f'{obj.adj_impressions / obj.adj_impressions_total_clients:.2f}'
    adj_impressions_per_client_humanized.short_description = 'Adj Impressions Per Client'

    def clicks_humanized(self, obj):
        return intcomma(obj.clicks or 0)
    clicks_humanized.short_description = 'Clicks'

    def blocks_humanized(self, obj):
        return intcomma(obj.blocks or 0)
    blocks_humanized.short_description = 'Blocks'

    def clicks_ctr(self, obj):
        if not (obj.clicks or obj.adj_impressions):
            return 'N/A'
        ratio = (obj.clicks / obj.adj_impressions) * 100
        return format_html(f'<span class="">{ratio:.4f}%</span>')
    clicks_ctr.short_description = 'Adjusted CTR'

    def blocks_ctr(self, obj):
        if not (obj.blocks or obj.adj_impressions):
            return 'N/A'
        ratio = (obj.blocks / obj.adj_impressions) * 100
        return format_html(f'<span class="">{ratio:.4f}%</span>')
    blocks_ctr.short_description = 'Adjusted BR'

    def redash_link(self, obj):
        publish_end = (
            obj.publish_end or datetime.utcnow() + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        link_bigquery = (
            f'{settings.REDASH_ENDPOINT}/queries/{settings.REDASH_JOB_QUERY_BIGQUERY_ID}/'
            f'?p_start_date_{settings.REDASH_JOB_QUERY_BIGQUERY_ID}='
            f'{obj.publish_start.strftime("%Y-%m-%d")}'
            f'&p_end_date_{settings.REDASH_JOB_QUERY_BIGQUERY_ID}='
            f'{publish_end}'
            f'&p_message_id_{settings.REDASH_JOB_QUERY_BIGQUERY_ID}={obj.id}#169041'
        )

        return format_html(
            f'<a href="{link_bigquery}">Explore Redash</a>'
        )

    redash_link.short_description = 'Explore in Redash'

    def save_model(self, request, obj, form, change):
        if not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """ Allow deletion only during Draft stage. """
        if obj and obj.status == models.Job.DRAFT:
            return True
        return False

    def has_publish_permission(self, request):
        return request.user.has_perm('base.change_job')

    def response_change(self, request, obj):
        # Add logs using admin system
        if '_cancel' in request.POST:
            obj.change_status(status=models.Job.CANCELED, user=request.user)
            return HttpResponseRedirect('.')
        elif '_schedule' in request.POST:
            obj.change_status(status=models.Job.SCHEDULED, user=request.user)
            return HttpResponseRedirect('.')
        elif '_duplicate' in request.POST:
            new_job = obj.duplicate(request.user)
            return HttpResponseRedirect(new_job.get_admin_url(full=False))
        return super().response_change(request, obj)

    def _changeform_view(self, request, *args, **kwargs):
        view = super()._changeform_view(request, *args, **kwargs)
        if hasattr(view, 'context_data'):
            obj = view.context_data['original']
            if obj and self.has_publish_permission(request):
                if obj.status in [models.Job.PUBLISHED, models.Job.SCHEDULED]:
                    view.context_data['show_cancel'] = True
                elif obj.status == models.Job.DRAFT:
                    view.context_data['show_schedule'] = True
                view.context_data['show_duplicate'] = True
        return view

    def _action_status_change(self, action, request, queryset):
        if action == 'schedule':
            status = models.Job.SCHEDULED
            no_action_message = 'Skipped {} already scheduled and published Jobs.'
            success_message = 'Scheduled {} Jobs.'
            clean_queryset = queryset.filter(status=models.Job.DRAFT)
        elif action == 'cancel':
            status = models.Job.CANCELED
            no_action_message = 'Skipped {} already canceled or completed Jobs.'
            success_message = 'Canceled {} Jobs.'
            clean_queryset = queryset.filter(
                Q(status=models.Job.PUBLISHED) |
                Q(status=models.Job.SCHEDULED) |
                Q(status=models.Job.DRAFT)
            )
        else:
            messages.success(request, 'Error no action')
            return

        no_jobs = clean_queryset.count()
        no_already_scheduled_jobs = queryset.count() - no_jobs

        for job in clean_queryset:
            job.change_status(status=status, user=request.user)

        if no_already_scheduled_jobs:
            messages.warning(request, no_action_message.format(no_already_scheduled_jobs))
        messages.success(request, success_message.format(no_jobs))

    def action_schedule_job(self, request, queryset):
        self._action_status_change('schedule', request, queryset)
    action_schedule_job.short_description = 'Schedule selected Jobs'
    action_schedule_job.allowed_permissions = (
        'publish',
    )

    def action_cancel_job(self, request, queryset):
        self._action_status_change('cancel', request, queryset)
    action_cancel_job.short_description = 'Cancel selected Jobs'
    action_cancel_job.allowed_permissions = (
        'publish',
    )

    def action_delete_job(self, request, queryset):
        original_job_count = queryset.count()
        queryset.filter(status=models.Job.DRAFT).delete()
        new_job_count = queryset.count()

        if original_job_count != new_job_count:
            message = f'Successfully deleted {original_job_count - new_job_count} Draft Jobs.'
            messages.success(request, message)

        if new_job_count:
            messages.warning(request, f'Cannot remove {new_job_count} Jobs not in Draft state.')
    action_delete_job.short_description = 'Delete selected Draft Jobs'
    action_delete_job.allowed_permissions = (
        'publish',
    )


class DistributionAdmin(admin.ModelAdmin):
    save_on_top = True

    list_display = [
        'id',
        'name',
    ]


class DistributionBundleAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = [
        'name',
        'code_name',
        'enabled',
        'distribution_list',
    ]

    def distribution_list(self, obj):
        return mark_safe(
            '<ul>' +
            ''.join([
                f'<li> {dist}' for dist in obj.distributions.values_list('name', flat=True)
            ]) +
            '</ul>'
        )
    distribution_list.short_description = 'Distributions'


class JobDailyPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'date',
        'job',
        'impression',
        'adj_impression',
        'click',
        'click_rate',
        'adj_click_rate',
        'block',
        'adj_block_rate',
        'dismiss',
        'go_to_scene2',
        'subscribe_success',
        'subscribe_error',
        'other_click',
        'data_fetched_on',
    ]
    search_fields = ['job']
    fieldsets = [
        ('Metrics', {
            'fields': (
                'job',
                'date',
                ('impression', 'impression_no_clients'),
                ('adj_impression', 'adj_impression_no_clients'),
                ('click', 'click_no_clients'),
                ('block', 'block_no_clients'),
                ('dismiss', 'dismiss_no_clients'),
                ('go_to_scene2', 'go_to_scene2_no_clients'),
                ('subscribe_success', 'subscribe_success_no_clients'),
                ('subscribe_error', 'subscribe_error_no_clients'),
                ('other_click', 'other_click_no_clients'),
                'details',
            ),
        }),
    ]
    actions = [
        actions.export_as_csv,
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DailyImpressionsAdmin(admin.ModelAdmin):
    list_display = [
        'date',
    ]
    fieldsets = [
        ('Metrics', {
            'fields': (
                'date',
                'details',
            ),
        }),
    ]
    actions = [
        actions.export_as_csv,
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
