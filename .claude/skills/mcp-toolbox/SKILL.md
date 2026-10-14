---
name: mcp-toolbox
description: Install/use reference for five MCP servers (Context7, Chrome DevTools MCP, DBHub, Serena, shadcn/ui MCP) for Claude Code on Windows. Use when asked to set up, install, or choose MCP servers, or when a task would benefit from live docs, browser debugging, DB inspection, symbol navigation, or shadcn components.
---

# MCP toolbox

Installs go into **Claude Code / Claude Desktop** on your machine, not a chat or cloud session.

## Windows prep
- `winget install OpenJS.NodeJS.LTS` (DBHub needs Node 22.5+)
- `winget install astral-sh.uv` (Serena)
- If an `npx` server won't start on native Windows: `claude mcp add <name> -- cmd /c npx ...`

## Scope
- User scope (`--scope user`): Context7, Chrome DevTools, Serena.
- Per project: DBHub (DSN), shadcn (`components.json`).
- Recommended default: Context7 + shadcn now; add the rest when a project needs them.
- Option B installer: `install-option-b.ps1` in this folder (`powershell -ExecutionPolicy Bypass -File .\install-option-b.ps1 [-ProjectPath <root>]`).
- Software cost $0; real cost is extra tokens per tool call.

## 1. Context7 (Upstash) — current library docs
- Install: `claude mcp add --scope user --header "CONTEXT7_API_KEY: YOUR_KEY" --transport http context7 https://mcp.context7.com/mcp`
- Use: say "use context7", or add a CLAUDE.md rule. Free key at context7.com/dashboard. Keep the key private.
- Cons: only as good as indexed docs; adds tokens per lookup.

## 2. Chrome DevTools MCP (Google) — drive/inspect Chrome
- Install: `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`
- Use: "Open localhost:5173, check the console, fix errors."
- Don't use on logged-in banking/email sessions. Uses its own Chrome profile by default. Overlaps with Claude in Chrome.

## 3. DBHub (Bytebase) — SQL databases
- Install: `claude mcp add dbhub -- npx -y @bytebase/dbhub --readonly --dsn "postgres://user:pass@localhost:5432/db"`
- Supports Postgres, MySQL, SQL Server, MariaDB, SQLite. No NoSQL/Redis.
- Always `--readonly`; never point at production; try `--demo` first.

## 4. Serena (Oraios) — symbol-level code navigation
- Install: `uv tool install -p 3.13 serena-agent` → `serena init` → `claude mcp add --scope user serena -- serena start-mcp-server --context claude-code --project-from-cwd`
- Run `serena project index` first. Old `uvx ... serena-mcp-server` instructions are outdated.
- Heaviest setup (language servers use RAM/disk); best on big repos (e.g. Kotlin).

## 5. shadcn/ui MCP — browse/install components
- Prereq: `npx shadcn@latest init` (creates `components.json`).
- Install from project root: `npx shadcn@latest mcp init --client claude` (writes `.mcp.json`), restart, check `/mcp`.
- Won't apply custom themes by itself.

## Official sources (verify before installing)
- Context7: https://github.com/upstash/context7
- Chrome DevTools MCP: https://github.com/ChromeDevTools/chrome-devtools-mcp
- DBHub: https://github.com/bytebase/dbhub
- Serena: https://github.com/oraios/serena
- shadcn MCP: https://ui.shadcn.com/docs/mcp
