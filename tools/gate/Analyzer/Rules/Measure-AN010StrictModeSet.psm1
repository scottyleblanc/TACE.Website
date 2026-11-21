#Requires -Version 7.6

. (Join-Path -Path $PSScriptRoot -ChildPath '..' -AdditionalChildPath 'Lib', 'Get-GateRuleTarget.ps1')

function Measure-AN010StrictModeSet {
    <#
    .SYNOPSIS
        Rule AN-010: every script and function sets strict mode and stops on errors.

    .DESCRIPTION
        Reports a script with a param block, or a function, whose body does not hold both
        Set-StrictMode -Version Latest and $ErrorActionPreference = 'Stop' as statements
        of its own (not inside a try, an if or a nested block). A function defined inside
        another function or inside such a script is skipped: it inherits both settings
        from the scope it runs in. Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        script or function missing either setting.

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
        $body = $target.Body
        $statements = @(foreach ($block in @($body.BeginBlock, $body.ProcessBlock, $body.EndBlock)) {
            if ($null -ne $block) { $block.Statements }
        })

        $hasStrictMode = @($statements | Where-Object { Test-AN010StrictModeStatement -Statement $PSItem }).Count -gt 0
        $hasStop       = @($statements | Where-Object { Test-AN010StopStatement -Statement $PSItem }).Count -gt 0
        if ($hasStrictMode -and $hasStop) { continue }

        $missing = @(
            if (-not $hasStrictMode) { 'Set-StrictMode -Version Latest' }
            if (-not $hasStop) { "`$ErrorActionPreference = 'Stop'" }
        ) -join ' and '
        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = "[AN-010] $($target.Label) does not set $missing in its body."
            Extent   = $target.Extent
            RuleName = 'Measure-AN010StrictModeSet'
            Severity = 'Warning'
        }
    }
}

function Test-AN010StrictModeStatement {
    <#
    .SYNOPSIS
        Tells whether one statement is Set-StrictMode -Version Latest.

    .DESCRIPTION
        Accepts the argument as a separate token (-Version Latest) or joined to the
        parameter (-Version:Latest).

    .PARAMETER Statement
        One statement from a script block's begin, process or end block.

    .EXAMPLE
        Test-AN010StrictModeStatement -Statement $statement

    .OUTPUTS
        [bool]

    .NOTES
        Helper for Measure-AN010StrictModeSet; not exported.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)]
        [System.Management.Automation.Language.StatementAst]$Statement
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ($Statement -isnot [System.Management.Automation.Language.PipelineAst]) { return $false }
    if ($Statement.PipelineElements.Count -ne 1) { return $false }
    $command = $Statement.PipelineElements[0]
    if ($command -isnot [System.Management.Automation.Language.CommandAst]) { return $false }
    if ($command.GetCommandName() -ne 'Set-StrictMode') { return $false }

    $elements = @($command.CommandElements)
    for ($index = 1; $index -lt $elements.Count; $index++) {
        $element = $elements[$index]
        if ($element -isnot [System.Management.Automation.Language.CommandParameterAst]) { continue }
        if ($element.ParameterName -ne 'Version') { continue }
        $argument = if ($null -ne $element.Argument) {
            $element.Argument
        } elseif ($index + 1 -lt $elements.Count) {
            $elements[$index + 1]
        } else {
            $null
        }
        return ($argument -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
            $argument.Value -eq 'Latest')
    }
    return $false
}

function Test-AN010StopStatement {
    <#
    .SYNOPSIS
        Tells whether one statement is $ErrorActionPreference = 'Stop'.

    .DESCRIPTION
        Accepts the value quoted or bare, in either quote style.

    .PARAMETER Statement
        One statement from a script block's begin, process or end block.

    .EXAMPLE
        Test-AN010StopStatement -Statement $statement

    .OUTPUTS
        [bool]

    .NOTES
        Helper for Measure-AN010StrictModeSet; not exported.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)]
        [System.Management.Automation.Language.StatementAst]$Statement
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ($Statement -isnot [System.Management.Automation.Language.AssignmentStatementAst]) { return $false }
    if ($Statement.Operator -ne [System.Management.Automation.Language.TokenKind]::Equals) { return $false }
    $left = $Statement.Left
    if ($left -isnot [System.Management.Automation.Language.VariableExpressionAst]) { return $false }
    if ($left.VariablePath.UserPath -ne 'ErrorActionPreference') { return $false }

    $right = $Statement.Right
    if ($right -is [System.Management.Automation.Language.PipelineAst] -and $right.PipelineElements.Count -eq 1) {
        $right = $right.PipelineElements[0]
    }
    if ($right -is [System.Management.Automation.Language.CommandExpressionAst]) {
        $right = $right.Expression
    }
    return ($right -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
        $right.Value -eq 'Stop')
}

Export-ModuleMember -Function 'Measure-AN010StrictModeSet'
