from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField


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


class Job(models.Model):
    """A single opportunity: job, internship, learnership, in-service
    trainee position, or bursary."""

    JOB = 'job'
    INTERNSHIP = 'internship'
    LEARNERSHIP = 'learnership'
    INSERVICE = 'inservice'
    BURSARY = 'bursary'

    TYPE_CHOICES = [
        (JOB, 'Job'),
        (INTERNSHIP, 'Internship'),
        (LEARNERSHIP, 'Learnership'),
        (INSERVICE, 'In-Service Trainee'),
        (BURSARY, 'Bursary'),
    ]

    PUBLIC = 'public'
    PRIVATE = 'private'
    SECTOR_CHOICES = [
        (PUBLIC, 'Public Sector'),
        (PRIVATE, 'Private Sector'),
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

    image = models.ImageField(
        upload_to='job_images/',
        blank=True,
        null=True,
        help_text="Optional banner image shown on the job card and job detail page (e.g. 800x450px, 16:9)."
    )

    # Five description blocks so ads can be placed between each one.
    description = RichTextUploadingField(
        "Description Part 1",
        help_text="Shown first, above the advertisement blocks."
    )
    description2 = RichTextUploadingField(
        "Description Part 2", blank=True
    )
    description3 = RichTextUploadingField(
        "Description Part 3", blank=True
    )
    description4 = RichTextUploadingField(
        "Description Part 4", blank=True
    )
    description5 = RichTextUploadingField(
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
    deadline = models.DateField()

    application_link = models.URLField(
        blank=True,
        help_text="External link the Apply button opens in a new tab. Leave blank if applicants must apply by email instead."
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

    created_at = models.DateTimeField(auto_now_add=True)
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
        if not self.application_link and not self.application_email:
            raise ValidationError(
                "Provide either an Application Link or an Application "
                "Email so job seekers know how to apply."
            )

    @property
    def slug(self):
        """A readable, SEO/share-friendly URL segment including the
        company name, e.g. 'software-developer-savanna-tech-solutions'.
        Computed on the fly (not stored) so it always reflects the
        current title/company — no migration or backfill needed, and
        it can never go stale or out of sync."""
        return slugify(f"{self.title}-{self.company.name}")[:200]

    @property
    def is_expired(self):
        return self.deadline < timezone.localdate()

    @property
    def type_label(self):
        return dict(self.TYPE_CHOICES).get(self.type, self.type)

    @property
    def sector_label(self):
        return dict(self.SECTOR_CHOICES).get(self.sector, self.sector)

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

    body = RichTextUploadingField(
        "Article Body — Part 1",
        blank=True,
        default='',
        config_name='article',
        help_text=(
            "Optional. Leave blank to keep this as a stat-only homepage "
            "card. Fill this in to publish a full article page — the "
            "homepage card automatically becomes clickable. Use the "
            "image icon in the toolbar to insert and position pictures "
            "anywhere in the text."
        )
    )
    body2 = RichTextUploadingField("Article Body — Part 2", blank=True, default='', config_name='article')
    body3 = RichTextUploadingField("Article Body — Part 3", blank=True, default='', config_name='article')
    body4 = RichTextUploadingField("Article Body — Part 4", blank=True, default='', config_name='article')
    body5 = RichTextUploadingField("Article Body — Part 5", blank=True, default='', config_name='article')

    author_name = models.CharField(
        max_length=100,
        blank=True,
        default="WorkBase21 Team",
        help_text="Shown on the article page. Only used if Article Body is filled in."
    )

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
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
