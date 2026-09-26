from django.conf import settings
from django.db import models
from django.utils.text import slugify

from jobs.models import Job, Skill


class Qualification(models.Model):
    """A canonical, specific qualification (e.g. 'BSc Computer
    Science', 'National Diploma: Information Technology', 'Matric').

    This is distinct from Job.qualification_level (Phase 1), which is
    a coarse level used for quick filtering — this is the actual named
    qualification. Reusable across user profiles, and later, job
    requirements and career paths."""

    LEVEL_CHOICES = Job.QUALIFICATION_CHOICES  # reuse the same coarse levels

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    level = models.CharField(
        max_length=20, choices=LEVEL_CHOICES, blank=True,
        help_text="Roughly where this sits among the site's qualification levels — optional, helps with matching in a later phase."
    )
    skills = models.ManyToManyField(
        Skill, blank=True, related_name='qualifications',
        help_text="Skills this qualification usually covers. Suggested to job seekers who list it.",
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or 'qualification'
            slug, n = base, 2
            while Qualification.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """A job seeker's profile — qualification, skills, experience and
    location. Created automatically on registration. This phase only
    covers the profile itself (view/edit); the matching engine,
    personalized feed and skills-gap analyzer that will read from it
    come in later phases."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    location = models.CharField(
        max_length=100, blank=True, help_text="e.g. Johannesburg, Gauteng"
    )
    qualification_level = models.CharField(
        max_length=20, choices=Job.QUALIFICATION_CHOICES, blank=True,
        verbose_name="Highest qualification level"
    )
    qualifications = models.ManyToManyField(
        Qualification, blank=True, related_name='profiles',
        help_text="Your specific qualification(s)."
    )
    experience_level = models.CharField(
        max_length=20, choices=Job.EXPERIENCE_CHOICES, blank=True
    )
    career_goal = models.CharField(
        max_length=150, blank=True,
        help_text="What role or field are you working towards? e.g. 'Data Analyst'"
    )
    skills = models.ManyToManyField(Skill, blank=True, related_name='profiles')
    bio = models.TextField(
        blank=True, max_length=1000,
        help_text="A short summary about yourself (optional)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_username()}'s profile"

    @property
    def qualification_label(self):
        return dict(Job.QUALIFICATION_CHOICES).get(self.qualification_level, '')

    @property
    def experience_label(self):
        return dict(Job.EXPERIENCE_CHOICES).get(self.experience_level, '')

    @property
    def is_complete(self):
        """Used to nudge a job seeker to finish their profile — not
        enforced anywhere yet, just available for later phases."""
        return bool(
            self.location and self.qualification_level
            and self.experience_level and self.skills.exists()
        )


class CareerPath(models.Model):
    """A configurable career path (e.g. Data Analyst, Software
    Developer) — associated skills, qualifications, and milestones.
    Admin-manageable data now; the public Career Explorer / roadmap
    pages that read from this come in a later phase."""

    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name='career_paths')
    qualifications = models.ManyToManyField(
        Qualification, blank=True, related_name='career_paths'
    )
    milestones = models.TextField(
        blank=True,
        help_text="Optional. One milestone per line, in the order a job seeker would tackle them, e.g. 'Learn Python basics'."
    )
    next_paths = models.ManyToManyField(
        'self', blank=True, symmetrical=False, related_name='previous_paths',
        verbose_name="Next career steps",
        help_text="Careers people typically move on to from this one, e.g. Data Analyst → Data Scientist.",
    )
    job_titles = models.TextField(
        blank=True,
        verbose_name="Related job titles",
        help_text=(
            "Optional. One job title per line (e.g. 'Data Analyst', 'BI Analyst'). "
            "Listings whose title contains any of these show up as related jobs."
        ),
    )
    icon = models.CharField(max_length=10, blank=True, help_text="An emoji, e.g. 📊")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Career Path"
        verbose_name_plural = "Career Paths"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:160]
            slug = base_slug
            counter = 2
            while CareerPath.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('career_detail', kwargs={'slug': self.slug})

    @property
    def job_title_list(self):
        return [t.strip() for t in self.job_titles.splitlines() if t.strip()]

    @property
    def milestone_list(self):
        return [m.strip() for m in self.milestones.splitlines() if m.strip()]


class TrackedJob(models.Model):
    """A job a job seeker has saved and/or is tracking an application
    for. 'Saved' is simply the first status, so saved jobs and the
    application tracker are the same list — no duplicate records."""

    SAVED = 'saved'
    APPLIED = 'applied'
    ASSESSMENT = 'assessment'
    INTERVIEW = 'interview'
    OFFER = 'offer'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (SAVED, 'Saved'),
        (APPLIED, 'Applied'),
        (ASSESSMENT, 'Assessment'),
        (INTERVIEW, 'Interview'),
        (OFFER, 'Offer'),
        (REJECTED, 'Rejected'),
    ]
    # Statuses that mean the job seeker has actually applied.
    APPLIED_STATUSES = {APPLIED, ASSESSMENT, INTERVIEW, OFFER, REJECTED}
    # Statuses that mean the employer responded in some way.
    RESPONDED_STATUSES = {ASSESSMENT, INTERVIEW, OFFER, REJECTED}

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tracked_jobs'
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='tracked_by')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SAVED)
    applied_at = models.DateField(null=True, blank=True, verbose_name="Date applied")
    reminder_date = models.DateField(
        null=True, blank=True,
        help_text="Optional — e.g. a follow-up date or interview date. Shown on your tracker as it gets close."
    )
    notes = models.TextField(blank=True, max_length=2000)
    # Remembered even if the status later moves on to Rejected, so
    # "interviews reached" in the stats stays accurate.
    reached_interview = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('user', 'job')
        verbose_name = "Tracked Job"
        verbose_name_plural = "Tracked Jobs"

    def __str__(self):
        return f"{self.user.get_username()} — {self.job.title} ({self.get_status_display()})"

    @property
    def has_applied(self):
        return self.status in self.APPLIED_STATUSES

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.status in self.APPLIED_STATUSES and not self.applied_at:
            self.applied_at = timezone.localdate()
        if self.status in (self.INTERVIEW, self.OFFER):
            self.reached_interview = True
        super().save(*args, **kwargs)


class SavedSearch(models.Model):
    """A job seeker's saved search. New listings matching it show up
    as in-app alerts — no email/SMS, so it costs nothing to run.

    'New' is tracked by job ID rather than 'Date Added', because
    admins can backdate a listing's Date Added; a newly added job
    always gets a higher ID regardless of the date set on it."""

    MAX_PER_USER = 10

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_searches'
    )
    job_type = models.CharField(max_length=20, blank=True)
    sector = models.CharField(max_length=10, blank=True)
    query = models.CharField(max_length=200, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    results_path = models.CharField(max_length=200, default='/search/')
    last_seen_job_id = models.PositiveIntegerField(default=0)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Saved Search"
        verbose_name_plural = "Saved Searches"

    def __str__(self):
        return f"{self.user.get_username()} — {self.describe()}"

    def describe(self):
        if self.job_type == Job.JOB and self.sector:
            parts = [dict(Job.SECTOR_CHOICES).get(self.sector, 'Jobs').replace(' Sector', ' Sector Jobs')]
        elif self.job_type:
            parts = [{
                Job.JOB: 'Jobs', Job.INTERNSHIP: 'Internships',
                Job.LEARNERSHIP: 'Learnerships', Job.BURSARY: 'Bursaries',
            }.get(self.job_type, 'Listings')]
        else:
            parts = ['All listings']
        if self.query:
            parts.append(f'"{self.query}"')
        f = self.filters or {}
        if f.get('qualification'):
            parts.append(dict(Job.QUALIFICATION_CHOICES).get(f['qualification'], f['qualification']))
        if f.get('experience'):
            parts.append(dict(Job.EXPERIENCE_CHOICES).get(f['experience'], f['experience']))
        if f.get('work_mode'):
            parts.append(dict(Job.WORK_MODE_CHOICES).get(f['work_mode'], f['work_mode']))
        if f.get('industry'):
            parts.append(dict(Job.INDUSTRY_CHOICES).get(f['industry'], f['industry']))
        if f.get('skill'):
            skill = Skill.objects.filter(slug=f['skill']).first()
            parts.append(skill.name if skill else f['skill'])
        if f.get('salary_min'):
            parts.append(f"R{int(f['salary_min']):,}+".replace(',', ' '))
        return ' · '.join(parts)

    def results_url(self):
        from urllib.parse import urlencode
        params = {}
        if self.query:
            params['q'] = self.query
        params.update(self.filters or {})
        return f"{self.results_path}?{urlencode(params)}" if params else self.results_path

    def matching_jobs(self):
        from jobs.search import apply_filter_params, keyword_filter
        qs = Job.objects.filter(is_active=True).select_related('company')
        if self.job_type:
            qs = qs.filter(type=self.job_type)
        if self.sector:
            qs = qs.filter(sector=self.sector)
        if self.query:
            qs = keyword_filter(qs, self.query)
        qs, _ = apply_filter_params(self.filters or {}, qs)
        return qs

    def new_jobs(self):
        return self.matching_jobs().filter(pk__gt=self.last_seen_job_id).order_by('-pk')

    @staticmethod
    def current_max_job_id():
        latest = Job.objects.order_by('-pk').values_list('pk', flat=True).first()
        return latest or 0
