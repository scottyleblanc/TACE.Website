#Requires -Version 7.6

. (Join-Path -Path $PSScriptRoot -ChildPath '..' -AdditionalChildPath 'Lib', 'Get-GateRuleTarget.ps1')

function Measure-AN011CmdletBindingDeclared {
    <#
    .SYNOPSIS
        Rule AN-011: every script and function is an advanced one.

    .DESCRIPTION
        Reports a script with a param block, or a function, whose param block has no
        [CmdletBinding()] attribute, or that has no param block at all. A function
        defined inside another function or inside such a script is skipped. Custom
        PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        script or function without [CmdletBinding()].

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
        $paramBlock = $target.Body.ParamBlock
        $declared = $null -ne $paramBlock -and @($paramBlock.Attributes | Where-Object {
            ($PSItem.TypeName.Name -split '\.')[-1] -in @('CmdletBinding', 'CmdletBindingAttribute')
        }).Count -gt 0
        if ($declared) { continue }

        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = "[AN-011] $($target.Label) does not declare [CmdletBinding()]. Add it above the param block."
            Extent   = $target.Extent
            RuleName = 'Measure-AN011CmdletBindingDeclared'
            Severity = 'Warning'
        }
    }
}

Export-ModuleMember -Function 'Measure-AN011CmdletBindingDeclared'
