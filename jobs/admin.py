from django.contrib import admin
from django.utils.html import format_html
from .models import Company, Job, Review, TrendingTopic


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
        'deadline', 'is_active', 'created_at',
    )
    list_filter = ('type', 'sector', 'is_active', 'company')
    search_fields = (
        'title', 'company__name', 'location', 'description',
        'application_email',
    )
    date_hierarchy = 'created_at'
    list_editable = ('is_active',)
    autocomplete_fields = ('company',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'company', 'type', 'sector', 'is_active', 'image')
        }),
        ('Description Part 1', {
            'fields': ('description',),
            'description': 'Shown first, above all advertisement blocks.',
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
            'fields': ('location', 'salary', 'deadline')
        }),
        ('How To Apply', {
            'fields': ('application_link', 'application_email'),
            'description': (
                'Fill in EITHER the link OR the email — whichever one the '
                'employer wants applicants to use. You can fill in both if '
                'you want to show both options.'
            ),
        }),
        ('Public Sector Documents', {
            'fields': ('z83_form',),
            'classes': ('collapse',),
            'description': 'Only shown to job seekers when Sector is set to Public Sector.',
        }),
    )

admin.site.site_header = "WorkBase21 Administration"
admin.site.site_title = "WorkBase21 Admin"
admin.site.index_title = "Manage Jobs, Internships, Learnerships & Bursaries"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('name', 'role', 'message')
    list_editable = ('is_published',)


@admin.register(TrendingTopic)
class TrendingTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'stat', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
