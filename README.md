# WorkBase21

A premium South African job portal built with Django 5, SQLite, pure CSS
(no Bootstrap/Tailwind) and vanilla JavaScript. Lists Jobs, Internships,
Learnerships, and Bursaries.

---

## 1. Requirements

- Python 3.10+
- pip

Check your Python version:
```bash
python3 --version
```

---

## 2. Local Setup (step by step)

**Step 1 — Unzip the project and open a terminal inside it.**

**Step 2 — Create and activate a virtual environment.**
```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**Step 3 — Install the dependencies.**
```bash
pip install -r requirements.txt
```

**Step 4 — Create the database tables.**
```bash
python manage.py migrate
```

**Step 5 — Create an admin (superuser) account.**
```bash
python manage.py createsuperuser
```
Follow the prompts (username, email, password). You'll use this to log
into `/admin/` and add companies and jobs.

**Step 6 — (Optional) Add sample listings so the site isn't empty.**
```bash
python manage.py seed_demo_data
```
This creates 5 demo companies and 10 sample listings across all five
categories. You can delete them later from the admin.

**Step 7 — Run the development server.**
```bash
python manage.py runserver
```

**Step 8 — Open the site.**
- Website: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

---

## 3. Adding Real Jobs

1. Go to `/admin/` and log in.
2. Under **Companies**, click **Add** — enter the name, upload a logo
   (square images work best), and add the website URL.
3. Under **Jobs**, click **Add**:
   - Pick the **Company**
   - Choose the **Type**: Job / Internship / Learnership / Bursary
   - Write the **Description** using the rich text editor (headings,
     bullet points, links all work)
   - Optionally fill in **Description Part 2** — this appears *below*
     the advertisement block on the job detail page
   - Fill in **Location**, **Salary**, **Deadline**, and
     **Application Link** (this is the external URL the "Apply Now"
     button opens in a new tab)
   - Untick **Is active** any time you want to hide a listing without
     deleting it

---

## 4. Project Structure

```
workbase21/
├── manage.py
├── requirements.txt
├── Procfile              # for Render deployment
├── build.sh               # for Render deployment
├── workbase21/            # project settings, root urls.py
├── jobs/                  # the app: models, views, admin, urls
│   └── management/commands/seed_demo_data.py
├── templates/
│   ├── base.html
│   ├── welcome.html
│   ├── jobs.html / internships.html / learnerships.html /
│   │   bursary.html
│   ├── job_detail.html
│   ├── search.html
│   ├── about.html / contact.html / privacy.html / terms.html
│   ├── 404.html
│   └── partials/          # reusable job card, grid, pagination
└── static/
    ├── css/style.css       # design tokens, components
    ├── css/responsive.css  # media queries, mobile menu
    ├── js/main.js          # vanilla JS behaviour
    └── images/logo.png     # placeholder logo — replace with your own
```

---

## 5. Deploying to Render (paid instance + persistent disk)

The database is SQLite stored on a Render **persistent disk** mounted
at `/var/data` (see `DATABASES` in settings.py). Persistent disks need a
paid instance type.

**Step 1 — Push this project to a GitHub repository.** Check `git status`
first: `venv/`, `db.sqlite3` and `media/` must NOT be listed (they're in
`.gitignore`).

**Step 2 — On Render, click New → Web Service** and connect the repo.
Add a **Disk** with mount path `/var/data`.

**Step 3 — Set the following:**
- **Build Command:** `./build.sh`
- **Start Command:** `python manage.py migrate --no-input && gunicorn workbase21.wsgi --log-file -`

> ⚠️ Render ignores the `Procfile` — the Start Command in the dashboard
> is what actually runs. Migrations MUST run in the Start Command, not
> in build.sh: the disk isn't mounted during the build, so a migrate
> there would update a throwaway database and miss the real one.

**Step 4 — Add environment variables** under the Render dashboard:
| Key | Value |
|---|---|
| `DJANGO_SECRET_KEY` | (generate a long random string) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | your domains, comma-separated |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | e.g. `https://workbase21.co.za,https://www.workbase21.co.za` |
| `RENDER_EXTERNAL_HOSTNAME` | your-app-name.onrender.com |
| `SITE_DOMAIN` | `workbase21.co.za` |
| `EMAIL_HOST_USER` | the Gmail address the site sends from |
| `EMAIL_HOST_PASSWORD` | a Google **App password** (needs 2-Step Verification) |

**Step 5 — Deploy.** Render runs `build.sh` (installs dependencies,
collects static files), then the Start Command (runs migrations on the
disk database, starts gunicorn).

**Step 6 — Create your production superuser** (first deploy only). In
the Render Shell tab:
```bash
python manage.py createsuperuser
```

**Optional:** `python manage.py seed_career_graph` adds starter career
paths/skills (never overwrites existing data). Don't worry about
`seed_demo_data` on production — it refuses to run if any jobs exist.

**Before a deploy that includes new migrations**, back up the database
from the Render Shell:
```bash
cp /var/data/db.sqlite3 /var/data/db-backup-$(date +%Y%m%d-%H%M).sqlite3
```

---

## 4b. The Text Editor (TinyMCE)

Job descriptions and blog articles are written in the admin with
**TinyMCE 7.9.3**, bundled in `static/vendor/tinymce/` (GPL-2.0-or-later,
free; see `VERSION.txt` there). It replaced django-ckeditor (CKEditor 4),
which is unsupported and has known security issues.

- Job descriptions: headings, bold/italic/underline, lists, links, view source.
- Articles: the same, plus quotes and pictures (upload + align left/centre/right).
- Picture uploads (`jobs/editor.py`): admins only; real JPG/PNG/GIF/WebP only
  (no SVG); max 5 MB; saved in `media/uploads/`.
- Existing content is kept exactly as saved. The fields are plain text in the
  database; only the admin screen changed.

**Updating TinyMCE later:** check https://github.com/tinymce/tinymce/security
now and then. To update, download the new version from npm and replace the
files in `static/vendor/tinymce/` (keep the same folder layout), update
`VERSION.txt`, then run `python manage.py test` and `python manage.py phone_check`.

---

## 5a. Backups & Restoring

Everything that isn't code (listings, articles, companies, reviews, user
accounts, profiles, saved jobs, alerts) lives in `/var/data/db.sqlite3`;
uploaded files live in `/var/data/media`. Neither is on GitHub.

**Three layers of protection:**
1. **Render daily snapshots** — Render copies the whole disk every day and
   keeps 7 days (Render → Disk → Snapshots). Nothing to do.
2. **Weekly emailed database backup** — sent automatically to `SITE_EMAIL`
   (`jobs/backup.py`, triggered by normal site traffic). Needs the Gmail
   settings. Uploaded files aren't included (too big to email).
3. **Downloads** — Django admin → **Backups**: *Download database* (small)
   or *Download everything* (database + uploaded files, one zip). Keep a
   copy on your laptop / Google Drive at least monthly.

**Something broke in the last 7 days?** Render → Disk → Snapshots → pick a
day from BEFORE the problem → Restore. Everything after that moment
(including new sign-ups) is lost, so pick the latest good one.

**Need an older copy, or a copy from email/your laptop?** Django admin →
Backups → *Restore database from a backup file* (superusers only): choose
the `.sqlite3.gz` (from the email) or the `.zip`, type `RESTORE`, submit.
A safety copy of the current database is saved first in
`/var/data/backups/` (the last 3 are kept), and migrations run
automatically, so backups from older versions of the site work too.

**Privacy:** backups contain job seekers' personal information. Keep them
private and delete copies older than about 3 months.

`gunicorn.conf.py` (loaded automatically) lets the server handle several
requests at once, so a big download neither gets cut off nor freezes the
site for other visitors.

---

## 5c. Automated Tests — run before every push

**Everyday check (about 30 seconds):**
```
python manage.py test
```
- `OK` at the end → safe to push.
- `FAILED` → don't push yet. Each failure says in one sentence what went
  wrong (e.g. *"Expected to see 'Message sent' on /contact/..."*).

Covers every page, sign-up/login (and how errors are shown), password
reset/change, download & delete my data, search and filters, hidden and
expired listings, Contact form + pop-up, saved jobs/tracker, job alerts,
eligibility/recommendations/careers, admin tools, backups & restore, the
weekly backup email, and privacy (job seekers can't see each other's data).

**Phone checks (a few minutes) — real browser at phone, tablet and laptop
sizes.** Run before layout/design changes:
```
pip install -r requirements-dev.txt      (one time)
playwright install chromium              (optional: downloads a browser, ~150 MB)
python manage.py phone_check
```
The checks use Playwright's own browser if it's installed; otherwise the
Google Chrome or Microsoft Edge already on your computer (Windows always has
Edge). So if `playwright install chromium` can't download (blocked network,
firewall, VPN), you can skip it. The first line of the output says which
browser was used.

Tests use a temporary practice database (`test_db.sqlite3`, deleted
automatically) — never your real data — and never send real emails.
Tests live in `jobs/tests/` and `accounts/tests/`.

---

## 5b. Connecting Your Custom Domain (workbase21.co.za)

Congrats on the domain! Here's how to point it at your Render app.

**Step 1 — In Render:** open your Web Service → **Settings** →
**Custom Domains** → **Add Custom Domain**. Add both:
- `workbase21.co.za`
- `www.workbase21.co.za`

Render will show you the DNS records it needs — usually:
- An **A record** for the root domain (`workbase21.co.za`) pointing to
  Render's IP address
- A **CNAME record** for `www` pointing to your `*.onrender.com`
  address

**Step 2 — At your domain registrar** (wherever you bought
workbase21.co.za — e.g. Domains.co.za, Afrihost, or similar), open the
DNS management page for the domain and add exactly the records Render
showed you in Step 1.

**Step 3 — Wait for DNS to propagate.** This can take anywhere from a
few minutes to a few hours. Render will show a green checkmark next to
each domain once it verifies successfully, and will auto-issue a free
SSL certificate for HTTPS.

**Step 4 — Set these environment variables in Render** (Settings →
Environment):
| Key | Value |
|---|---|
| `DJANGO_ALLOWED_HOSTS` | `workbase21.co.za,www.workbase21.co.za,your-app-name.onrender.com` |
| `SITE_DOMAIN` | `workbase21.co.za` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://workbase21.co.za,https://www.workbase21.co.za` |

These already default to `workbase21.co.za` in `settings.py`, so this
step is mainly a safety net — set them explicitly in Render so nothing
breaks if the code defaults ever change.

**Step 5 — Set `workbase21.co.za` (no www) as primary, redirect `www`
to it.** In Render's Custom Domains list, mark `workbase21.co.za` as
the primary domain — Render will then automatically 301-redirect
`www.workbase21.co.za` to it. This keeps everything consistent with
`SITE_DOMAIN` in `settings.py`, which is already set to
`workbase21.co.za` (no www) as the canonical URL used in SEO meta
tags, Open Graph tags, and Twitter Cards.

---

## 6. Customising the Design

- Colours, spacing, and radii are all CSS variables at the top of
  `static/css/style.css` under `:root` — change them there and the
  whole site updates.
- Replace `static/images/logo.png` with your real logo (square, at
  least 200×200px works best).
- Fonts are loaded from Google Fonts in `style.css` (Plus Jakarta Sans
  for headings, Inter for body text) — swap the `@import` line to use
  different fonts.

---

## 7. What's Left to Wire Up Later

This was built to be easy to extend, as requested:
- User accounts (job seeker + employer login)
- Employer dashboards for posting/managing their own jobs
- "Apply" tracking / saved jobs
- Email alerts for new matching listings
- Replace the AdSense placeholder on the job detail page with a real
  AdSense unit once your account is approved

---

## 8. Changelog — Latest Update

- **Apply by email:** Jobs now support `application_email` in addition
  to `application_link`. On the job detail page it renders as a
  clickable `mailto:` link plus a "Copy Email" button. You can fill in
  either field (or both) per job in the admin.
- **5 description blocks:** The single description field is now five
  (`description` through `description5`), each shown in its own admin
  section (collapsed by default). An advertisement placeholder is
  automatically inserted between each non-empty block on the job
  detail page — 4 ad slots total instead of 1.
- **Job images:** Jobs now have an optional `image` field. It shows as
  a banner on the job card (object-fit: cover, so any image size looks
  clean) and as a larger banner at the top of the job detail page.
- **Share links:** The job detail page ends with Facebook, X
  (Twitter), Pinterest and LinkedIn share buttons that link to the
  specific job's URL.
- **Related opportunities:** The job detail page shows up to 4 related
  listings of the same type underneath the main content.
- **Public/Private sector split:** Clicking "Jobs" in the nav now
  opens a choice screen (Public Sector vs Private Sector) before
  showing listings. This only applies to the "Jobs" category — set
  each job's **Sector** field in the admin.
- **Z83 form download:** For Public Sector jobs, upload a PDF to the
  job's **Z83 Form** field in the admin and a "Download Z83 Form"
  button appears on that job's detail page automatically.
- **Homepage reviews:** A new `Review` model (name, role/organisation,
  star rating, message) — manage entries from the admin under
  **Reviews**. Untick "Is published" to hide one without deleting it.
- **What's Trending in the Job Market:** A new `TrendingTopic` model
  (title, description, stat, emoji icon, order) — fully editable from
  the admin under **Trending Topics**, no code changes needed.

> **If you're upgrading from an earlier copy of this project:** the
> `Job` model changed significantly (new fields, renamed description
> fields). Easiest path is to delete `db.sqlite3` and re-run
> `python manage.py migrate` then re-add your listings (or re-run
> `seed_demo_data` for fresh samples). If you already have real
> production data you want to keep, let me know and I can write a
> data migration instead of a fresh reset.

