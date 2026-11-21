#Requires -Version 7.6

function Measure-AN002OutputTypeDeclared {
    <#
    .SYNOPSIS
        Rule AN-002: every function declares its output type.

    .DESCRIPTION
        Reports a function whose param block has no [OutputType()] attribute, or that has
        no param block at all. Class methods and constructors are skipped: their return
        type is part of their signature, and [OutputType()] cannot be applied to them.
        Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        function without [OutputType()].

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

    $functions = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $Node.Parent -isnot [System.Management.Automation.Language.FunctionMemberAst]
    }, $true))

    foreach ($function in $functions) {
        $paramBlock = $function.Body.ParamBlock
        $declared = $null -ne $paramBlock -and @($paramBlock.Attributes | Where-Object {
            ($PSItem.TypeName.Name -split '\.')[-1] -in @('OutputType', 'OutputTypeAttribute')
        }).Count -gt 0

        if (-not $declared) {
            [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
                Message  = "[AN-002] Function '$($function.Name)' does not declare its output type. Add [OutputType()] below [CmdletBinding()]."
                Extent   = $function.Extent
                RuleName = 'Measure-AN002OutputTypeDeclared'
                Severity = 'Warning'
            }
        }
    }
}

Export-ModuleMember -Function 'Measure-AN002OutputTypeDeclared'
