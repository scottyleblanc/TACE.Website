#Requires -Version 7.6

<#
.SYNOPSIS
    Runs this repository's unit tests and builds the Hugo site, for gate check GK11.

.DESCRIPTION
    Runs the offline econ tests (python -m pytest app/econ; the live upstream tests are
    excluded by app/econ/pytest.ini) and the tracker Lambda tests (app/train), builds the
    site with Hugo into a temporary folder, and checks every pip install in
    .github/workflows, so a broken test, a page that fails to build or an unpinned
    install stops the pull request before it reaches main. Exits 0 only when every step
    passes. Prints one [PASS] or [FAIL] line per step; the gate reports the [FAIL] lines.

    The workflow check fails when a pip install does not install from a requirements file
    with --require-hashes, or comes after configure-aws-credentials in the same file.
    Shell line continuations are joined first; comment lines are skipped.

    Python with pytest and boto3, and Hugo Extended, must be on PATH. The PaperMod theme
    submodule must be checked out (git submodule update --init).

.EXAMPLE
    pwsh -NoProfile -File ./Gate/Invoke-UnitTest.ps1

    Runs every step from the repository root.

.EXAMPLE
    pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1 -Unit

    Runs every gate check, and this script as GK11.

.NOTES
    Called by tools/gate/Scripts/Invoke-Gate.ps1 (GK11, rule UT-001) and, through it, by
    .github/workflows/gate.yml on every pull request.
    [SEC] Needs no secrets and no AWS access: the build writes only to a temporary
    folder, which is removed afterwards, and uses a placeholder base URL.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Path $PSScriptRoot -Parent
$failures = 0

foreach ($tool in 'python', 'hugo') {
    if (-not (Get-Command -Name $tool -CommandType Application -ErrorAction SilentlyContinue)) {
        Write-Output "[FAIL] $tool is not on PATH"
        exit 1
    }
}

# Step 1: the econ and tracker tests.
foreach ($suite in 'econ', 'train') {
    $suitePath = Join-Path -Path $repoRoot -ChildPath 'app' -AdditionalChildPath $suite
    $pytestOut = @(& python -m pytest $suitePath -q 2>&1 | ForEach-Object { "$PSItem" })
    if ($LASTEXITCODE -eq 0) {
        Write-Output "[PASS] pytest app/${suite}: $(@($pytestOut | Where-Object { $PSItem -match 'passed' }) | Select-Object -Last 1)"
    }
    else {
        $failures++
        $pytestOut | Select-Object -Last 15 | ForEach-Object { Write-Output "  $PSItem" }
        Write-Output "[FAIL] pytest app/$suite (exit $LASTEXITCODE)"
    }
}

# Step 2: the Hugo build, into a temporary folder.
$hugoSource = Join-Path -Path $repoRoot -ChildPath 'hugo'
$buildDir   = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath "gate-hugo-$([guid]::NewGuid().ToString('N'))"
try {
    $hugoArgs = @('--source', $hugoSource, '--destination', $buildDir, '--minify', '--baseURL', 'https://example.org/', '--quiet')
    $hugoOut  = @(& hugo @hugoArgs 2>&1 | ForEach-Object { "$PSItem" })
    if ($LASTEXITCODE -eq 0) {
        Write-Output '[PASS] hugo build'
    }
    else {
        $failures++
        $hugoOut | Select-Object -Last 15 | ForEach-Object { Write-Output "  $PSItem" }
        Write-Output "[FAIL] hugo build (exit $LASTEXITCODE)"
    }
}
finally {
    if (Test-Path -LiteralPath $buildDir) {
        Remove-Item -LiteralPath $buildDir -Recurse -Force
    }
}

# Step 3: every pip install in a workflow is hashed and runs before AWS credentials exist.
# [SEC] A package installed after configure-aws-credentials runs alongside the deploy
# role; an unhashed install ships whatever the index serves that day.
$workflowDir = Join-Path -Path $repoRoot -ChildPath '.github' -AdditionalChildPath 'workflows'
$pipProblems = [System.Collections.Generic.List[string]]::new()
foreach ($workflow in @(Get-ChildItem -LiteralPath $workflowDir -Filter '*.yml' -File)) {
    $text      = (Get-Content -LiteralPath $workflow.FullName -Raw) -replace '\\\r?\n\s*', ' '
    $credsSeen = $false
    foreach ($line in @($text -split '\r?\n')) {
        if ($line -match '^\s*#') { continue }
        if ($line -match 'aws-actions/configure-aws-credentials') { $credsSeen = $true }
        if ($line -notmatch '\bpip\s+install\b') { continue }
        $command = $line.Trim()
        if ($command -notmatch '\s--require-hashes\b' -or $command -notmatch '\s-r\s+\S+') {
            $pipProblems.Add("$($workflow.Name): not from a hashed requirements file: $command")
        }
        if ($credsSeen) {
            $pipProblems.Add("$($workflow.Name): after configure-aws-credentials: $command")
        }
    }
}
if ($pipProblems.Count -eq 0) {
    Write-Output '[PASS] workflow pip installs: hashed, before AWS credentials'
}
else {
    $failures++
    $pipProblems | ForEach-Object { Write-Output "  $PSItem" }
    Write-Output "[FAIL] workflow pip installs ($($pipProblems.Count) problem(s))"
}

if ($failures -gt 0) { exit 1 }
exit 0
