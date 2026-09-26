"""Contact form: messages reach SITE_EMAIL with the visitor as Reply-To,
the pop-up shows the right result, the rate limit works, and a failed
send is reported honestly (and keeps what the visitor typed)."""
import smtplib
from unittest import mock

from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from .helpers import WBTestCase

GOOD = {'name': 'Lerato', 'email': 'lerato@example.com', 'subject': 'Bursaries', 'message': 'Are 2027 bursaries open?'}


class ContactFormTest(WBTestCase):
    url = reverse('contact')

    def test_message_delivered_to_site_inbox(self):
        r = self.client.post(self.url, GOOD)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, [settings.SITE_EMAIL])
        self.assertEqual(m.reply_to, ['lerato@example.com'])
        self.assertEqual(m.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(m.subject, '[WorkBase21 Contact] Bursaries')
        self.assertIn('Are 2027 bursaries open?', m.body)
        self.assertIn('Lerato', m.body)

    @override_settings(SITE_EMAIL='someone.else@example.com')
    def test_goes_to_whatever_site_email_is_set(self):
        self.client.post(self.url, GOOD)
        self.assertEqual(mail.outbox[0].to, ['someone.else@example.com'])

    def test_success_popup_shown_not_green_bar(self):
        r = self.client.post(self.url, GOOD, follow=True)
        self.assertPageHas(r, 'id="contact-result"')
        self.assertPageHas(r, 'Message sent')
        self.assertPageHas(r, 'Thanks, Lerato!')
        # The green bar may only appear inside the no-JavaScript fallback.
        visible_part = r.content.decode().split('<noscript>')[0]
        self.assertNotIn('<div class="alert alert-success">', visible_part,
                         "the green bar should not show as well as the pop-up")

    def test_missing_fields_flagged_and_nothing_sent(self):
        r = self.client.post(self.url, {'name': '', 'email': 'not-an-email', 'subject': 'Hi', 'message': ''})
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(r.content.decode().count('has-error'), 3)
        self.assertPageHas(r, 'form-error-summary')
        self.assertPageLacks(r, 'id="contact-result"')

    def test_sixth_message_in_an_hour_is_refused(self):
        for _ in range(5):
            self.client.post(self.url, GOOD)
        r = self.client.post(self.url, GOOD, follow=True)
        self.assertEqual(len(mail.outbox), 5)
        self.assertPageHas(r, 'Message not sent')
        self.assertPageHas(r, 'several messages')

    def test_gmail_failure_reported_and_message_kept(self):
        with mock.patch('django.core.mail.EmailMessage.send', side_effect=smtplib.SMTPException('down')):
            r = self.client.post(self.url, GOOD)
        self.assertEqual(r.status_code, 200)
        self.assertPageHas(r, 'Message not sent')
        self.assertPageHas(r, 'Are 2027 bursaries open?')
        self.assertPageHas(r, f'mailto:{settings.SITE_EMAIL}')
        self.assertPageLacks(r, 'Thanks, Lerato!')
