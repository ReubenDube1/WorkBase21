"""Diagnose why emails (password reset, Contact form) aren't arriving.

    python manage.py check_email you@example.com

Checks, in order, and stops at the first problem:
  1. Gmail settings (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD) are set
  2. Whether an account exists for that email (reset emails only go to
     active accounts that have that exact email address)
  3. The server can reach Gmail (Render FREE instances block email ports)
  4. Gmail accepts the login (App password correct)
  5. Actually sends a test email to that address
Never prints the password.
"""
import smtplib
import socket

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

OK, BAD, INFO = "✅", "❌", "ℹ️ "


class Command(BaseCommand):
    help = "Check the email setup and send a test email."

    def add_arguments(self, parser):
        parser.add_argument('email', nargs='?', help='Address to check and send a test email to.')

    def say(self, icon, text):
        self.stdout.write(f"{icon} {text}")

    def handle(self, *args, **options):
        to = (options.get('email') or settings.EMAIL_HOST_USER or '').strip()

        # 1. Settings --------------------------------------------------------
        user_set = bool(settings.EMAIL_HOST_USER)
        pw = settings.EMAIL_HOST_PASSWORD
        if not user_set or not pw:
            missing = [n for n, v in (('EMAIL_HOST_USER', user_set), ('EMAIL_HOST_PASSWORD', pw)) if not v]
            self.say(BAD, f"Not set on this server: {', '.join(missing)}.")
            self.say(INFO, "So emails are only PRINTED in the Render logs, never sent. Add them under "
                           "Render → your service → Environment, save, and let it redeploy.")
            return
        self.say(OK, f"Gmail settings found: sending as {settings.EMAIL_HOST_USER}.")
        if len(pw) != 16:
            self.say(BAD, f"EMAIL_HOST_PASSWORD is {len(pw)} characters (spaces ignored). A Google App "
                          "password is exactly 16 letters. It looks like the normal Gmail password — "
                          "that won't work. Create an App password at myaccount.google.com/apppasswords.")
            return
        self.say(OK, "EMAIL_HOST_PASSWORD looks like an App password (16 characters).")

        # 2. Account lookup --------------------------------------------------
        if not to:
            self.say(BAD, "Give an email address, e.g.:  python manage.py check_email you@gmail.com")
            return
        users = get_user_model().objects.filter(email__iexact=to)
        if not users.exists():
            self.say(INFO, f"No account uses {to}. Password reset emails are ONLY sent to an address "
                           "that belongs to an account — test reset with the email you registered with "
                           "(see Users in the admin).")
        else:
            for u in users:
                problems = []
                if not u.is_active:
                    problems.append("account is inactive")
                if not u.has_usable_password():
                    problems.append("account has no usable password")
                if problems:
                    self.say(BAD, f"Account '{u.username}' has {to}, but reset won't email it: {', '.join(problems)}.")
                else:
                    self.say(OK, f"Account '{u.username}' uses {to} — password reset can email it.")

        # 3. Network ---------------------------------------------------------
        try:
            socket.create_connection((settings.EMAIL_HOST, settings.EMAIL_PORT), timeout=10).close()
        except OSError as e:
            self.say(BAD, f"This server can't reach {settings.EMAIL_HOST}:{settings.EMAIL_PORT} ({e}).")
            self.say(INFO, "Render blocks email ports (25, 465, 587) on FREE instances. Check Render → "
                           "your service → Settings → Instance Type. Paid instances aren't blocked.")
            return
        self.say(OK, f"Server can reach {settings.EMAIL_HOST}:{settings.EMAIL_PORT}.")

        # 4. Login -----------------------------------------------------------
        try:
            conn = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=15)
            conn.starttls()
            conn.login(settings.EMAIL_HOST_USER, pw)
            conn.quit()
        except smtplib.SMTPAuthenticationError:
            self.say(BAD, "Gmail rejected the login. Usual causes: wrong App password, it was revoked, "
                          "2-Step Verification was turned off, or EMAIL_HOST_USER isn't the Gmail "
                          "account that created the App password.")
            return
        except (smtplib.SMTPException, OSError) as e:
            self.say(BAD, f"Connecting to Gmail failed: {e}")
            return
        self.say(OK, "Gmail accepted the login.")

        # 5. Send ------------------------------------------------------------
        try:
            send_mail(
                "WorkBase21 test email",
                "This is a test from `python manage.py check_email`. If you can read this, "
                "email sending works.",
                settings.DEFAULT_FROM_EMAIL, [to],
            )
        except (smtplib.SMTPException, OSError) as e:
            self.say(BAD, f"Sending failed: {e}")
            return
        self.say(OK, f"Test email sent to {to}. Check the inbox AND the Spam folder.")
