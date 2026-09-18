from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.db.models import Count
from .models import Company, Job, JobApplicationLink, Review, TrendingTopic, PageVisit


class JobApplicationLinkInline(admin.TabularInline):
    model = JobApplicationLink
    extra = 1
    fields = ('title', 'url', 'order')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_preview', 'website', 'job_count')
    search_fields = ('name',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;'
                'object-fit:contain;border-radius:6px;" />',
                obj.logo.url
            )
        return "—"
    logo_preview.short_description = "Logo"

    def job_count(self, obj):
        return obj.jobs.count()
    job_count.short_description = "Listings"


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'company', 'type', 'sector', 'location', 'salary',
        'deadline_display', 'views_display', 'is_active', 'created_at',
    )
    list_filter = ('type', 'sector', 'is_active', 'company')
    search_fields = (
        'title', 'company__name', 'location', 'description',
        'application_email',
    )
    date_hierarchy = 'created_at'
    list_editable = ('is_active',)
    autocomplete_fields = ('company',)
    inlines = [JobApplicationLinkInline]
    class Media:
        js = ('js/admin_insert_article_link.js',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _viewer_count=Count('page_visits__session_key', distinct=True)
        )

    def views_display(self, obj):
        url = reverse('admin_analytics') + f'#job-{obj.pk}'
        return mark_safe(
            f'<a href="{url}" title="See full analytics">{obj._viewer_count}</a>'
        )
    views_display.short_description = "Views"
    views_display.admin_order_field = '_viewer_count'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'company', 'type', 'sector', 'is_active', 'image', 'created_at')
        }),
        ('Description Part 1', {
            'fields': ('description',),
            'description': (
                'Shown first, above all advertisement blocks. To link to '
                'one of your Blog articles (e.g. the Z83 '
                'guide) from within this text, click where you want the '
                'link and use the "Insert Article Link" picker above the '
                'toolbar.'
            ),
        }),
        ('Description Part 2', {
            'fields': ('description2',),
            'classes': ('collapse',),
            'description': 'Ad slot 1 appears between Part 1 and Part 2.',
        }),
        ('Description Part 3', {
            'fields': ('description3',),
            'classes': ('collapse',),
            'description': 'Ad slot 2 appears between Part 2 and Part 3.',
        }),
        ('Description Part 4', {
            'fields': ('description4',),
            'classes': ('collapse',),
            'description': 'Ad slot 3 appears between Part 3 and Part 4.',
        }),
        ('Description Part 5', {
            'fields': ('description5',),
            'classes': ('collapse',),
            'description': 'Ad slot 4 appears between Part 4 and Part 5.',
        }),
        ('Details', {
            'fields': ('location', 'salary', 'deadline', 'deadline_text')
        }),
        ('How To Apply — Single Link/Email', {
            'fields': ('application_link', 'application_email'),
            'description': (
                'Use this for a normal single-position listing. Fill in '
                'EITHER the link OR the email. If this company has '
                'several positions open at once with different links '
                '(e.g. separate internship streams), leave both of these '
                'blank and use "Multiple Application Options" below instead.'
            ),
        }),
        ('Public Sector Documents', {
            'fields': ('z83_form',),
            'classes': ('collapse',),
            'description': 'Only shown to job seekers when Sector is set to Public Sector.',
        }),
    )

    def deadline_display(self, obj):
        return obj.deadline_display or "—"
    deadline_display.short_description = "Deadline"
    deadline_display.admin_order_field = 'deadline'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'article-links.json',
                self.admin_site.admin_view(self.article_links_json),
                name='jobs_job_article_links',
            ),
        ]
        return custom_urls + urls

    def article_links_json(self, request):
        """Powers the 'Insert Article Link' picker in the description
        editors — returns every published article as {title, url} so
        the admin can insert a link without leaving the page or
        looking up the URL manually."""
        articles = TrendingTopic.objects.filter(
            is_active=True
        ).exclude(body='').order_by('title')
        data = [
            {'title': a.title, 'url': a.get_absolute_url()}
            for a in articles
        ]
        return JsonResponse(data, safe=False)

admin.site.site_header = "WorkBase21 Administration"
admin.site.site_title = "WorkBase21 Admin"
admin.site.index_title = "Manage Jobs, Internships, Learnerships & Bursaries"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('name', 'role', 'message')
    list_editable = ('is_published',)


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    """Read-only log of raw page visits — mainly for spot-checking.
    For the aggregated numbers (totals, unique visitors, most-viewed
    jobs, trends over time), use the Site Analytics dashboard linked
    at the top of the admin home page instead."""
    list_display = ('path', 'job', 'session_key', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('path', 'session_key')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TrendingTopic)
class TrendingTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'stat', 'icon', 'has_article', 'order', 'is_active', 'updated_at')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description', 'body', 'body2', 'body3', 'body4', 'body5')
    prepopulated_fields = {'slug': ('title',)}

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:36px;width:56px;'
                'object-fit:cover;border-radius:6px;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Image"

    fieldsets = (
        ('Homepage Card', {
            'fields': ('title', 'description', 'stat', 'icon', 'image', 'order', 'is_active', 'created_at'),
            'description': 'Every entry shows as a short stat card on the homepage regardless of the fields below.',
        }),
        ('Full Article — Setup (optional)', {
            'fields': ('slug', 'author_name'),
            'description': (
                'Fill in Article Body — Part 1 below to publish this as a full, '
                'clickable article page — great for original career-advice '
                'content like CV tips or Z83 form guides. Leave all body parts '
                'blank to keep this as a stat-only homepage card.'
            ),
        }),
        ('Article Body — Part 1', {
            'fields': ('body',),
            'description': 'Use the image icon in the toolbar to insert and position pictures anywhere in the text.',
        }),
        ('Article Body — Part 2', {
            'fields': ('body2',),
            'classes': ('collapse',),
        }),
        ('Article Body — Part 3', {
            'fields': ('body3',),
            'classes': ('collapse',),
        }),
        ('Article Body — Part 4', {
            'fields': ('body4',),
            'classes': ('collapse',),
        }),
        ('Article Body — Part 5', {
            'fields': ('body5',),
            'classes': ('collapse',),
        }),
    )

    def has_article(self, obj):
        return obj.is_article
    has_article.boolean = True
    has_article.short_description = "Article?"
