#Requires -Version 7.6

function Measure-AN012SuppressionJustified {
    <#
    .SYNOPSIS
        Rule AN-012: every analyzer suppression says why.

    .DESCRIPTION
        Reports a SuppressMessage or SuppressMessageAttribute attribute, in any namespace
        form, that has no Justification argument or whose Justification is an empty or
        blank string. Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        suppression without a justification.

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

    $suppressions = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.AttributeAst] -and
            ($Node.TypeName.Name -split '\.')[-1] -in @('SuppressMessage', 'SuppressMessageAttribute')
    }, $true))

    foreach ($suppression in $suppressions) {
        $justification = @($suppression.NamedArguments | Where-Object { $PSItem.ArgumentName -eq 'Justification' })
        $justified = $justification.Count -gt 0 -and
            $justification[0].Argument -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
            -not [string]::IsNullOrWhiteSpace($justification[0].Argument.Value)
        if ($justified) { continue }

        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = "[AN-012] A suppression has no Justification. Add Justification = '<why>'."
            Extent   = $suppression.Extent
            RuleName = 'Measure-AN012SuppressionJustified'
            Severity = 'Warning'
        }
    }
}

Export-ModuleMember -Function 'Measure-AN012SuppressionJustified'
