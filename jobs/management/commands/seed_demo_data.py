import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Company, Job, Review, TrendingTopic


class Command(BaseCommand):
    help = "Creates sample companies, listings, reviews and trends so the site isn't empty on first run."

    def handle(self, *args, **options):
        if Job.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Jobs already exist — skipping seed. Delete existing jobs first if you want to reseed."
            ))
            return

        companies_data = [
            "Savanna Tech Solutions",
            "Highveld Retail Group",
            "Vaal Financial Services",
            "Cape Coastal Logistics",
            "Limpopo Agri Innovations",
            "Department of Public Works (Demo)",
        ]
        companies = [Company.objects.create(name=name) for name in companies_data]

        today = timezone.localdate()

        listings = [
            {
                "title": "Junior Software Developer",
                "company": companies[0],
                "type": Job.JOB,
                "sector": Job.PRIVATE,
                "location": "Johannesburg, Gauteng",
                "salary": "R25,000 - R32,000 per month",
                "days_ahead": 21,
                "apply": "link",
            },
            {
                "title": "Administrative Officer",
                "company": companies[5],
                "type": Job.JOB,
                "sector": Job.PUBLIC,
                "location": "Pretoria, Gauteng",
                "salary": "R18,000 - R22,000 per month",
                "days_ahead": 14,
                "apply": "email",
            },
            {
                "title": "Graduate IT Internship Programme",
                "company": companies[0],
                "type": Job.INTERNSHIP,
                "sector": Job.PRIVATE,
                "location": "Pretoria, Gauteng",
                "salary": "R8,000 monthly stipend",
                "days_ahead": 30,
                "apply": "link",
            },
            {
                "title": "Retail Operations Internship",
                "company": companies[1],
                "type": Job.INTERNSHIP,
                "sector": Job.PRIVATE,
                "location": "Durban, KwaZulu-Natal",
                "salary": "R7,500 monthly stipend",
                "days_ahead": 25,
                "apply": "email",
            },
            {
                "title": "Business Administration Learnership (NQF 5)",
                "company": companies[1],
                "type": Job.LEARNERSHIP,
                "sector": Job.PRIVATE,
                "location": "Cape Town, Western Cape",
                "salary": "R4,500 monthly allowance",
                "days_ahead": 40,
                "apply": "link",
            },
            {
                "title": "Agricultural Sciences Learnership",
                "company": companies[4],
                "type": Job.LEARNERSHIP,
                "sector": Job.PRIVATE,
                "location": "Polokwane, Limpopo",
                "salary": "R5,000 monthly allowance",
                "days_ahead": 35,
                "apply": "link",
            },
            {
                "title": "In-Service Trainee: Mechanical Engineering",
                "company": companies[3],
                "type": Job.INSERVICE,
                "sector": Job.PRIVATE,
                "location": "Gqeberha, Eastern Cape",
                "salary": "R6,000 monthly stipend",
                "days_ahead": 28,
                "apply": "link",
            },
            {
                "title": "In-Service Trainee: Financial Accounting",
                "company": companies[2],
                "type": Job.INSERVICE,
                "sector": Job.PRIVATE,
                "location": "Bloemfontein, Free State",
                "salary": "R6,500 monthly stipend",
                "days_ahead": 18,
                "apply": "email",
            },
            {
                "title": "STEM Undergraduate Bursary",
                "company": companies[4],
                "type": Job.BURSARY,
                "sector": Job.PRIVATE,
                "location": "Thohoyandou, Limpopo",
                "salary": "Full tuition + accommodation",
                "days_ahead": 60,
                "apply": "link",
            },
            {
                "title": "Actuarial Sciences Bursary",
                "company": companies[2],
                "type": Job.BURSARY,
                "sector": Job.PRIVATE,
                "location": "Nationwide",
                "salary": "Full tuition + monthly allowance",
                "days_ahead": 50,
                "apply": "email",
            },
            {
                "title": "Municipal Finance Intern",
                "company": companies[5],
                "type": Job.JOB,
                "sector": Job.PUBLIC,
                "location": "Polokwane, Limpopo",
                "salary": "R15,000 per month",
                "days_ahead": 20,
                "apply": "email",
            },
        ]

        description_parts = [
            (
                "<p>This is sample demo content generated by the "
                "<code>seed_demo_data</code> management command. Replace it "
                "with real listing details from the Django admin.</p>"
                "<ul><li>Requirement one</li><li>Requirement two</li>"
                "<li>Requirement three</li></ul>"
            ),
            "<p>Key responsibilities go here — this is Description Part 2.</p>",
            "<p>Minimum qualifications go here — this is Description Part 3.</p>",
            "<p>Additional benefits or notes — this is Description Part 4.</p>",
            "<p>Closing remarks or how to apply details — this is Description Part 5.</p>",
        ]

        for item in listings:
            kwargs = dict(
                title=item["title"],
                company=item["company"],
                type=item["type"],
                sector=item["sector"],
                description=description_parts[0],
                description2=description_parts[1],
                description3=description_parts[2],
                description4=description_parts[3],
                description5=description_parts[4],
                location=item["location"],
                salary=item["salary"],
                deadline=today + datetime.timedelta(days=item["days_ahead"]),
            )
            if item["apply"] == "email":
                kwargs["application_email"] = "careers@example.com"
            else:
                kwargs["application_link"] = "https://example.com/apply"

            Job.objects.create(**kwargs)

        # --- Sample reviews for the homepage ---
        reviews = [
            {
                "name": "Thandiwe M.",
                "role": "Marketing Graduate",
                "rating": 5,
                "message": "I found my first internship within two weeks of using WorkBase21. The filters made it so easy to find relevant listings.",
            },
            {
                "name": "Sipho N.",
                "role": "IT Learnership Alumnus",
                "rating": 5,
                "message": "Clean site, real listings, and the apply links actually work. Highly recommend to any student looking for a learnership.",
            },
            {
                "name": "Karabo Youth Development Trust",
                "role": "Partner Organisation",
                "rating": 5,
                "message": "We've partnered with WorkBase21 to promote our bursary programme and have seen a steady increase in quality applicants.",
            },
        ]
        for r in reviews:
            Review.objects.create(**r)

        # --- Sample trending topics for the homepage ---
        trends = [
            {
                "title": "Data & Analytics Roles",
                "description": "Demand for data analysts and BI roles keeps climbing across finance and retail.",
                "stat": "+18% this quarter",
                "icon": "📊",
                "order": 1,
            },
            {
                "title": "Public Sector Graduate Programmes",
                "description": "More municipalities and departments are opening structured graduate intakes.",
                "stat": "120+ open listings",
                "icon": "🏛️",
                "order": 2,
            },
            {
                "title": "Renewable Energy Learnerships",
                "description": "Solar and green-energy learnerships are growing fast in Limpopo and the Western Cape.",
                "stat": "+25% year-on-year",
                "icon": "🌱",
                "order": 3,
            },
            {
                "title": "Remote-Friendly Internships",
                "description": "More companies now offer hybrid or fully remote internship placements.",
                "stat": "1 in 3 internships",
                "icon": "💻",
                "order": 4,
            },
        ]
        for t in trends:
            TrendingTopic.objects.create(**t)

        # --- Sample full articles (Career Resources) ---
        articles = [
            {
                "title": "How to Fill In the Z83 Form for Public Sector Jobs",
                "description": "A step-by-step walkthrough of South Africa's standard government job application form.",
                "icon": "📝",
                "order": 5,
                "author_name": "WorkBase21 Team",
                "body": (
                    "<p>This is placeholder sample content generated by the "
                    "<code>seed_demo_data</code> command — replace it with a "
                    "real, original guide before publishing. A genuinely useful "
                    "Z83 article should cover:</p>"
                    "<ul>"
                    "<li>Where to download the current official Z83 form</li>"
                    "<li>Section-by-section guidance on filling it in correctly</li>"
                    "<li>Common mistakes that get applications disqualified</li>"
                    "<li>What supporting documents to attach</li>"
                    "</ul>"
                    "<p>Write this from real, verified knowledge of the current "
                    "DPSA requirements rather than generic filler — that's what "
                    "makes it genuinely useful (and what AdSense reviewers are "
                    "actually checking for).</p>"
                ),
            },
            {
                "title": "Learnerships vs Internships vs In-Service Training",
                "description": "Understand the real differences before you apply, so you choose the right path.",
                "icon": "🎓",
                "order": 6,
                "author_name": "WorkBase21 Team",
                "body": (
                    "<p>This is placeholder sample content generated by the "
                    "<code>seed_demo_data</code> command — replace it with your "
                    "own original comparison. Cover things like:</p>"
                    "<ul>"
                    "<li>How each is structured (duration, stipend, NQF credit)</li>"
                    "<li>Who's eligible for each one</li>"
                    "<li>How to decide which fits your situation</li>"
                    "</ul>"
                ),
            },
        ]
        for a in articles:
            TrendingTopic.objects.create(**a)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(companies)} companies, {len(listings)} listings, "
            f"{len(reviews)} reviews, {len(trends)} trending topics and "
            f"{len(articles)} sample articles."
        ))
