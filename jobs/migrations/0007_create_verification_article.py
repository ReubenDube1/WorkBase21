from django.db import migrations


ARTICLE_SLUG = 'how-to-verify-a-remote-job-before-you-apply'

ARTICLE_BODY = (
    "<p>South Africa's job market has seen a real rise in fake listings — "
    "especially remote and work-from-home roles advertised through "
    "WhatsApp groups, social media, and copycat websites. Before you "
    "apply anywhere, a few checks take less than five minutes and can "
    "save you a lot of trouble.</p>"

    "<h2>1. Never pay to apply</h2>"
    "<p>A legitimate employer does not ask you to pay a registration fee, "
    "a \"training deposit,\" or courier fees before you've even been "
    "interviewed. If money is requested upfront, treat it as a serious "
    "warning sign.</p>"

    "<h2>2. Check the company actually exists</h2>"
    "<p>Search the company name on Google along with words like "
    "\"reviews\" or \"scam.\" Look them up on the CIPC company register if "
    "you want to confirm they're a registered South African business. A "
    "real company will also usually have a LinkedIn page with actual "
    "employees listed.</p>"

    "<h2>3. Look closely at the contact details</h2>"
    "<p>Be cautious of listings that only give a personal Gmail or "
    "WhatsApp number, with no company email domain, landline, or "
    "physical address anywhere. Legitimate employers are traceable.</p>"

    "<h2>4. Be wary of instant job offers</h2>"
    "<p>If you're offered a role with no interview, no reference checks, "
    "and no formal offer letter — especially for a role that pays "
    "unusually well for very little described work — slow down and "
    "verify everything before sharing any personal documents.</p>"

    "<h2>5. Protect your personal information</h2>"
    "<p>Never send your ID copy, banking details, or a copy of your "
    "signature to an employer before you've had a real interview and "
    "confirmed they're legitimate. Genuine onboarding paperwork comes "
    "after an offer, not before an interview.</p>"

    "<h2>6. Trust your instincts</h2>"
    "<p>If a listing feels off — vague job description, poor spelling "
    "throughout, pressure to \"act fast\" — it's worth pausing. It's "
    "always better to lose a few hours double-checking than to lose "
    "money or personal information to a scam.</p>"
)


def create_verification_article(apps, schema_editor):
    TrendingTopic = apps.get_model('jobs', 'TrendingTopic')
    if TrendingTopic.objects.filter(slug=ARTICLE_SLUG).exists():
        return
    TrendingTopic.objects.create(
        title="How to Verify a Remote Job Before You Apply",
        slug=ARTICLE_SLUG,
        description="Practical checks to spot fake job listings before you share your details or pay anything.",
        icon="🔍",
        author_name="WorkBase21 Team",
        body=ARTICLE_BODY,
        order=0,
        is_active=True,
    )


def remove_verification_article(apps, schema_editor):
    TrendingTopic = apps.get_model('jobs', 'TrendingTopic')
    TrendingTopic.objects.filter(slug=ARTICLE_SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_alter_job_created_at_alter_trendingtopic_created_at'),
    ]

    operations = [
        migrations.RunPython(create_verification_article, reverse_code=remove_verification_article),
    ]
