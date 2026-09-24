# ConnectGuidance Django

Django replica of **GuidanceConnect** (original Next.js app in `../connectguidance1`).  
Phase 1 foundation: Python + Django + Supabase PostgreSQL only — no app features yet.

## Documentation (master plan)

| Doc | Purpose |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | **Start here** — Phases 1–8, steps 1–73, checklist |
| [docs/ERD.md](docs/ERD.md) | Data model / Django models spec |
| [docs/FLOWS.md](docs/FLOWS.md) | 24 system flowcharts |
| [docs/INTERFACES.md](docs/INTERFACES.md) | 16 UI screens + design tokens |
| [docs/RLS_AND_SECURITY.md](docs/RLS_AND_SECURITY.md) | Access control (Supabase RLS → Django) |
| [docs/REFERENCES.md](docs/REFERENCES.md) | Pointers into the original Next.js repo |

## Python Virtual Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Dependency Installation

```powershell
pip install -r requirements.txt
```

## Environment Variable Setup

Copy `.env.example` to `.env` and set your real values:

```powershell
Copy-Item .env.example .env
```

Required in `.env` before first `migrate`:

- `DJANGO_SECRET_KEY` — generate with  
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DJANGO_DEBUG=True`
- `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`
- `DATABASE_URL` — Supabase **Settings → Database → Connection string (URI)** with `sslmode=require`

## Supabase PostgreSQL Configuration

1. Open your Supabase project → **Settings → Database**
2. Copy the connection URI (use port `6543` pooler or `5432` direct)
3. Paste into `.env` as `DATABASE_URL`

## How to Run Django Checks

```powershell
python manage.py check
```

## How to Run Migrations (Phase 2+)

```powershell
python manage.py makemigrations
python manage.py migrate
```

## How to Start the Development Server

```powershell
python manage.py runserver
```

## Roadmap

See [docs/PLAN.md](docs/PLAN.md): Phase 1 foundation → models → auth/RBAC → appointments → case notes → mood/chat → 16 screens → audit/reports.
