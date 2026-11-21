#Requires -Version 7.6

<#
.SYNOPSIS
    Runs the repository's evidence script and records the result for gate check GK12
    (rule EV-001).

.DESCRIPTION
    Runs the script gate.config.psd1 names under Evidence.Script, usually the
    integration tests that need a machine or service CI does not have, and writes the
    record Evidence.Record names. GK12 then accepts the branch's changes under
    Evidence.Paths without running those tests in CI.

    The record holds the commit the run was made on, whether the working tree was
    clean, whether the script passed, and Evidence, true only for a passing run on a
    clean tree. Uncommitted changes, untracked files included, make the run not count:
    the evidence must describe a commit. The record itself does not count as a change,
    since every run rewrites it. The record holds no host name, user name or path
    outside the repository.

    Commit the record as the last commit of the branch. GK12 fails when any file other
    than the evidence record and the review record changes after the run's commit.

.EXAMPLE
    pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-EvidenceRun.ps1

    Runs Evidence.Script and writes the record. Exits 0 when the record is evidence.

.NOTES
    **Invocation:** Standalone — self-contained; safe to run with `pwsh -File`. Needs git
    and Checks.Evidence on in gate.config.psd1. Writes only Evidence.Record.
#>
[CmdletBinding(SupportsShouldProcess)]
[OutputType([string])]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path -Path $PSScriptRoot -ChildPath 'Lib' -AdditionalChildPath 'GateLib.ps1')

$repoRoot = Get-GateRepoRoot -Path $PSScriptRoot

$loaded = Import-GateConfig -RepoRoot $repoRoot
if ($loaded.Problems.Count -gt 0) { throw "[Invoke-EvidenceRun] gate.config.psd1 is not valid: $($loaded.Problems -join '; ')" }
$config = $loaded.Config
if (-not $config.Checks.Evidence) { throw '[Invoke-EvidenceRun] Checks.Evidence is off in gate.config.psd1, so no evidence is needed.' }

$recordPath = $config.Evidence.Record
$recordFile = Resolve-GatePath -RepoRoot $repoRoot -RelativePath $recordPath

# Read before the run, so the record describes the tree the script ran against.
$commit = @(& git -C $repoRoot rev-parse --verify --quiet 'HEAD^{commit}' 2>$null) | Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or -not $commit) { throw '[Invoke-EvidenceRun] The repository has no commit to record evidence for.' }
$status = @(& git -C $repoRoot status --porcelain --untracked-files=all 2>$null)
if ($LASTEXITCODE -ne 0) { throw '[Invoke-EvidenceRun] git could not read the working tree status.' }
$changes   = @($status | Where-Object { $PSItem -and $PSItem.Substring(3).Trim('"') -ne $recordPath })
$treeClean = $changes.Count -eq 0

Write-Output "[INFO] evidence: running $($config.Evidence.Script) on $($commit.Substring(0, 7))"
& pwsh -NoProfile -File (Resolve-GatePath -RepoRoot $repoRoot -RelativePath $config.Evidence.Script)
$exitCode = $LASTEXITCODE
$passed   = $exitCode -eq 0

$record = [ordered]@{
    SchemaVersion    = 1
    Script           = $config.Evidence.Script
    Commit           = $commit
    WorkingTreeClean = $treeClean
    Passed           = $passed
    ExitCode         = $exitCode
    Evidence         = $treeClean -and $passed
    RunAtUtc         = [datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    PowerShell       = $PSVersionTable.PSVersion.ToString()
}

if ($PSCmdlet.ShouldProcess($recordPath, 'Write the evidence record')) {
    $null = New-Item -Path (Split-Path -Path $recordFile -Parent) -ItemType Directory -Force
    $json = (ConvertTo-Json -InputObject $record -Depth 3) -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($recordFile, $json + "`n", [System.Text.UTF8Encoding]::new($false))
}

if ($record.Evidence) {
    Write-Output "[PASS] evidence: $recordPath records a passing run on $($commit.Substring(0, 7)). Commit it as the last commit of the branch."
    exit 0
}
if (-not $passed) {
    Write-Output "[FAIL] evidence: $($config.Evidence.Script) failed (exit $exitCode); $recordPath is written but is not evidence."
}
else {
    Write-Output "[FAIL] evidence: the working tree had $($changes.Count) uncommitted change(s), so $recordPath is not evidence. Commit them and run again."
}
exit 1
