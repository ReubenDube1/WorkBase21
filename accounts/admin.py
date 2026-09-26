from django.contrib import admin

from .models import CareerPath, Qualification, SavedSearch, TrackedJob, UserProfile


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')
    list_filter = ('level',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('skills',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Read-mostly — job seekers manage their own profile from the
    site. Useful here mainly for support/debugging."""
    list_display = (
        'user', 'location', 'qualification_level', 'experience_level',
        'career_goal', 'updated_at',
    )
    list_filter = ('qualification_level', 'experience_level')
    search_fields = ('user__username', 'user__email', 'location', 'career_goal')
    filter_horizontal = ('skills', 'qualifications')
    autocomplete_fields = ()


@admin.register(CareerPath)
class CareerPathAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'is_active', 'order')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('skills', 'qualifications', 'next_paths')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'icon', 'description', 'is_active', 'order'),
        }),
        ('Requirements', {
            'fields': ('skills', 'qualifications'),
        }),
        ('Milestones', {
            'fields': ('milestones',),
            'description': 'One milestone per line, in order.',
        }),
        ('Career Graph', {
            'fields': ('next_paths', 'job_titles'),
            'description': (
                "Next career steps appear as a path map on the career page "
                "(and this career shows as 'Often comes from' on theirs). "
                "Related job titles find listings by title, in addition to shared skills."
            ),
        }),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        career = form.instance
        if career.next_paths.filter(pk=career.pk).exists():
            career.next_paths.remove(career)
            self.message_user(
                request, "A career path can't be its own next step — that link was removed.",
                level='warning',
            )


@admin.register(TrackedJob)
class TrackedJobAdmin(admin.ModelAdmin):
    """Read-mostly — job seekers manage their own tracker from the
    site. Here mainly for support and to see which listings people
    save and apply to."""
    list_display = ('user', 'job', 'status', 'applied_at', 'reminder_date', 'updated_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'job__title', 'job__company__name')
    raw_id_fields = ('user', 'job')


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'created_at', 'last_seen_at')
    search_fields = ('user__username', 'query')
    raw_id_fields = ('user',)

    def description(self, obj):
        return obj.describe()
