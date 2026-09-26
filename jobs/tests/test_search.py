"""Search and the advanced filters return exactly the right listings;
pagination keeps filters; Market Insights counts correctly."""
from django.urls import reverse

from jobs.models import Job
from .helpers import WBTestCase, make_company, make_job, skill


def titles(response):
    return sorted(j.title for j in response.context['page_obj'].object_list)


class FilterTest(WBTestCase):
    def setUp(self):
        super().setUp()
        py = skill('Python')
        make_job('Graduate Dev', qualification_level='degree', experience_level='entry',
                 work_mode='remote', industry='it', salary_min=20000, skills=[py])
        make_job('Senior Accountant', qualification_level='honours', experience_level='5_plus',
                 work_mode='onsite', industry='finance', salary_min=45000)
        make_job('Shop Assistant', qualification_level='matric', experience_level='entry',
                 work_mode='onsite', industry='retail')
        self.url = reverse('jobs_private')

    def get(self, **params):
        return self.client.get(self.url, params)

    def test_each_filter_returns_the_right_listings(self):
        cases = [
            ({'qualification': 'degree'}, ['Graduate Dev']),
            ({'experience': 'entry'}, ['Graduate Dev', 'Shop Assistant']),
            ({'work_mode': 'onsite'}, ['Senior Accountant', 'Shop Assistant']),
            ({'industry': 'finance'}, ['Senior Accountant']),
            ({'skill': 'python'}, ['Graduate Dev']),
            ({'salary_min': '30000'}, ['Senior Accountant']),
            ({'experience': 'entry', 'work_mode': 'onsite'}, ['Shop Assistant']),
            ({'qualification': 'doctorate'}, []),
            ({}, ['Graduate Dev', 'Senior Accountant', 'Shop Assistant']),
        ]
        for params, expected in cases:
            with self.subTest(filters=params):
                self.assertEqual(titles(self.get(**params)), expected)

    def test_non_number_salary_is_ignored(self):
        self.assertEqual(len(titles(self.get(salary_min='lots'))), 3)

    def test_filters_stay_selected_after_applying(self):
        self.assertPageHas(self.get(industry='finance'), 'value="finance" selected')

    def test_pagination_links_keep_filters(self):
        for i in range(12):
            make_job(f'Retail Job {i:02d}', industry='retail')
        r = self.get(industry='retail')
        self.assertPageHas(r, '?industry=retail&page=2')

    def test_filters_work_on_internships_page_too(self):
        make_job('Remote Intern', type=Job.INTERNSHIP, work_mode='remote')
        make_job('Office Intern', type=Job.INTERNSHIP, work_mode='onsite')
        r = self.client.get(reverse('internships'), {'work_mode': 'remote'})
        self.assertEqual(titles(r), ['Remote Intern'])


class SearchTest(WBTestCase):
    def setUp(self):
        super().setUp()
        make_job('Python Developer', company=make_company('Acme Tech'), location='Polokwane')
        make_job('Nurse', company=make_company('City Hospital'), location='Durban')
        make_job('Hidden Python Job', is_active=False)

    def search(self, q):
        return self.client.get(reverse('search'), {'q': q})

    def test_matches_title_company_and_location(self):
        self.assertEqual(titles(self.search('python')), ['Python Developer'])
        self.assertEqual(titles(self.search('hospital')), ['Nurse'])
        self.assertEqual(titles(self.search('polokwane')), ['Python Developer'])

    def test_hidden_jobs_never_in_results(self):
        self.assertNotIn('Hidden Python Job', titles(self.search('python')))

    def test_empty_search_shows_nothing(self):
        self.assertEqual(titles(self.search('')), [])

    def test_search_plus_filter(self):
        Job.objects.filter(title='Python Developer').update(work_mode='remote')
        r = self.client.get(reverse('search'), {'q': 'python', 'work_mode': 'onsite'})
        self.assertEqual(titles(r), [])


class MarketInsightsTest(WBTestCase):
    def test_counts_active_listings_only(self):
        py = skill('Python')
        make_job('A', industry='it', skills=[py])
        make_job('B', industry='it', skills=[py])
        make_job('C', industry='finance')
        make_job('Hidden', industry='it', is_active=False, skills=[py])
        r = self.client.get(reverse('market_insights'))
        self.assertEqual(r.context['total'], 3)
        industries = {row['label']: row['count'] for row in r.context['by_industry']}
        self.assertEqual(industries['IT & Technology'], 2)
        skills = {s.name: s.count for s in r.context['top_skills']}
        self.assertEqual(skills['Python'], 2)

    def test_page_works_with_no_listings(self):
        r = self.client.get(reverse('market_insights'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total'], 0)
