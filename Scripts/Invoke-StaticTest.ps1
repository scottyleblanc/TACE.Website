#Requires -Version 7.6

<#
.SYNOPSIS
    Runs the Pester tests in one folder for check GK04 (rule ST-001).

.DESCRIPTION
    Runs every *.Tests.ps1 file under -Path and prints one summary line. Exits 1 when
    any test fails or any test file fails to run, and 0 otherwise. Writes no results
    file.

.PARAMETER Path
    The folder of static tests.

.EXAMPLE
    pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-StaticTest.ps1 -Path ./tests/static

.NOTES
    **Invocation:** Standalone — self-contained; safe to run with `pwsh -File`. Called by
    Invoke-Gate.ps1 in its own process.
#>
[CmdletBinding()]
[OutputType([string])]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $PSItem -PathType Container })]
    [string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module Pester -MinimumVersion 5.0

$config = New-PesterConfiguration
$config.Run.Path         = $Path
$config.Run.PassThru     = $true
$config.Output.Verbosity = 'Detailed'

$result = Invoke-Pester -Configuration $config

# A failure above any Describe block (a parse error, or a throwing file-level block)
# counts only in FailedContainersCount. Checking FailedCount alone would pass a run in
# which a whole test file never ran.
$failed = $result.FailedCount -gt 0 -or $result.FailedContainersCount -gt 0

$label = if ($failed) { '[FAIL]' } else { '[PASS]' }
Write-Output ('{0} static: {1} passed, {2} failed, {3} skipped, {4} file(s) failed to run' -f
    $label, $result.PassedCount, $result.FailedCount, $result.SkippedCount, $result.FailedContainersCount)

if ($failed) { exit 1 }

# Explicit, so a caller never reads a $LASTEXITCODE left over from an earlier command.
exit 0
