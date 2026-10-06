# Deploying PractiCore to Vercel

Vercel's Python runtime has **zero-configuration Flask support**, and this repo
already satisfies every requirement — there is no `vercel.json` to write.

## Why it works out of the box

| Vercel expects | This repo |
|---|---|
| A Flask instance named `app` at a supported entrypoint (`app.py`, `index.py`, `main.py`, `wsgi.py`, …) | root `app.py` → `app = create_app()` ✓ |
| Dependencies in `requirements.txt` | runtime-only deps (~150 MB installed) ✓ |
| Python version | `.python-version` → 3.12 ✓ |
| Framework detection | `Flask>=3.0` in `requirements.txt` ✓ |

The training-only stack (scikit-learn/numpy/joblib ≈ 170 MB) lives in
`requirements-train.txt` and is **deliberately not deployed** — that split is
what keeps the function bundle well under Vercel's 500 MB Python limit. The app
falls back to the weighted content-based scorer without it.

## Steps

1. Push the repository to GitHub (already done: `adeeyn/PractiCore`).
2. In Vercel: **Add New → Project → Import `adeeyn/PractiCore`**. Vercel
   auto-detects Flask — leave the Build Command and Output settings untouched.
3. Under **Settings → Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | your Supabase **Transaction pooler** URI: `postgresql://postgres.<ref>:<password>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres` (no `pgbouncer=true` — psycopg2 rejects that parameter) |
   | `SECRET_KEY` | a long random string (session cookies; the code falls back to an insecure default if unset) |

4. **Region:** Supabase is in `ap-southeast-1` (Singapore), so set the
   serverless region to **Singapore (`sin1`)** in
   **Settings → Functions** to keep database round-trips fast.
5. Deploy. The database is already migrated and seeded — no build-time
   migration step is needed.

## Logins after deploying

- Admin: `admin@practicore.test` / `admin123` — **change this password**.
- Demo employers: see `flask --app app seed-employers` output
  (all use `PractiCore123`).

## Known limitation: avatar & company-logo uploads

Those two features write files under `practicore/static/uploads/`, but a Vercel
function's filesystem is **read-only** (uploads will fail in production until
migrated to Supabase Storage — tracked as a follow-up). Everything else works:

- **Resumes are stored as bytes in Postgres** (`student_resumes.file_data`),
  so resume upload/view is unaffected.
- Static assets (CSS/JS/images) ship with the deployment and are served fine.

## Local development

`.env` (gitignored) holds `DATABASE_URL` and is loaded by `load_dotenv()` in
`create_app()`. Real environment variables always override the file.
