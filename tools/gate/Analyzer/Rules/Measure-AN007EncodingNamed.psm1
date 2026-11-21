#Requires -Version 7.6

function Measure-AN007EncodingNamed {
    <#
    .SYNOPSIS
        Rule AN-007: every file write names its encoding.

    .DESCRIPTION
        Reports a file write that does not name an encoding:
          - Set-Content, Add-Content, Out-File, Export-Csv, Export-Clixml, and Tee-Object
            writing to a file, without -Encoding. A splatted call passes when the splatted
            hashtable has an Encoding key, or is given one, anywhere in the file
          - [System.IO.File]::WriteAllText, WriteAllLines, AppendAllText and AppendAllLines
            with no encoding argument
          - output redirection (> or >>) to anything but $null
        Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        write without an encoding.

    .NOTES
        Returns diagnostic records, not the Success/Data/Message object: this is the
        contract PSScriptAnalyzer requires of a rule.
        Limitation: New-Item -Value and stream writers are not checked. The splat check
        looks for an Encoding key by variable name anywhere in the file, not along the
        path the code runs.
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

    $writeCommands = @('Set-Content', 'Add-Content', 'Out-File', 'Export-Csv', 'Export-Clixml', 'Tee-Object')
    $fileMethods   = @('WriteAllText', 'WriteAllLines', 'AppendAllText', 'AppendAllLines')

    # Variables given an Encoding key anywhere in the file: $p = @{ Encoding = ... },
    # $p.Encoding = ..., or $p['Encoding'] = ...
    $encodingSplats = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $assignments = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.AssignmentStatementAst]
    }, $true))
    foreach ($assignment in $assignments) {
        $left = $assignment.Left
        if ($left -is [System.Management.Automation.Language.VariableExpressionAst]) {
            $hashtables = @($assignment.Right.FindAll({
                param([System.Management.Automation.Language.Ast]$Node)
                $Node -is [System.Management.Automation.Language.HashtableAst]
            }, $false))
            foreach ($hashtable in $hashtables) {
                $keys = @($hashtable.KeyValuePairs | ForEach-Object { $PSItem.Item1.Extent.Text.Trim('''', '"') })
                if ($keys -contains 'Encoding') { $null = $encodingSplats.Add($left.VariablePath.UserPath) }
            }
        }
        elseif ($left -is [System.Management.Automation.Language.MemberExpressionAst] -and
            $left.Expression -is [System.Management.Automation.Language.VariableExpressionAst] -and
            $left.Member.Extent.Text.Trim('''', '"') -eq 'Encoding') {
            $null = $encodingSplats.Add($left.Expression.VariablePath.UserPath)
        }
        elseif ($left -is [System.Management.Automation.Language.IndexExpressionAst] -and
            $left.Target -is [System.Management.Automation.Language.VariableExpressionAst] -and
            $left.Index.Extent.Text.Trim('''', '"') -eq 'Encoding') {
            $null = $encodingSplats.Add($left.Target.VariablePath.UserPath)
        }
    }

    $hits = [System.Collections.Generic.List[object]]::new()

    $commands = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.CommandAst]
    }, $true))
    foreach ($command in $commands) {
        $name = $command.GetCommandName()
        if ($null -eq $name -or $name -notin $writeCommands) { continue }

        $parameterNames = @($command.CommandElements | Where-Object {
            $PSItem -is [System.Management.Automation.Language.CommandParameterAst]
        } | ForEach-Object { $PSItem.ParameterName })

        if ($name -eq 'Tee-Object' -and @($parameterNames | Where-Object { $PSItem -in @('FilePath', 'LiteralPath', 'Append') }).Count -eq 0) { continue }

        $named = @($parameterNames | Where-Object {
            $PSItem.Length -ge 3 -and 'Encoding'.StartsWith($PSItem, [System.StringComparison]::OrdinalIgnoreCase)
        }).Count -gt 0

        $splatted = @($command.CommandElements | Where-Object {
            $PSItem -is [System.Management.Automation.Language.VariableExpressionAst] -and
            $PSItem.Splatted -and
            $encodingSplats.Contains($PSItem.VariablePath.UserPath)
        }).Count -gt 0

        if (-not $named -and -not $splatted) { $hits.Add($command) }
    }

    $calls = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -and
            $Node.Static -and
            $Node.Expression -is [System.Management.Automation.Language.TypeExpressionAst]
    }, $true))
    foreach ($call in $calls) {
        $typeName = $call.Expression.TypeName.Name
        if ($typeName -notin @('System.IO.File', 'IO.File')) { continue }
        $member = $call.Member.Extent.Text
        if ($member -notin $fileMethods) { continue }
        if (@($call.Arguments).Count -lt 3) { $hits.Add($call) }
    }

    $redirections = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.FileRedirectionAst]
    }, $true))
    foreach ($redirection in $redirections) {
        $location = $redirection.Location
        $toNull = $location -is [System.Management.Automation.Language.VariableExpressionAst] -and
            $location.VariablePath.UserPath -eq 'null'
        if (-not $toNull) { $hits.Add($redirection) }
    }

    foreach ($hit in $hits) {
        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = '[AN-007] File write without a named encoding. Pass -Encoding UTF8, or an encoding argument to the .NET method.'
            Extent   = $hit.Extent
            RuleName = 'Measure-AN007EncodingNamed'
            Severity = 'Warning'
        }
    }
}

Export-ModuleMember -Function 'Measure-AN007EncodingNamed'
