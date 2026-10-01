"""Adds ready-to-edit DRAFT blog articles (hidden until you publish them).

    python manage.py seed_article_drafts

Each draft is created with "Is active" UNTICKED, so nothing appears on the
public site until you open it in the admin (Trending Topics & Articles),
read it, make it yours, and tick "Is active".

Safe to run more than once: a draft is skipped if an article with the same
title already exists, and existing articles are never changed.

BEFORE YOU PUBLISH EACH ONE:
  * Read it all. Fix anything that doesn't match what you know.
  * Add something only you can: a real example, a tip from experience, a
    South African detail. Original, first-hand content is what makes an
    article valuable (and is what Google's reviewers look for).
  * Check the facts that can change (marked below) against official sources.
  * Add a picture with an "alt" description if you have a suitable one.
  * Link related articles using the "Insert Article Link" picker on jobs.
"""
from django.core.management.base import BaseCommand

from jobs.models import TrendingTopic

# Facts worth re-checking against official sources before publishing:
#  * "Learnership / SETA / NQF / work-back" definitions (article 1)
#  * Section 195 of the Constitution and the Batho Pele principles (article 3)
#  * Whether departments you care about still use the steps described (article 3)

DRAFTS = [
    {
        'title': 'Learnership, Internship, Bursary or Apprenticeship? A Clear Guide to Choosing in South Africa',
        'description': ("These words sound alike but mean different things. Learn what each one is, who it "
                        "is for, and how to pick the right one before you apply."),
        'icon': '🎓',
        'order': 20,
        'body': """
<p>Adverts for opportunities in South Africa use a handful of words that sound alike but mean quite different things: learnership, internship, bursary and apprenticeship. Applying for the wrong one wastes your time, so here is what each really is, who it is for, and how to choose.</p>

<h2>Learnerships</h2>
<p>A learnership is a structured programme that mixes classroom learning (theory) with practical work at an employer, and it leads to a nationally recognised qualification registered on the National Qualifications Framework (NQF). Learnerships are normally linked to a Sector Education and Training Authority (SETA), the body that oversees skills training in a particular industry. You, the employer and a training provider usually sign an agreement for a fixed period, often around 12 months, and you receive a monthly stipend. A stipend is an allowance and is not the same as a salary.</p>
<p><strong>Best for:</strong> people with a Grade 12 (matric) or an equivalent qualification who want a qualification and workplace experience at the same time. Many learnerships do not require any previous work experience.</p>

<h2>Internships</h2>
<p>An internship gives you workplace experience, usually after you have finished (or nearly finished) a diploma or degree. It does not normally lead to a new qualification. The value lies in the experience, the references and the contacts you build. Internships are usually fixed-term, often between 6 and 24 months, and many pay a stipend. Employers often state clearly that an internship does not guarantee permanent employment at the end.</p>
<p><strong>Best for:</strong> graduates and final-year students who have the qualification but not the experience that most entry-level jobs ask for.</p>

<h2>Bursaries</h2>
<p>A bursary pays for part or all of your studies. This can include tuition, accommodation, books and sometimes a living allowance. Many bursaries come with conditions: you may need to keep a minimum average, study a particular field and, in some cases, <strong>work for the funder after you graduate</strong> for as long as they paid for your studies (often called "work-back"). Closing dates vary widely, and many fall months before the academic year starts, so plan well ahead.</p>
<p><strong>Best for:</strong> learners about to start tertiary study, and current students who need funding.</p>

<h2>Apprenticeships and artisan programmes</h2>
<p>These train you in a trade such as electrical work, plumbing, welding or motor mechanics. You combine technical training with years of supervised work and, at the end, you normally write a trade test to become a qualified artisan. These programmes tend to run longer than a typical learnership.</p>
<p><strong>Best for:</strong> people who want a hands-on trade career.</p>

<h2>Graduate programmes and traineeships</h2>
<p>Some large employers run structured programmes for graduates, often lasting 12 to 24 months, where you rotate through different departments. They are usually more competitive than general internships, and many lead to permanent roles for strong performers.</p>

<h2>How to choose</h2>
<p>Start with what you already have and what you need most:</p>
<ul>
<li><strong>Matric, no experience, and you want to work and study:</strong> look at learnerships.</li>
<li><strong>Qualification finished, but no experience:</strong> look at internships and graduate programmes.</li>
<li><strong>Studying, or about to start, and short of money:</strong> look at bursaries.</li>
<li><strong>Want a trade:</strong> look at apprenticeships and artisan programmes.</li>
</ul>
<p>You can often apply for several at once, and you can move from one to the next: for example, a bursary to finish your degree, then an internship, then a permanent job.</p>

<h2>Questions to ask before you apply</h2>
<ul>
<li>How long is the programme, and what is the monthly stipend or allowance?</li>
<li>For a learnership: what is the qualification called, at what NQF level, and which SETA is it registered with?</li>
<li>Is there any work-back or repayment condition?</li>
<li>What must I submit, and by what date? Late applications are normally not considered.</li>
</ul>

<h2>Protect yourself</h2>
<p>Genuine learnerships, internships and bursaries do not charge you to apply or to be &ldquo;placed&rdquo;. If anyone asks for money, a &ldquo;registration fee&rdquo; or your banking details, walk away. Check that the advert comes from the organisation's own website or official channels, and read our other guides in the <a href="/resources/">Blog</a> on spotting fake listings.</p>

<h2>Where to look</h2>
<p>Browse current <a href="/learnerships/">learnerships</a>, <a href="/internships/">internships</a> and <a href="/bursaries/">bursaries</a> on WorkBase21, and visit the <a href="/jobs/">jobs</a> section when you are ready for permanent work.</p>
""",
    },
    {
        'title': 'How to Write a CV With No Work Experience: A South African Guide',
        'description': ("You do not need a job history to write a strong CV. See what to include, what to leave "
                        "out, and how to show employers your potential."),
        'icon': '📝',
        'order': 21,
        'body': """
<p>Almost every first-time job seeker hits the same wall: the advert asks for experience, and you have never had a job. The good news is that employers hiring for entry-level posts know this. They are looking for evidence that you are reliable, willing to learn and able to do the basics well. A clear, honest CV can show all of that.</p>

<h2>Keep it short and simple</h2>
<ul>
<li><strong>One page is ideal, and two pages is the maximum.</strong> Recruiters often scan a CV for under a minute.</li>
<li><strong>Use a clean layout</strong> with one readable font, clear headings and consistent dates. Heavy graphics and complicated tables can confuse the online systems that some employers use to read CVs.</li>
<li><strong>Save it as a PDF</strong> unless the advert says otherwise, and name the file clearly, for example <em>Thandi-Mokoena-CV.pdf</em>.</li>
</ul>

<h2>What to put on it, in this order</h2>

<h3>1. Contact details</h3>
<p>Your full name, cellphone number, a professional email address (a simple version of your name works best) and your town and province. A photo is not required. Only add your ID number if the employer asks for it, because it is sensitive personal information that criminals use for fraud.</p>

<h3>2. A short personal statement</h3>
<p>Two or three lines at the top saying who you are, what you offer and the kind of work you want. For example: <em>&ldquo;Recent Grade 12 graduate with strong mathematics results, good computer skills and experience organising school events. Looking for an entry-level administration role where I can learn and grow.&rdquo;</em> Change it for each application.</p>

<h3>3. Education</h3>
<p>List your highest qualification first. Give the school or institution, the year you finished (or expect to finish), and the subjects or modules that are relevant to the job. If your matric results are good, or the advert asks for them, include them. Add short courses and online certificates as well.</p>

<h3>4. Skills</h3>
<p>Be specific. Instead of &ldquo;good with computers&rdquo;, write &ldquo;Microsoft Word, Excel (basic formulas) and email&rdquo;. Include the languages you speak and your level in each, and your driver's licence code if you have one. South Africa is multilingual, and speaking several languages is a real advantage in many roles.</p>

<h3>5. Experience that counts</h3>
<p>&ldquo;No experience&rdquo; usually means no <em>paid</em> experience. All of these belong on your CV, described the way you would describe a job (what you did and what you achieved):</p>
<ul>
<li>Volunteering, and community or church projects</li>
<li>School or campus leadership, such as being a prefect or captain of a society or sports team</li>
<li>Holiday jobs, informal work, tutoring or helping in a family business</li>
<li>Projects from your studies, such as a research assignment or a website you built</li>
</ul>
<p>Use short bullet points that start with an action word: <em>organised</em>, <em>helped</em>, <em>trained</em>, <em>managed</em>, <em>supported</em>. Mention results where you honestly can, such as how many people you helped or how often you did it.</p>

<h3>6. Achievements and interests</h3>
<p>Awards, academic prizes, sports colours or leadership recognition. Keep interests brief and relevant.</p>

<h3>7. References</h3>
<p>Two people who can speak about your character or work, such as a teacher, lecturer, coach or community leader (not family). Always ask their permission first. If you are short of space, &ldquo;References available on request&rdquo; is acceptable.</p>

<h2>Tailor it to every advert</h2>
<p>Read the advert carefully and note the skills and duties it lists. Where they are true for you, use the same words in your CV. A general CV sent to fifty employers usually does worse than a tailored one sent to ten.</p>

<h2>Common mistakes to avoid</h2>
<ul>
<li><strong>Lying or exaggerating.</strong> Qualifications and employment are routinely verified, and a lie can cost you a job even after you have started.</li>
<li><strong>Spelling and grammar errors.</strong> Read your CV aloud, and ask someone you trust to check it.</li>
<li><strong>An unprofessional email address</strong> or voicemail greeting.</li>
<li><strong>Unexplained gaps.</strong> If you spent time looking for work, studying or caring for family, say so in one line.</li>
<li><strong>Sending the same CV unchanged</strong> to every employer.</li>
</ul>

<h2>Next steps</h2>
<p>Once your CV is ready, browse current <a href="/jobs/">jobs</a>, <a href="/internships/">internships</a> and <a href="/learnerships/">learnerships</a> that welcome first-time applicants, and read how to avoid fake adverts in our <a href="/resources/">Blog</a>. Remember: you should never have to pay to apply for a job.</p>
""",
    },
    {
        'title': 'How to Prepare for a Government Job Interview in South Africa',
        'description': ("Public sector interviews follow a set format. Learn what to expect, how to prepare "
                        "with the STAR method, and the questions you are likely to face."),
        'icon': '🏛️',
        'order': 22,
        'body': """
<p>Being shortlisted for a public sector post is an achievement, because many people apply for each vacancy. Government interviews are usually more structured than private-sector ones, which means you can prepare for them very effectively.</p>

<h2>What to expect</h2>
<ul>
<li><strong>A panel.</strong> You will normally face several interviewers, often including a human resources representative and the manager of the unit you would join.</li>
<li><strong>The same questions for every candidate.</strong> Panels typically score each answer against set criteria taken from the advert, so a clear, relevant answer matters more than a clever one.</li>
<li><strong>Possibly more than an interview.</strong> Depending on the post, you may also face a written exercise, a presentation or a practical test.</li>
<li><strong>Checks afterwards.</strong> Qualification verification, reference checks and other pre-employment screening are common for public service posts.</li>
</ul>

<h2>Before the interview</h2>

<h3>Re-read the advert and the job requirements</h3>
<p>Your answers should match what the post asks for. List each duty and requirement, and note an example from your life, studies or work that shows you can do it.</p>

<h3>Research the department</h3>
<p>Find the department's website and read about its mandate (what it exists to do), the programmes of the unit you would join, and its recent news. Annual reports are a good source. Being able to explain why you want to work for <em>this</em> department sets you apart from candidates who give a generic answer.</p>

<h3>Know the values of public service</h3>
<p>Public administration in South Africa is guided by the basic values and principles in Section 195 of the Constitution, and by the <strong>Batho Pele</strong> (&ldquo;People First&rdquo;) principles, which focus on serving citizens with courtesy, openness and value for money. Interviewers sometimes ask what these mean in practice, so be ready with a simple explanation and an example.</p>

<h3>Prepare examples with the STAR method</h3>
<p>Many questions ask for a real example. Structure your answer in four parts: <strong>Situation</strong> (the context), <strong>Task</strong> (what you needed to do), <strong>Action</strong> (what <em>you</em> did) and <strong>Result</strong> (what happened). For example, to answer &ldquo;Tell us about a time you worked under pressure&rdquo;, describe the deadline, your role, how you organised your work and the outcome, in about two minutes.</p>

<h2>Questions you may be asked</h2>
<ul>
<li>Tell us about yourself and why you applied for this post.</li>
<li>What do you understand about the work of this department?</li>
<li>Describe a time you worked in a team to achieve a goal.</li>
<li>How do you handle pressure and tight deadlines?</li>
<li>What would you do if you disagreed with your supervisor?</li>
<li>How would you deal with a frustrated member of the public?</li>
<li>What do you understand by Batho Pele?</li>
<li>Where do you see yourself in five years?</li>
<li>Do you have any questions for us?</li>
</ul>
<p>Always have one or two thoughtful questions ready of your own, such as what a typical first month in the post looks like.</p>

<h2>What to bring and how to arrive</h2>
<ul>
<li>Your <strong>ID document</strong> and the <strong>interview invitation</strong></li>
<li>Whatever the invitation asks for, such as original certificates or certified copies. Read it carefully, because requirements differ from one department to another</li>
<li>A spare copy of your CV, and a notepad and pen</li>
</ul>
<p>Plan your route and transport the day before, and arrive early. Dress neatly and professionally, even if the post is not an office job.</p>

<h2>During the interview</h2>
<ul>
<li>Greet the panel politely and wait to be invited to sit.</li>
<li>Listen to the whole question. It is fine to ask for it to be repeated, or to take a moment to think.</li>
<li>Answer the question you were asked, with specific examples, and keep to the point.</li>
<li>Be honest. If you do not know something, say so and explain how you would find out.</li>
<li>Thank the panel at the end.</li>
</ul>

<h2>After the interview</h2>
<p>Public sector processes can take weeks or months, so keep applying elsewhere while you wait. If you are unsuccessful, you can politely ask whether feedback is available, and use it to improve next time.</p>

<h2>Beware of scams</h2>
<p>Genuine interview invitations come from official government email addresses or phone numbers. Nobody can sell you a government job, and nobody should ask you for money to &ldquo;secure&rdquo; an interview or an appointment. If an invitation looks suspicious, check it by calling the department's human resources office on the number listed on its <em>official website</em>, not the number in the message.</p>

<p>Looking for your next application? Browse current <a href="/jobs/public/">public sector jobs</a>, <a href="/internships/">internships</a> and <a href="/learnerships/">learnerships</a>, or read more in our <a href="/resources/">Blog</a>.</p>
""",
    },
]


class Command(BaseCommand):
    help = "Add hidden draft articles for you to review, personalise and publish."

    def handle(self, *args, **options):
        created, skipped = [], []
        for d in DRAFTS:
            if TrendingTopic.objects.filter(title__iexact=d['title']).exists():
                skipped.append(d['title'])
                continue
            TrendingTopic.objects.create(
                title=d['title'], description=d['description'], icon=d['icon'],
                order=d['order'], body=d['body'].strip(), is_active=False,
            )
            created.append(d['title'])

        self.stdout.write(self.style.SUCCESS(
            f"{len(created)} draft article(s) created (hidden), {len(skipped)} skipped (already exist)."
        ))
        for t in created:
            self.stdout.write(f"  + {t}")
        for t in skipped:
            self.stdout.write(f"  = {t}  (left untouched)")
        if created:
            self.stdout.write(
                "\nNext: Admin -> Trending Topics & Articles. Open each draft, read it, make it yours, "
                "then tick 'Is active' to publish."
            )
