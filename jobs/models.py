from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Company(models.Model):
    """A company that posts opportunities on WorkBase21."""

    name = models.CharField(max_length=200)
    logo = models.ImageField(
        upload_to='company_logos/',
        blank=True,
        null=True,
        help_text="Square logo works best (e.g. 200x200px)."
    )
    website = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name


class Skill(models.Model):
    """A canonical skill, reusable across jobs for filtering and (in a
    later phase) skills-matching. Kept as a simple flat list managed
    from the admin — no need for job posters to type free text that
    won't match up."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    related_skills = models.ManyToManyField(
        'self', blank=True, symmetrical=True,
        help_text=(
            "Skills that commonly go together, e.g. Statistics ↔ Data Analysis. "
            "Works both ways automatically. Used to suggest skills to job seekers."
        ),
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:80] or 'skill'
            slug, n = base, 2
            while Skill.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Job(models.Model):
    """A single opportunity: job, internship, learnership, or bursary."""

    JOB = 'job'
    INTERNSHIP = 'internship'
    LEARNERSHIP = 'learnership'
    BURSARY = 'bursary'

    TYPE_CHOICES = [
        (JOB, 'Job'),
        (INTERNSHIP, 'Internship'),
        (LEARNERSHIP, 'Learnership'),
        (BURSARY, 'Bursary'),
    ]

    PUBLIC = 'public'
    PRIVATE = 'private'
    SECTOR_CHOICES = [
        (PUBLIC, 'Public Sector'),
        (PRIVATE, 'Private Sector'),
    ]

    QUALIFICATION_CHOICES = [
        ('none', 'No formal qualification required'),
        ('matric', 'Matric / Grade 12'),
        ('certificate', 'Certificate'),
        ('diploma', 'Diploma'),
        ('degree', "Bachelor's Degree"),
        ('honours', 'Honours Degree'),
        ('masters', "Master's Degree"),
        ('doctorate', 'Doctorate'),
    ]

    EXPERIENCE_CHOICES = [
        ('entry', 'Entry-level / No experience'),
        ('1_2', '1–2 years'),
        ('3_5', '3–5 years'),
        ('5_plus', '5+ years'),
        ('senior', 'Senior / Executive'),
    ]

    WORK_MODE_CHOICES = [
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]

    INDUSTRY_CHOICES = [
        ('it', 'IT & Technology'),
        ('finance', 'Finance & Accounting'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education & Training'),
        ('engineering', 'Engineering'),
        ('retail', 'Retail & Sales'),
        ('government', 'Government & Public Sector'),
        ('marketing', 'Marketing & Communications'),
        ('agriculture', 'Agriculture'),
        ('construction', 'Construction & Built Environment'),
        ('logistics', 'Logistics & Supply Chain'),
        ('hospitality', 'Hospitality & Tourism'),
        ('legal', 'Legal'),
        ('manufacturing', 'Manufacturing'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='jobs'
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=JOB)
    sector = models.CharField(
        max_length=10,
        choices=SECTOR_CHOICES,
        default=PRIVATE,
        help_text=(
            "Only used for the 'Jobs' category — lets job seekers filter "
            "between Public Sector and Private Sector roles."
        )
    )

    # --- Structured filter fields (all optional) --------------------
    # Left blank ("Not specified") a listing simply won't be narrowed
    # out by that particular filter — existing jobs keep working with
    # nothing to fill in.
    qualification_level = models.CharField(
        max_length=20, choices=QUALIFICATION_CHOICES, blank=True,
        help_text="Powers the 'Qualification' search filter. Leave blank if not specified."
    )
    experience_level = models.CharField(
        max_length=20, choices=EXPERIENCE_CHOICES, blank=True,
        help_text="Powers the 'Experience' search filter. Leave blank if not specified."
    )
    work_mode = models.CharField(
        max_length=10, choices=WORK_MODE_CHOICES, blank=True,
        help_text="Powers the 'Remote/On-site' search filter. Leave blank if not specified."
    )
    industry = models.CharField(
        max_length=20, choices=INDUSTRY_CHOICES, blank=True,
        help_text="Powers the 'Industry' search filter. Leave blank if not specified."
    )
    skills = models.ManyToManyField(
        Skill, blank=True, related_name='jobs',
        help_text="Powers the 'Skill' search filter and the Job-Market Analytics 'most requested skills' chart."
    )
    salary_min = models.PositiveIntegerField(
        blank=True, null=True,
        verbose_name="Minimum salary (for filtering only)",
        help_text=(
            "Optional whole number, e.g. 15000. Only used to power the "
            "'minimum salary' search filter — it is NOT shown to job "
            "seekers; the Salary field above is still what's displayed."
        )
    )

    image = models.ImageField(
        upload_to='job_images/',
        blank=True,
        null=True,
        help_text="Optional banner image shown on the job card and job detail page (e.g. 800x450px, 16:9)."
    )

    # Five description blocks so ads can be placed between each one.
    description = models.TextField(
        "Description Part 1",
        help_text="Shown first, above the advertisement blocks."
    )
    description2 = models.TextField(
        "Description Part 2", blank=True
    )
    description3 = models.TextField(
        "Description Part 3", blank=True
    )
    description4 = models.TextField(
        "Description Part 4", blank=True
    )
    description5 = models.TextField(
        "Description Part 5", blank=True
    )

    location = models.CharField(
        max_length=100,
        help_text="e.g. Johannesburg, Gauteng"
    )
    salary = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. R15,000 - R20,000 per month, or 'Market Related'"
    )

    deadline = models.DateField(
        blank=True,
        null=True,
        help_text="Leave blank if there's no fixed date — use Deadline (text) below instead."
    )
    deadline_text = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Deadline (text)",
        help_text=(
            "Use this instead of a date when no specific deadline was "
            "given, e.g. 'Until filled', 'Open until further notice', "
            "'Ongoing applications'. If both are filled in, this text "
            "is shown instead of the date."
        )
    )

    application_link = models.URLField(
        blank=True,
        help_text=(
            "External link the Apply button opens in a new tab. Leave "
            "blank if applicants must apply by email, or if you're using "
            "Multiple Application Options below instead."
        )
    )
    application_email = models.EmailField(
        blank=True,
        help_text="Fill this in if applicants must apply by email instead of a link. It will show as a clickable, copyable email address."
    )

    z83_form = models.FileField(
        upload_to='z83_forms/',
        blank=True,
        null=True,
        verbose_name="Z83 Form",
        help_text="Upload the Z83 application form (PDF). Only shown for Public Sector jobs."
    )

    created_at = models.DateTimeField(
        "Date Added",
        default=timezone.now,
        help_text="Defaults to right now, but you can set this to any date/time — useful for backdating a listing."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Untick to hide this listing without deleting it."
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} at {self.company.name}"

    def get_absolute_url(self):
        return reverse('job_detail', kwargs={'pk': self.pk, 'slug': self.slug})

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if not self.deadline and not self.deadline_text:
            errors['deadline'] = (
                "Provide either a Deadline date or Deadline (text) so "
                "job seekers know when applications close."
            )
        # Note: application_link/application_email are intentionally NOT
        # required here anymore — a job posted with only Multiple
        # Application Options (added below, after saving) is valid too.
        if errors:
            raise ValidationError(errors)

    @property
    def slug(self):
        """A readable, SEO/share-friendly URL segment including the
        company name, e.g. 'software-developer-savanna-tech-solutions'.
        Computed on the fly (not stored) so it always reflects the
        current title/company — no migration or backfill needed, and
        it can never go stale or out of sync."""
        return slugify(f"{self.title}-{self.company.name}")[:200]

    @property
    def deadline_display(self):
        """What to show job seekers — the free-text version takes
        priority if both happen to be filled in."""
        if self.deadline_text:
            return self.deadline_text
        if self.deadline:
            return self.deadline.strftime('%d %b %Y')
        return ''

    @property
    def is_expired(self):
        # A job with no fixed date (deadline_text only, e.g. "Until
        # filled") never auto-expires — only a real date can do that.
        if not self.deadline:
            return False
        return self.deadline < timezone.localdate()

    @property
    def type_label(self):
        return dict(self.TYPE_CHOICES).get(self.type, self.type)

    @property
    def sector_label(self):
        return dict(self.SECTOR_CHOICES).get(self.sector, self.sector)

    @property
    def qualification_label(self):
        return dict(self.QUALIFICATION_CHOICES).get(self.qualification_level, '')

    @property
    def experience_label(self):
        return dict(self.EXPERIENCE_CHOICES).get(self.experience_level, '')

    @property
    def work_mode_label(self):
        return dict(self.WORK_MODE_CHOICES).get(self.work_mode, '')

    @property
    def industry_label(self):
        return dict(self.INDUSTRY_CHOICES).get(self.industry, '')

    @property
    def description_blocks(self):
        """All non-empty description parts, in order, for easy looping
        in templates when interleaving advertisement placeholders."""
        return [
            block for block in [
                self.description, self.description2, self.description3,
                self.description4, self.description5,
            ] if block
        ]

    @property
    def has_multiple_application_links(self):
        return self.application_links.exists()


class JobApplicationLink(models.Model):
    """One titled application link under a Job — for when a company
    posts several positions at once under a single listing (e.g. an
    internship intake with separate links per stream/department),
    each with its own title and apply link."""

    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name='application_links'
    )
    title = models.CharField(
        max_length=150,
        help_text="e.g. 'Marketing Internship', 'Finance Internship — Cape Town'"
    )
    url = models.URLField(
        verbose_name="Application Link",
        help_text="Where this specific option's Apply button goes."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Application Option"
        verbose_name_plural = "Multiple Application Options"

    def __str__(self):
        return f"{self.title} ({self.job.title})"


class Review(models.Model):
    """A testimonial shown on the homepage from a job seeker or
    organisation that has used WorkBase21."""

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    name = models.CharField(max_length=120)
    role = models.CharField(
        max_length=150,
        blank=True,
        help_text="e.g. 'Marketing Graduate' or an organisation name."
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, default=5
    )
    message = models.TextField()
    is_published = models.BooleanField(
        default=True,
        help_text="Untick to hide this review without deleting it."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.rating}★)"

    @property
    def star_range(self):
        return range(self.rating)


class TrendingTopic(models.Model):
    """An entry in the homepage 'What's Trending in the Job Market'
    section. Fully editable from the admin — no code changes needed.

    Every entry always shows as a short stat card on the homepage.
    If you also fill in the Article Body, it additionally becomes a
    full, clickable article page — useful for original career-advice
    content (CV tips, Z83 guides, etc.) without needing a separate
    blog app."""

    title = models.CharField(max_length=150)
    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True,
        help_text="Used in the article URL. Leave blank to auto-generate from the title."
    )
    description = models.CharField(
        max_length=250,
        blank=True,
        help_text="Short teaser shown on the homepage card."
    )
    stat = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. '+18% this quarter' or '2,340 openings'"
    )
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text="An emoji to display, e.g. 💻 📈 🏥"
    )

    image = models.ImageField(
        upload_to='trending_images/',
        blank=True,
        null=True,
        verbose_name="Featured Image",
        help_text=(
            "Optional. A simple picture upload — no rich text editor "
            "needed. Shown on the homepage 'Trending' card and at the "
            "top of the full article page, if one is published."
        )
    )

    body = models.TextField(
        "Article Body — Part 1",
        blank=True,
        default='',
        help_text=(
            "Optional. Leave blank to keep this as a stat-only homepage "
            "card. Fill this in to publish a full article page — the "
            "homepage card automatically becomes clickable. Use the "
            "image icon in the toolbar to insert and position pictures "
            "anywhere in the text."
        )
    )
    body2 = models.TextField("Article Body — Part 2", blank=True, default='')
    body3 = models.TextField("Article Body — Part 3", blank=True, default='')
    body4 = models.TextField("Article Body — Part 4", blank=True, default='')
    body5 = models.TextField("Article Body — Part 5", blank=True, default='')

    author_name = models.CharField(
        max_length=100,
        blank=True,
        default="WorkBase21 Team",
        help_text="Shown on the article page. Only used if Article Body is filled in."
    )

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(
        "Date Added",
        default=timezone.now,
        help_text="Defaults to right now, but you can set this to any date/time — useful for backdating an entry."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Trending Topic"
        verbose_name_plural = "Trending Topics & Articles"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)[:170]
            slug = base_slug
            counter = 2
            while TrendingTopic.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('trending_detail', kwargs={'slug': self.slug})

    @property
    def is_article(self):
        return bool(self.body)

    @property
    def body_blocks(self):
        """All non-empty article body parts, in order, for looping in
        the article template — lets images/text be paced across
        several boxes instead of one long block."""
        return [
            block for block in [
                self.body, self.body2, self.body3, self.body4, self.body5,
            ] if block
        ]


class PageVisit(models.Model):
    """One logged page view, written by VisitTrackingMiddleware for every
    real page request (static/media/admin/ckeditor excluded). Powers the
    'Site Visits' analytics screen in the admin — total visits, unique
    visitors, busiest pages, and traffic over time.

    Kept deliberately minimal for privacy: no IP addresses are stored,
    just the anonymous session key Django already issues."""

    path = models.CharField(max_length=500, db_index=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    job = models.ForeignKey(
        Job, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='page_visits',
        help_text="Set automatically when the visited page was a job detail page."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Site Visit"
        verbose_name_plural = "Site Visits"

    def __str__(self):
        return f"{self.path} @ {self.created_at:%Y-%m-%d %H:%M}"
