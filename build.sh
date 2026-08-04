#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# NOTE: migrations intentionally do NOT run here. This build step runs
# before Render's persistent disk is mounted, so a `migrate` here would
# apply to a throwaway database and silently miss the real one. Migrations
# now run in the Procfile's start command instead, at runtime, after the
# disk is available.
