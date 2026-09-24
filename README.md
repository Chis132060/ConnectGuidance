# ConnectGuidance Django

Minimal Django foundation configured to use Supabase PostgreSQL as the database.

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

Copy `.env.example` to `.env` and set your Supabase PostgreSQL credentials:

```powershell
cp .env.example .env
```

Edit `.env` with your actual Supabase PostgreSQL connection details:

```
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True

DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=your-supabase-host
DB_PORT=5432
DB_SSLMODE=require

DATABASE_URL=postgres://your-supabase-host:5432/postgres?sslmode=require
```

## Supabase PostgreSQL Configuration

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Go to Settings > Database to get your connection string
3. The `DATABASE_URL` environment variable is used by Django to connect

## How to Run Django Checks

```powershell
python manage.py check
```

## How to Start the Development Server

```powershell
python manage.py runserver
```