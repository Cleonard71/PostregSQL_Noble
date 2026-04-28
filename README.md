# claude-hub

PostgreSQL database for Claude's memory + all application data.

## What's in here

| Schema | Purpose |
|---|---|
| `memory` | Mirror of Claude's markdown memory files (queryable) |
| `apps_shared` | Cross-app registry, event log, and file metadata (`files` table) |
| `smart_agent` | SmartAgent application data |
| `medical_records` | MedicalRecordsApp data (HIPAA-sensitive) |

## File storage

Physical files live on disk at `C:\Users\Cyd_L\Documents\Claude\Files\<app>\`.
Metadata (path, size, tags, mime type, description) is tracked in `apps_shared.files`.

Use `store_file.py` to store a file:
```cmd
python store_file.py C:\path\to\report.pdf --app shared --tags report 2026
```

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
"C:\PostgreSQL\pgsql\bin\psql.exe" -h localhost -U postgres -d postgres -f "C:\PostgreSQL\claude-hub\add_files_table.sql"
```

### 4b. Create file storage directories

```cmd
md C:\Users\%USERNAME%\Documents\Claude\Files\smart_agent
md C:\Users\%USERNAME%\Documents\Claude\Files\medical_records
md C:\Users\%USERNAME%\Documents\Claude\Files\shared
```

### 4c. Wire up MCP servers (optional, for Claude Desktop / Claude Code integration)

```cmd
npm install -g @modelcontextprotocol/server-postgres
```

Then add to `%APPDATA%\Claude\claude_desktop_config.json` and `%USERPROFILE%\.claude\mcp.json`:
```json
{
  "mcpServers": {
    "claude-hub-postgres": {
      "command": "C:\\Users\\YOU\\AppData\\Roaming\\npm\\mcp-server-postgres.cmd",
      "args": ["postgresql://claude_app:YOUR_PW_URLENCODED@localhost:5432/claude_hub"]
    }
  }
}
```
Note: URL-encode special chars in the password (`#` → `%23`).

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
| `add_files_table.sql` | Adds `apps_shared.files` for tracking disk files |
| `sync_to_postgres.py` | Syncs markdown memory files → `memory.entries` |
| `store_file.py` | Copies a file to disk + registers row in `apps_shared.files` |
| `start_postgres.bat` | Start the PostgreSQL server |
| `psql-claude.bat` | Open psql as `claude_app` (fill password first) |
| `CONNECTION.template.md` | Copy → `CONNECTION.md` and fill in passwords |
