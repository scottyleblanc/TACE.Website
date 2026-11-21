#Requires -Version 7.6

function Measure-AN017VerboseLabelled {
    <#
    .SYNOPSIS
        Rule AN-017: every verbose message starts with the name of the command that
        writes it, in square brackets.

    .DESCRIPTION
        Reports a Write-Verbose call whose message, given as a literal string, an
        expandable string or the left side of a -f expression, does not start with
        [Name]. Name is the enclosing function, or any function that encloses it, so a
        helper defined inside a function may use either name. Inside a class method or
        constructor, the class's name is accepted too: the class is what callers use and
        what an operator searches a log for. A call outside every
        function uses the script's file name without its extension; code analyzed
        without a path is then skipped. A message held in a variable, or built some
        other way, is not checked (DEC-016). Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        verbose message without the label.

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

    $file = $ScriptBlockAst.Extent.File
    $scriptName = if ([string]::IsNullOrEmpty($file)) { $null } else { [System.IO.Path]::GetFileNameWithoutExtension($file) }

    $calls = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.CommandAst] -and $Node.GetCommandName() -eq 'Write-Verbose'
    }, $true))

    foreach ($call in $calls) {
        # The message: the value of -Message, or the first positional argument.
        $message = $null
        $elements = @($call.CommandElements | Select-Object -Skip 1)
        for ($index = 0; $index -lt $elements.Count; $index++) {
            $element = $elements[$index]
            if ($element -is [System.Management.Automation.Language.CommandParameterAst]) {
                if ($element.ParameterName -like 'M*' -and 'Message' -like "$($element.ParameterName)*") {
                    $message = if ($null -ne $element.Argument) { $element.Argument } elseif ($index + 1 -lt $elements.Count) { $elements[$index + 1] } else { $null }
                    break
                }
                # Another parameter: skip its value when it is given separately.
                if ($null -eq $element.Argument -and $element.ParameterName -notin @('Verbose', 'Debug')) { $index++ }
                continue
            }
            if ($null -eq $message) { $message = $element }
        }
        if ($null -eq $message) { continue }

        if ($message -is [System.Management.Automation.Language.BinaryExpressionAst] -and
            $message.Operator -eq [System.Management.Automation.Language.TokenKind]::Format) {
            $message = $message.Left
        }
        $isString = $message -is [System.Management.Automation.Language.StringConstantExpressionAst] -or
            $message -is [System.Management.Automation.Language.ExpandableStringExpressionAst]
        if (-not $isString) { continue }

        # The names the label may use: every enclosing function or method, and the class
        # that holds a method; then, outside all of them, the script.
        $names = [System.Collections.Generic.List[string]]::new()
        for ($node = $call.Parent; $null -ne $node; $node = $node.Parent) {
            if ($node -is [System.Management.Automation.Language.FunctionDefinitionAst]) { $names.Add($node.Name) }
            if ($node -is [System.Management.Automation.Language.FunctionMemberAst] -and -not $names.Contains($node.Name)) { $names.Add($node.Name) }
            if ($node -is [System.Management.Automation.Language.TypeDefinitionAst]) { $names.Add($node.Name) }
        }
        if ($names.Count -eq 0) {
            if ($null -eq $scriptName) { continue }
            $names.Add($scriptName)
        }

        $text = [string]$message.Value
        $labelled = @($names | Where-Object { $text.StartsWith("[$PSItem]", [System.StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
        if ($labelled) { continue }

        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = "[AN-017] Verbose message does not start with [$($names[0])]. Start it with the name of the command that writes it, for example '[$($names[0])] Reading the config.'"
            Extent   = $call.Extent
            RuleName = 'Measure-AN017VerboseLabelled'
            Severity = 'Warning'
        }
    }
}

Export-ModuleMember -Function 'Measure-AN017VerboseLabelled'
