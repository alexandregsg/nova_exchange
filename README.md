# Nova Exchange

A student marketplace built with Python.

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and add your Supabase credentials
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run locally:
   ```
   python -m uvicorn main:app --reload
   ```

## Supabase Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Go to Settings → API
3. Copy the Project URL and anon key to your `.env` file
4. Run the SQL table creation script (if provided)

## Deployment

Deploy to any platform that supports Python (Render, Railway, Fly.io, etc.).

Set these environment variables in your hosting platform:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY` (optional, for admin operations)