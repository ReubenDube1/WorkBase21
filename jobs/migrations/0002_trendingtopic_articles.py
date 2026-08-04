import ckeditor_uploader.fields
import django.utils.timezone
from django.db import migrations, models


def populate_slugs(apps, schema_editor):
    """Backfill a unique slug for any TrendingTopic rows that already
    existed before this migration (e.g. previously seeded stat cards)."""
    from django.utils.text import slugify
    TrendingTopic = apps.get_model('jobs', 'TrendingTopic')
    seen = set()
    for topic in TrendingTopic.objects.all():
        base_slug = slugify(topic.title)[:170] or f"topic-{topic.pk}"
        slug = base_slug
        counter = 2
        while slug in seen or TrendingTopic.objects.filter(slug=slug).exclude(pk=topic.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        seen.add(slug)
        topic.slug = slug
        topic.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='trendingtopic',
            options={'ordering': ['order', 'id'], 'verbose_name': 'Trending Topic', 'verbose_name_plural': 'Trending Topics & Articles'},
        ),
        migrations.AlterField(
            model_name='trendingtopic',
            name='description',
            field=models.CharField(blank=True, help_text='Short teaser shown on the homepage card.', max_length=250),
        ),
        migrations.AddField(
            model_name='trendingtopic',
            name='slug',
            field=models.SlugField(blank=True, max_length=180, null=True, unique=True, help_text='Used in the article URL. Leave blank to auto-generate from the title.'),
        ),
        migrations.AddField(
            model_name='trendingtopic',
            name='body',
            field=ckeditor_uploader.fields.RichTextUploadingField(blank=True, default='', help_text="Optional. Leave blank to keep this as a stat-only homepage card. Fill this in to publish a full article page — the homepage card automatically becomes clickable.", verbose_name='Article Body'),
        ),
        migrations.AddField(
            model_name='trendingtopic',
            name='author_name',
            field=models.CharField(blank=True, default='WorkBase21 Team', help_text='Shown on the article page. Only used if Article Body is filled in.', max_length=100),
        ),
        migrations.AddField(
            model_name='trendingtopic',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='trendingtopic',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(populate_slugs, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='trendingtopic',
            name='slug',
            field=models.SlugField(blank=True, max_length=180, unique=True, help_text='Used in the article URL. Leave blank to auto-generate from the title.'),
        ),
    ]
