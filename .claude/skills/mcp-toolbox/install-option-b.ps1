<#
.SYNOPSIS
  MCP toolbox, option B: Context7 (user scope) + shadcn/ui MCP (per project) for Claude Code on Windows.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install-option-b.ps1
  powershell -ExecutionPolicy Bypass -File .\install-option-b.ps1 -ProjectPath C:\dev\osint-hunter
  powershell -ExecutionPolicy Bypass -File .\install-option-b.ps1 -SkipContext7 -ProjectPath C:\dev\pc-command-center

.NOTES
  Safe to re-run: existing entries are replaced, not duplicated.
  Context7 key: pass -Context7Key, set $env:CONTEXT7_API_KEY, or type it at the prompt (blank = no key, lower rate limits).
#>
param(
    [string]$ProjectPath,
    [string]$Context7Key = $env:CONTEXT7_API_KEY,
    [switch]$SkipContext7,
    [switch]$SkipNode
)

$ErrorActionPreference = 'Stop'

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "    XX  $msg" -ForegroundColor Red; exit 1 }

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# --- 1. Claude Code CLI ---------------------------------------------------
Step 'Checking Claude Code CLI'
if (-not (Has 'claude')) {
    Fail "'claude' not found on PATH. Install Claude Code first, then re-run this script."
}
Ok (claude --version)

# --- 2. Node.js LTS (needed for npx / shadcn) -----------------------------
if (-not $SkipNode) {
    Step 'Checking Node.js (need 22.5+)'
    $needNode = $true
    if (Has 'node') {
        $v = [version]((node --version).TrimStart('v'))
        if ($v -ge [version]'22.5.0') { $needNode = $false; Ok "node $v" }
        else { Warn "node $v is too old; upgrading" }
    }
    if ($needNode) {
        if (-not (Has 'winget')) { Fail 'winget not found. Install Node.js LTS from nodejs.org, then re-run.' }
        winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { Warn "winget exited $LASTEXITCODE (may already be installed)" }
        Refresh-Path
        if (-not (Has 'node')) { Fail 'Node installed but not on PATH yet. Open a new terminal and re-run.' }
        Ok "node $(node --version)"
    }
}

# --- 3. Context7 (user scope, remote HTTP) --------------------------------
if (-not $SkipContext7) {
    Step 'Adding Context7 MCP (user scope)'
    if (-not $Context7Key) {
        $secure = Read-Host 'Context7 API key (free at context7.com/dashboard; Enter to skip)' -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { $Context7Key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }

    # Remove any previous entry so re-runs don't fail on "already exists".
    claude mcp remove context7 --scope user 2>$null | Out-Null

    $c7 = @('mcp', 'add', '--scope', 'user', '--transport', 'http')
    if ($Context7Key) { $c7 += @('--header', "CONTEXT7_API_KEY: $Context7Key") }
    else { Warn 'No key: Context7 will work with lower rate limits.' }
    $c7 += @('context7', 'https://mcp.context7.com/mcp')

    & claude @c7
    if ($LASTEXITCODE -ne 0) { Fail 'claude mcp add context7 failed.' }
    Ok 'context7 added (key stored in your user Claude config, not printed)'
    $Context7Key = $null
}

# --- 4. shadcn/ui MCP (per project) ---------------------------------------
if ($ProjectPath) {
    Step "Adding shadcn/ui MCP to $ProjectPath"
    if (-not (Test-Path (Join-Path $ProjectPath 'package.json'))) {
        Fail "No package.json in $ProjectPath. Point -ProjectPath at a React/Vite project root."
    }
    Push-Location $ProjectPath
    try {
        if (-not (Test-Path 'components.json')) {
            Warn 'No components.json (shadcn not initialised here).'
            $ans = Read-Host 'Run "npx shadcn@latest init" now? It edits Tailwind/CSS config. (y/N)'
            if ($ans -notmatch '^[Yy]') { Fail 'Skipped. Run shadcn init yourself, then re-run with -SkipContext7.' }
            npx shadcn@latest init
            if ($LASTEXITCODE -ne 0) { Fail 'shadcn init failed.' }
        }
        npx shadcn@latest mcp init --client claude
        if ($LASTEXITCODE -ne 0) { Fail 'shadcn mcp init failed.' }
        Ok '.mcp.json written (commit it so the project keeps the server)'
    }
    finally { Pop-Location }
}
else {
    Step 'shadcn/ui MCP skipped (no -ProjectPath)'
    Warn 'Re-run per project: .\install-option-b.ps1 -SkipContext7 -ProjectPath <project root>'
}

# --- 5. Verify -------------------------------------------------------------
Step 'Registered MCP servers'
if ($ProjectPath) { Push-Location $ProjectPath }
try { claude mcp list } finally { if ($ProjectPath) { Pop-Location } }

Write-Host "`nDone. Restart Claude Code, then run /mcp to confirm." -ForegroundColor Green
Write-Host 'Tip: add "use context7" to prompts, or a CLAUDE.md rule, to pull live docs.'
