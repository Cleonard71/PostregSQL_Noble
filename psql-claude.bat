@echo off
rem Fill in your claude_app password from CONNECTION.md
set PGPASSWORD=YOUR_APP_PASSWORD
"C:\PostgreSQL\pgsql\bin\psql.exe" -h localhost -U claude_app -d claude_hub
