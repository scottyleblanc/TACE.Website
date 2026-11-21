#Requires -Version 7.6

<#
.SYNOPSIS
    Builds the agent instruction file from the repository's standards files, for gate
    check GK14 (rule AG-001).

.DESCRIPTION
    Joins the files gate.config.psd1 lists under Instructions.Sources, in that order,
    into the file Instructions.Output names (AGENTS.md by default), under a generated
    header that tells an agent to run the gate before it reports a change as done.
    Each source file's title becomes a second-level heading followed by a Source line,
    its other headings move down one level, and its relative links are rewritten to
    resolve from the repository root.

    AI coding agents read AGENTS.md at the repository root; Claude Code reads it
    through an @AGENTS.md import in CLAUDE.md. GK14 fails when the committed file does
    not match what this script builds, so a change to a standard reaches the agents in
    the same pull request.

.EXAMPLE
    pwsh -NoProfile -File ./tools/gate/Scripts/Export-AgentInstruction.ps1

    Rewrites the instruction file. Commit it with the source change.

.NOTES
    **Invocation:** Standalone — self-contained; safe to run with `pwsh -File`. Needs
    Checks.Instructions on in gate.config.psd1. Writes only Instructions.Output.
#>
[CmdletBinding(SupportsShouldProcess)]
[OutputType([string])]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path -Path $PSScriptRoot -ChildPath 'Lib' -AdditionalChildPath 'GateLib.ps1')

$kitRoot  = Split-Path -Path $PSScriptRoot -Parent
$repoRoot = Get-GateRepoRoot -Path $PSScriptRoot
$kitPath  = [System.IO.Path]::GetRelativePath($repoRoot, $kitRoot).Replace('\', '/')
$kitPath  = if ($kitPath -eq '.') { '.' } else { "./$kitPath" }

$loaded = Import-GateConfig -RepoRoot $repoRoot
if ($loaded.Problems.Count -gt 0) { throw "[Export-AgentInstruction] gate.config.psd1 is not valid: $($loaded.Problems -join '; ')" }
$config = $loaded.Config
if (-not $config.Checks.Instructions) { throw '[Export-AgentInstruction] Checks.Instructions is off in gate.config.psd1: turn it on and list Instructions.Sources.' }

$text   = Get-GateAgentInstruction -RepoRoot $repoRoot -KitPath $kitPath -Config $config
$target = Resolve-GatePath -RepoRoot $repoRoot -RelativePath $config.Instructions.Output
$count  = @($config.Instructions.Sources).Count

if ($PSCmdlet.ShouldProcess($config.Instructions.Output, "Write the agent instructions from $count source file(s)")) {
    $null = New-Item -Path (Split-Path -Path $target -Parent) -ItemType Directory -Force
    [System.IO.File]::WriteAllText($target, $text, [System.Text.UTF8Encoding]::new($false))
    Write-Output "[INFO] $($config.Instructions.Output): built from $count source file(s)"
}
