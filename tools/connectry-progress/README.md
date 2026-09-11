# MCP progress database

`progress.db` is the `connectry-architect` MCP server's SQLite store — dashboards,
assessment history, task-statement mastery.

By default the server writes it to `$HOME/.connectry-architect/progress.db`, which is
per-machine and, in a Claude Code cloud session, lives on a VM that gets reclaimed after
inactivity. `.mcp.json` sets `CONNECTRY_DB_PATH` to this directory instead, so progress
lives in the repo and travels with a clone.

For progress made in a cloud session to survive, `progress.db` has to be **committed**
like any other file. The `-wal` / `-shm` sidecars SQLite writes alongside it are
gitignored; commit only `progress.db`, and only when the server isn't mid-write.

This directory must exist before the server starts — it does not create it, and a missing
directory makes the first MCP tool call fail with "Cannot open database because the
directory does not exist". That's what `.gitkeep` is for.
