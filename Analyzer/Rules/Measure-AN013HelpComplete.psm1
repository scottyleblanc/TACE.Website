#Requires -Version 7.6

. (Join-Path -Path $PSScriptRoot -ChildPath '..' -AdditionalChildPath 'Lib', 'Get-GateRuleTarget.ps1')

function Measure-AN013HelpComplete {
    <#
    .SYNOPSIS
        Rule AN-013: every script and function has complete help that Get-Help can read.

    .DESCRIPTION
        Reports a script with a param block, or a function, whose comment-based help is
        missing or unreadable, lacks a synopsis, description, example or notes section,
        lacks a parameter entry for any of its parameters, or has a parameter entry for
        a parameter that does not exist. A function defined inside another function or
        inside such a script is skipped. Custom PSScriptAnalyzer rule.

        Help that PowerShell cannot read is reported as missing: Get-Help then shows only
        the syntax. The usual causes are a misspelt keyword, a prose line that starts
        with a dot (read as an unknown keyword), and a script's help block written on the
        line directly below #Requires.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        script or function, naming every gap in its help.

    .NOTES
        Returns diagnostic records, not the Success/Data/Message object: this is the
        contract PSScriptAnalyzer requires of a rule.
    #>
    [CmdletBinding()]
    [OutputType([Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNull()]
        [System.Management.Automation.Language.ScriptBlockAst]$ScriptBlockAst
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ($null -ne $ScriptBlockAst.Parent) { return }

    foreach ($target in @(Get-GateRuleTarget -ScriptBlockAst $ScriptBlockAst)) {
        $help = $target.Node.GetHelpContent()
        $gaps = if ($null -eq $help) {
            @('no help block that Get-Help can read (a misspelt keyword, a prose line that starts with a dot, or script help directly below #Requires)')
        } else {
            Get-AN013HelpGap -Help $help -ParamBlock $target.Body.ParamBlock
        }
        if (@($gaps).Count -eq 0) { continue }

        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = "[AN-013] $($target.Label) help: $(@($gaps) -join '; ')."
            Extent   = $target.Extent
            RuleName = 'Measure-AN013HelpComplete'
            Severity = 'Warning'
        }
    }
}

function Get-AN013HelpGap {
    <#
    .SYNOPSIS
        Lists what one readable help block is missing.

    .DESCRIPTION
        Returns one phrase per gap: each missing section, the parameters with no help
        entry, and the parameter entries that name no parameter. Returns nothing when
        the help is complete.

    .PARAMETER Help
        The help content PowerShell read from the script or function.

    .PARAMETER ParamBlock
        The param block of the script or function, or $null when it has none.

    .EXAMPLE
        $gaps = @(Get-AN013HelpGap -Help $node.GetHelpContent() -ParamBlock $body.ParamBlock)

    .OUTPUTS
        [string], one per gap.

    .NOTES
        Helper for Measure-AN013HelpComplete; not exported.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [System.Management.Automation.Language.CommentHelpInfo]$Help,

        [Parameter()]
        [AllowNull()]
        [System.Management.Automation.Language.ParamBlockAst]$ParamBlock
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ([string]::IsNullOrWhiteSpace($Help.Synopsis)) { 'no .SYNOPSIS' }
    if ([string]::IsNullOrWhiteSpace($Help.Description)) { 'no .DESCRIPTION' }
    if ($Help.Examples.Count -eq 0) { 'no .EXAMPLE' }
    if ([string]::IsNullOrWhiteSpace($Help.Notes)) { 'no .NOTES' }

    $names = @(if ($null -ne $ParamBlock) {
        $ParamBlock.Parameters | ForEach-Object { $PSItem.Name.VariablePath.UserPath }
    })
    $documented = @($Help.Parameters.Keys)

    $undocumented = @($names | Where-Object { $PSItem.ToUpperInvariant() -notin $documented })
    if ($undocumented.Count -gt 0) { "no .PARAMETER for $($undocumented -join ', ')" }

    $upperNames = @($names | ForEach-Object { $PSItem.ToUpperInvariant() })
    $stale = @($documented | Where-Object { $PSItem -notin $upperNames })
    if ($stale.Count -gt 0) { ".PARAMETER names no parameter: $($stale -join ', ')" }
}

Export-ModuleMember -Function 'Measure-AN013HelpComplete'
