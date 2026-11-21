#Requires -Version 7.6

function Measure-AN006PathWithJoinPath {
    <#
    .SYNOPSIS
        Rule AN-006: paths are built with Join-Path, never by joining strings with \ or /.

    .DESCRIPTION
        Reports three ways of building a path from strings:
          - a double-quoted string in which a variable or subexpression sits directly
            against a \ or / separator, such as "$installRoot\bin", when the string is
            used as a path: passed to a parameter named like a path (-Path,
            -Destination, ...), passed first and positionally to a path cmdlet
            (Test-Path, Get-Content, ...), assigned to a variable named like a path
            ($binPath, $installRoot, ...), or the value of a hashtable key named like
            a path
          - + where one side is a string constant that starts or ends with \ or /
          - -join with a \ or / separator
        A string containing :// is a URL, not a path, and is not reported. Messages and
        labels that show a path to a reader are not paths and are not reported. Custom
        PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        string-built path.

    .NOTES
        Returns diagnostic records, not the Success/Data/Message object: this is the
        contract PSScriptAnalyzer requires of a rule.
        Limitation: a heuristic. A double-quoted path is found only in the contexts
        above, so one stored in a variable with a name that does not look like a path,
        or passed to a .NET method, is missed. A path built with -f or [string]::Concat
        is not detected. A deliberate -join '/' (a Linux path built on any platform)
        carries a suppression with the reason.
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

    # A variable or the close of a subexpression directly before a separator and a
    # path character, or a path character and a separator directly before a variable.
    $adjacent = '(\$(\{[^}]+\}|[\w:]+)|\))[\\/][\w.$]|[\w.][\\/]\$'

    # Names that mark a value as a path: parameters, variables and splat keys.
    $pathName = '(?i)(path|destination|directory|dir|folder|file|home|root|base)$'

    # Cmdlets whose first positional parameter is a path.
    $pathCommand = '(?i)^(\w+-(Item|ItemProperty|Content|ChildItem|Path|Location|Module)|Out-File|Export-Csv|Export-Clixml)$'

    # True when a double-quoted string is used as a path: the argument of a path
    # parameter, the first positional argument of a path cmdlet, the value assigned to
    # a path-named variable, or the value of a path-named key in a hashtable.
    $isPathContext = {
        param([System.Management.Automation.Language.Ast]$Node)

        $parent = $Node.Parent
        if ($parent -is [System.Management.Automation.Language.CommandParameterAst]) {
            return $parent.ParameterName -match $pathName
        }
        if ($parent -is [System.Management.Automation.Language.CommandAst]) {
            $elements = @($parent.CommandElements)
            $index = [array]::IndexOf($elements, $Node)
            if ($index -gt 0 -and $elements[$index - 1] -is [System.Management.Automation.Language.CommandParameterAst]) {
                return $elements[$index - 1].ParameterName -match $pathName
            }
            $name = $parent.GetCommandName()
            return $index -eq 1 -and $null -ne $name -and $name -match $pathCommand
        }

        # Climb through the wrappers a value sits in to the statement that uses it.
        $child = $Node
        while ($parent -is [System.Management.Automation.Language.CommandExpressionAst] -or
            $parent -is [System.Management.Automation.Language.PipelineAst] -or
            $parent -is [System.Management.Automation.Language.ParenExpressionAst]) {
            $child = $parent
            $parent = $parent.Parent
        }
        if ($parent -is [System.Management.Automation.Language.AssignmentStatementAst] -and
            $parent.Right -eq $child -and
            $parent.Left -is [System.Management.Automation.Language.VariableExpressionAst]) {
            return $parent.Left.VariablePath.UserPath -match $pathName
        }
        if ($parent -is [System.Management.Automation.Language.HashtableAst]) {
            $pair = @($parent.KeyValuePairs | Where-Object { $PSItem.Item2 -eq $child })
            return $pair.Count -gt 0 -and $pair[0].Item1.Extent.Text.Trim('''', '"') -match $pathName
        }
        return $false
    }

    $strings = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.ExpandableStringExpressionAst] -and
            $Node.Extent.Text -notmatch '://' -and
            $Node.Extent.Text -match $adjacent
    }, $true))
    $stringHits = @($strings | Where-Object { & $isPathContext $PSItem })

    $operatorHits = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)

        if ($Node -is [System.Management.Automation.Language.BinaryExpressionAst]) {
            $sides = @($Node.Left, $Node.Right) | Where-Object {
                $PSItem -is [System.Management.Automation.Language.StringConstantExpressionAst]
            }
            if ($Node.Operator -eq [System.Management.Automation.Language.TokenKind]::Plus) {
                return @($sides | Where-Object {
                    $PSItem.Value -notmatch '://' -and $PSItem.Value -match '^[\\/]|[\\/]$'
                }).Count -gt 0
            }
            if ($Node.Operator -eq [System.Management.Automation.Language.TokenKind]::Join -and
                $Node.Right -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
                return $Node.Right.Value -in @('\', '/')
            }
        }

        return $false
    }, $true))

    foreach ($hit in @($stringHits) + @($operatorHits)) {
        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = '[AN-006] Path built by joining strings with a separator. Use Join-Path.'
            Extent   = $hit.Extent
            RuleName = 'Measure-AN006PathWithJoinPath'
            Severity = 'Warning'
        }
    }
}

Export-ModuleMember -Function 'Measure-AN006PathWithJoinPath'
