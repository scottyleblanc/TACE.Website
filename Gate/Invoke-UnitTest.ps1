#Requires -Version 7.6

<#
.SYNOPSIS
    Runs this repository's unit tests and builds the Hugo site, for gate check GK11.

.DESCRIPTION
    Runs the offline econ tests (python -m pytest app/econ; the live upstream tests are
    excluded by app/econ/pytest.ini) and then builds the site with Hugo into a temporary
    folder, so a broken test or a page that fails to build stops the pull request before
    it reaches main. Exits 0 only when both pass. Prints one [PASS] or [FAIL] line per
    step; the gate reports the [FAIL] lines.

    Python with pytest and boto3, and Hugo Extended, must be on PATH. The PaperMod theme
    submodule must be checked out (git submodule update --init).

.EXAMPLE
    pwsh -NoProfile -File ./Gate/Invoke-UnitTest.ps1

    Runs both steps from the repository root.

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

# Step 1: the econ tests.
$econPath = Join-Path -Path $repoRoot -ChildPath 'app' -AdditionalChildPath 'econ'
$pytestOut = @(& python -m pytest $econPath -q 2>&1 | ForEach-Object { "$PSItem" })
if ($LASTEXITCODE -eq 0) {
    Write-Output "[PASS] pytest app/econ: $(@($pytestOut | Where-Object { $PSItem -match 'passed' }) | Select-Object -Last 1)"
}
else {
    $failures++
    $pytestOut | Select-Object -Last 15 | ForEach-Object { Write-Output "  $PSItem" }
    Write-Output "[FAIL] pytest app/econ (exit $LASTEXITCODE)"
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

if ($failures -gt 0) { exit 1 }
exit 0
