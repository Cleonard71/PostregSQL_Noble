# claude_hub PostgreSQL — connection reference
# Copy this file to CONNECTION.md and fill in your passwords.
# CONNECTION.md is gitignored — never commit it.

## Server
- Host: `localhost`
- Port: `5432`
- Install dir: `C:\PostgreSQL\pgsql`
- Data dir:    `C:\PostgreSQL\data`
- Logs:        `C:\PostgreSQL\logs\server.log`
- Version:     PostgreSQL 16

## Credentials
| User         | Password         | Use                        |
|--------------|------------------|----------------------------|
| `postgres`   | YOUR_PG_PASSWORD | Superuser (admin only)     |
| `claude_app` | YOUR_APP_PASSWORD| Application connections    |

## Connection strings

```
# psql (cmd)
set PGPASSWORD=YOUR_APP_PASSWORD
"C:\PostgreSQL\pgsql\bin\psql.exe" -h localhost -U claude_app -d claude_hub

# psql (PowerShell)
$env:PGPASSWORD = "YOUR_APP_PASSWORD"
& "C:\PostgreSQL\pgsql\bin\psql.exe" -h localhost -U claude_app -d claude_hub

# Python (psycopg)
psycopg.connect("host=localhost port=5432 dbname=claude_hub user=claude_app password=YOUR_APP_PASSWORD")

# SQLAlchemy / generic URL
postgresql://claude_app:YOUR_APP_PASSWORD@localhost:5432/claude_hub
```

## Memory sync

```
python sync_to_postgres.py
```
