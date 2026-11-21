#Requires -Version 7.6

function Measure-AN015PublicParameterValidated {
    <#
    .SYNOPSIS
        Rule AN-015: every parameter of a public function has a [Validate*] attribute,
        except switches and credential types.

    .DESCRIPTION
        Applies to files under a folder named Public, at any depth. Reports a parameter
        of a function defined at the top level of the file that has no attribute named
        Validate*. Parameters typed [switch], [SecureString] or [PSCredential] are exempt:
        a switch has only two values, and a credential type is checked by its own type. A
        parameter with no type is reported by AN-004, not here (DEC-015). Custom
        PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        parameter without validation.

    .NOTES
        Returns diagnostic records, not the Success/Data/Message object: this is the
        contract PSScriptAnalyzer requires of a rule.
        Limitation: "public" is read from the file's path, so code analyzed without a path
        (Invoke-ScriptAnalyzer -ScriptDefinition) is never checked by this rule.
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
    if ([string]::IsNullOrEmpty($file) -or $file -notmatch '[\\/]Public[\\/]') { return }

    $exemptTypes = @('switch', 'switchparameter', 'securestring', 'pscredential')

    $functions = @($ScriptBlockAst.EndBlock.Statements | Where-Object {
        $PSItem -is [System.Management.Automation.Language.FunctionDefinitionAst]
    })

    foreach ($function in $functions) {
        if ($null -eq $function.Body.ParamBlock) { continue }

        foreach ($parameter in $function.Body.ParamBlock.Parameters) {
            $typeConstraints = @($parameter.Attributes | Where-Object {
                $PSItem -is [System.Management.Automation.Language.TypeConstraintAst]
            })
            if ($typeConstraints.Count -eq 0) { continue }

            $typeName = ($typeConstraints[0].TypeName.Name -split '\.')[-1]
            if ($typeName -in $exemptTypes) { continue }

            $validated = @($parameter.Attributes | Where-Object {
                $PSItem -is [System.Management.Automation.Language.AttributeAst] -and
                ($PSItem.TypeName.Name -split '\.')[-1] -like 'Validate*'
            }).Count -gt 0
            if ($validated) { continue }

            [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
                Message  = "[AN-015] Public parameter '$($parameter.Name.VariablePath.UserPath)' of '$($function.Name)' has no [Validate*] attribute."
                Extent   = $parameter.Extent
                RuleName = 'Measure-AN015PublicParameterValidated'
                Severity = 'Warning'
            }
        }
    }
}

Export-ModuleMember -Function 'Measure-AN015PublicParameterValidated'
