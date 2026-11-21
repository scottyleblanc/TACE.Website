#Requires -Version 7.6

function Get-GateRuleTarget {
    <#
    .SYNOPSIS
        Lists the scripts and functions that rules AN-010, AN-011 and AN-013 check.

    .DESCRIPTION
        Returns the file's root script block when it has a param block, and every
        function that is not defined inside another function or inside such a script. A
        function nested that way runs in a child scope of one that is checked, so it
        inherits strict mode and the error preference, and it is not a command anyone
        calls by name. Class methods and constructors are not functions here.

    .PARAMETER ScriptBlockAst
        The root script block of the file.

    .EXAMPLE
        $targets = @(Get-GateRuleTarget -ScriptBlockAst $ScriptBlockAst)

    .OUTPUTS
        PSCustomObject with Label (for the finding message), Body (the script block whose
        param block and statements are checked), Node (the node whose help is read) and
        Extent (where the finding is reported).

    .NOTES
        Dot-sourced by the rule modules. Not a rule: PSScriptAnalyzer runs only the
        exported Measure-* functions.
    #>
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNull()]
        [System.Management.Automation.Language.ScriptBlockAst]$ScriptBlockAst
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ($null -ne $ScriptBlockAst.ParamBlock) {
        [PSCustomObject]@{
            Label  = 'The script'
            Body   = $ScriptBlockAst
            Node   = $ScriptBlockAst
            Extent = $ScriptBlockAst.ParamBlock.Extent
        }
    }

    $functions = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $Node.Parent -isnot [System.Management.Automation.Language.FunctionMemberAst]
    }, $true))

    foreach ($function in $functions) {
        $covered = $false
        for ($node = $function.Parent; $null -ne $node; $node = $node.Parent) {
            $isFunction = $node -is [System.Management.Automation.Language.FunctionDefinitionAst]
            $isScript   = $node -eq $ScriptBlockAst -and $null -ne $ScriptBlockAst.ParamBlock
            if ($isFunction -or $isScript) {
                $covered = $true
                break
            }
        }
        if ($covered) { continue }

        [PSCustomObject]@{
            Label  = "Function '$($function.Name)'"
            Body   = $function.Body
            Node   = $function
            Extent = $function.Extent
        }
    }
}
