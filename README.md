# claude-hub

PostgreSQL database for Claude's memory + all application data.

## What's in here

| Schema | Purpose |
|---|---|
| `memory` | Mirror of Claude's markdown memory files (queryable) |
| `apps_shared` | Cross-app registry and event log |
| `smart_agent` | SmartAgent application data |
| `medical_records` | MedicalRecordsApp data (HIPAA-sensitive) |

## Setup on a new machine

### 1. Install PostgreSQL 16

Download the binaries zip from:
https://www.enterprisedb.com/download-postgresql-binaries

Extract to `C:\PostgreSQL\pgsql`

### 2. Initialize the database

```cmd
md C:\PostgreSQL\data
md C:\PostgreSQL\logs
"C:\PostgreSQL\pgsql\bin\initdb.exe" -D "C:\PostgreSQL\data" -U postgres -E UTF8 --locale=C
```

### 3. Start the server

```cmd
C:\PostgreSQL\start_postgres.bat
```

Or register auto-start (run cmd as Administrator):
```cmd
schtasks /Create /TN "PostgreSQL_claude_hub" /SC ONLOGON /TR "C:\PostgreSQL\start_postgres.bat" /F
```

### 4. Create the database and schemas

```cmd
set PGPASSWORD=YOUR_POSTGRES_PASSWORD
"C:\PostgreSQL\pgsql\bin\psql.exe" -h localhost -U postgres -d postgres -f "C:\PostgreSQL\claude-hub\init_claude_hub.sql"
```

### 5. Copy CONNECTION.md

Copy `CONNECTION.template.md` → `CONNECTION.md` and fill in your passwords.

### 6. Sync memory files

```cmd
pip install psycopg[binary]
python sync_to_postgres.py
```

## Files

| File | Purpose |
|---|---|
| `init_claude_hub.sql` | Full schema — run once to create DB + all schemas |
| `sync_to_postgres.py` | Syncs markdown memory files → `memory.entries` |
| `start_postgres.bat` | Start the PostgreSQL server |
| `psql-claude.bat` | Open psql as `claude_app` (fill password first) |
| `CONNECTION.template.md` | Copy → `CONNECTION.md` and fill in passwords |
