"""Profile editing (typeable skills), eligibility checker, recommendations,
career explorer + skills graph suggestions, and the starter career data."""
import io
from datetime import timedelta

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from accounts import graph
from accounts.models import CareerPath, Qualification, UserProfile
from jobs import matching
from jobs.models import Job, Skill
from jobs.tests.helpers import WBTestCase, make_job, make_seeker, skill


def edit_form(**overrides):
    data = {'location': '', 'qualification_level': '', 'experience_level': '', 'career_goal': '',
            'bio': '', 'skills_text': '', 'qualifications_text': ''}
    data.update(overrides)
    return data


class ProfileEditTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_seeker('grad')
        self.login(self.user)
        skill('Python')

    def profile(self):
        return UserProfile.objects.get(user=self.user)

    def test_typed_skills_saved_cleanly(self):
        r = self.client.post(reverse('profile_edit'),
                             edit_form(skills_text='python, Excel ,  Customer   Service, excel, C++, C#',
                                       qualifications_text='BSc Statistics, Matric'))
        self.assertRedirects(r, reverse('profile'))
        names = sorted(self.profile().skills.values_list('name', flat=True))
        self.assertEqual(names, sorted(['Python', 'Excel', 'Customer Service', 'C++', 'C#']))
        self.assertEqual(Skill.objects.filter(name__iexact='python').count(), 1, "existing skill reused")
        self.assertEqual(len(set(Skill.objects.filter(name__in=['C++', 'C#']).values_list('slug', flat=True))), 2)
        self.assertEqual(sorted(self.profile().qualifications.values_list('name', flat=True)), ['BSc Statistics', 'Matric'])

    def test_saved_skills_prefilled_and_can_be_cleared(self):
        self.client.post(reverse('profile_edit'), edit_form(skills_text='Python, SQL'))
        self.assertPageHas(self.client.get(reverse('profile_edit')), 'Python, SQL')
        self.client.post(reverse('profile_edit'), edit_form(skills_text=''))
        self.assertEqual(self.profile().skills.count(), 0)

    def test_skill_filter_only_lists_skills_used_on_jobs(self):
        self.client.post(reverse('profile_edit'), edit_form(skills_text='Underwater Basket Weaving'))
        make_job('Dev', skills=[skill('Python')])
        r = self.client.get(reverse('jobs_private'))
        self.assertPageHas(r, 'value="python"')
        self.assertPageLacks(r, 'Underwater Basket Weaving')


class EligibilityTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job('Analyst', qualification_level='degree', experience_level='3_5',
                            location='Johannesburg, Gauteng', work_mode='onsite',
                            skills=[skill('Python'), skill('Excel'), skill('SQL')])

    def test_needs_login(self):
        r = self.client.get(reverse('job_eligibility', args=[self.job.pk]))
        self.assertIn(reverse('login'), r['Location'])

    def test_strong_match(self):
        u = make_seeker(qualification_level='honours', experience_level='5_plus', location='Johannesburg',
                        skills=[skill('Python'), skill('Excel'), skill('SQL')])
        result = matching.check_eligibility(UserProfile.objects.get(user=u), self.job)
        self.assertEqual((result['matched_count'], result['checked_count'], result['unmet']), (4, 4, []))

    def test_gaps_named_specifically(self):
        u = make_seeker(qualification_level='matric', experience_level='entry', location='Cape Town',
                        skills=[skill('Python')])
        result = matching.check_eligibility(UserProfile.objects.get(user=u), self.job)
        self.assertEqual(result['matched_count'], 1)
        gaps = ' '.join(result['unmet'])
        self.assertIn('Excel', gaps)
        self.assertIn('Cape Town', gaps)

    def test_blank_fields_are_unclear_not_failures(self):
        u = make_seeker()
        result = matching.check_eligibility(UserProfile.objects.get(user=u), make_job('Blank job'))
        self.assertEqual(result['unmet'], [])
        self.assertGreater(len(result['unclear']), 0)

    def test_page_shows_no_hiring_prediction_disclaimer(self):
        self.login(make_seeker())
        self.assertPageHas(self.client.get(reverse('job_eligibility', args=[self.job.pk])),
                           'prediction of whether')


class RecommendationsTest(WBTestCase):
    def test_empty_profile_gets_prompt(self):
        self.login(make_seeker())
        self.assertPageHas(self.client.get(reverse('recommended_jobs')), 'Complete your profile')

    def test_matching_jobs_listed_with_reason_hidden_excluded(self):
        make_job('Python Dev', skills=[skill('Python')])
        make_job('Hidden Python Dev', skills=[skill('Python')], is_active=False)
        self.login(make_seeker(skills=[skill('Python')]))
        r = self.client.get(reverse('recommended_jobs'))
        self.assertPageHas(r, 'Python Dev')
        self.assertPageLacks(r, 'Hidden Python Dev')
        self.assertPageHas(r, 'skills this role lists')


class CareerGraphTest(WBTestCase):
    def setUp(self):
        super().setUp()
        call_command('seed_career_graph', stdout=io.StringIO())

    def test_starter_command_is_safe_to_rerun_and_never_overwrites(self):
        CareerPath.objects.filter(title='Data Analyst').update(description='MY OWN TEXT')
        before = (CareerPath.objects.count(), Skill.objects.count(), Qualification.objects.count())
        call_command('seed_career_graph', stdout=io.StringIO())
        self.assertEqual((CareerPath.objects.count(), Skill.objects.count(), Qualification.objects.count()), before)
        self.assertEqual(CareerPath.objects.get(title='Data Analyst').description, 'MY OWN TEXT')

    def test_career_pages_and_path_map(self):
        self.assertEqual(self.client.get(reverse('careers')).status_code, 200)
        cy = CareerPath.objects.get(title='Cybersecurity Analyst')
        r = self.client.get(cy.get_absolute_url())
        self.assertPageHas(r, 'Often comes from')
        self.assertPageHas(r, 'IT Support Technician')

    def test_related_jobs_by_title_or_skill_open_only(self):
        today = timezone.localdate()
        by_title = make_job('Junior Software Developer')
        by_skill = make_job('Office Clerk', skills=[skill('Git')])
        expired = make_job('Software Developer Old', deadline=today - timedelta(days=1))
        hidden = make_job('Software Developer Hidden', is_active=False)
        related = list(graph.related_jobs_for_career(CareerPath.objects.get(title='Software Developer')))
        self.assertIn(by_title, related)
        self.assertIn(by_skill, related)
        self.assertNotIn(expired, related)
        self.assertNotIn(hidden, related)

    def test_suggestions_with_reasons_and_one_tap_add(self):
        u = make_seeker(career_goal='data scientist', skills=[skill('Python')])
        profile = UserProfile.objects.get(user=u)
        profile.qualifications.set([Qualification.objects.get(name='BSc Statistics')])
        careers = graph.suggest_careers(profile)
        self.assertEqual(careers[0]['career'].title, 'Data Scientist')
        skills = {row['skill'].name: row for row in graph.suggest_skills(profile)}
        self.assertIn('covered by your BSc Statistics', skills['Statistics']['reasons'])
        self.assertNotIn('Python', skills)
        self.login(u)
        stat = Skill.objects.get(name='Statistics')
        r = self.client.post(reverse('profile_add_skill', args=[stat.pk]), {'next': 'https://evil.example.com/'})
        self.assertEqual(r['Location'], reverse('profile'), "must not redirect to other websites")
        self.assertTrue(profile.skills.filter(pk=stat.pk).exists())
        self.assertEqual(self.client.get(reverse('profile_add_skill', args=[stat.pk])).status_code, 405)

    def test_skill_gap_on_career_page(self):
        u = make_seeker(skills=[skill('Python'), skill('SQL')])
        self.login(u)
        r = self.client.get(CareerPath.objects.get(title='Data Scientist').get_absolute_url())
        self.assertPageHas(r, 'skill coverage')
        self.assertPageHas(r, 'You already have')
        self.assertPageHas(r, 'Worth building')
