<#
  Option 1 — put JJ-Takeoff on a PRIVATE GitHub remote.

  Everything is staged. This script only runs after you authenticate, because
  `gh auth login` needs a browser and cannot be automated.

  STEP 1 (you, once):   gh auth login
  STEP 2 (this script): powershell -ExecutionPolicy Bypass -File eval\push_to_github.ps1

  It refuses to run if you are not authenticated, and it VERIFIES the repo is
  private after creating it — a public repo here would publish J&J's cost
  structure and client list.
#>
$ErrorActionPreference = "Stop"
$REPO = "jj-takeoff"
$ROOT = Split-Path $PSScriptRoot -Parent
$gh   = "C:\Program Files\GitHub CLI\gh.exe"

if (-not (Test-Path $gh)) { throw "gh not found at $gh" }

& $gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Not authenticated. Run this first, then re-run this script:" -ForegroundColor Yellow
  Write-Host "    gh auth login" -ForegroundColor Cyan
  exit 1
}
$who = (& $gh api user --jq .login).Trim()
Write-Host "authenticated as $who"

Push-Location $ROOT
try {
  # never push a dirty tree — what is on the remote should be a commit you can reproduce
  if ((git status --porcelain).Length -gt 0) { throw "working tree is dirty — commit first" }

  git gc --quiet --aggressive 2>&1 | Out-Null

  $exists = $false
  & $gh repo view "$who/$REPO" 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { $exists = $true }

  if (-not $exists) {
    Write-Host "creating PRIVATE repo $who/$REPO"
    & $gh repo create $REPO --private --source=. --remote=origin --description "J&J Custom Homes takeoff + estimating engine, and the Level Ground report that runs on it"
    if ($LASTEXITCODE -ne 0) { throw "repo create failed" }
  } elseif (-not (git remote | Select-String -Quiet '^origin$')) {
    git remote add origin "https://github.com/$who/$REPO.git"
  }

  # HARD GATE: confirm private BEFORE any object leaves the machine.
  $vis = (& $gh repo view "$who/$REPO" --json visibility --jq .visibility).Trim()
  if ($vis -ne "PRIVATE") {
    throw "repo visibility is '$vis', refusing to push. Fix: gh repo edit $who/$REPO --visibility private"
  }
  Write-Host "visibility confirmed: PRIVATE"

  git push -u origin (git rev-parse --abbrev-ref HEAD)
  if ($LASTEXITCODE -ne 0) { throw "push failed" }

  Write-Host ""
  Write-Host "pushed. remote: https://github.com/$who/$REPO  (private)" -ForegroundColor Green
  Write-Host "from now on `git push` covers history; `python jj.py backup` covers the binaries git ignores."
}
finally { Pop-Location }
