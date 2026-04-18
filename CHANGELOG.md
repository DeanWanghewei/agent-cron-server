# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-04-18

### Added

- Web UI Dashboard — browser-based monitoring at `/dashboard/`
  - Dashboard overview with stats and recent executions
  - Task list with CRUD operations, filtering, and manual trigger
  - Task detail page with associated execution records
  - Execution records list with status filtering
  - Execution log detail page (stdout/stderr)
- Dark / Light / System theme toggle with localStorage persistence
- Sidebar navigation with active-page highlighting
- Execution logs stored as date-based files on disk (`data/logs/YYYY-MM-DD/`) instead of database TEXT fields
- Auto cleanup of expired log files (configurable `LOG_RETENTION_DAYS`)
- Alembic database migrations — schema auto-upgrades on service startup
- `.env.example` with all configuration options documented

### Changed

- SKILL.md rewritten to enforce MCP-tool-only interaction (no curl/API)
- README.md updated with MCP interaction guide (mcporter CLI), systemd deployment without root
- Time display fixed to respect server timezone (UTC → local conversion)
- `init_db()` now runs Alembic `upgrade head` instead of `create_all`

## [0.1.0] - 2026-04-16

### Added

- FastAPI REST API for cron task management (`/api/v1/tasks`, `/api/v1/executions`)
- MCP Server (FastMCP StreamableHTTP) mounted at `/mcp/`
- APScheduler-based cron scheduling with async subprocess execution
- SQLite (aiosqlite) / PostgreSQL (asyncpg) async database support
- Task CRUD: create, read, update, delete, enable/disable, manual trigger
- Execution tracking: status, duration, exit code, error message
- Execution log capture (stdout/stderr)
- Pydantic Settings with `.env` file support
- Skill definition (`skill/SKILL.md`) for hermes-agent & openclaw integration
- Basic systemd service file for deployment
