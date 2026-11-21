#Requires -Version 7.6

function Measure-AN016RequiresVersion {
    <#
    .SYNOPSIS
        Rule AN-016: every script and module file declares the PowerShell version it
        needs.

    .DESCRIPTION
        Reports a .ps1 or .psm1 file, or code analyzed without a path, that has no
        #Requires -Version statement. Any version passes: the minimum is the
        repository's choice, not the kit's (DEC-015). A .psd1 data file is skipped,
        because #Requires does not apply to it. Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per file
        without #Requires -Version.

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
    if (-not [string]::IsNullOrEmpty($file) -and [System.IO.Path]::GetExtension($file) -eq '.psd1') { return }

    $requirements = $ScriptBlockAst.ScriptRequirements
    if ($null -ne $requirements -and $null -ne $requirements.RequiredPSVersion) { return }

    [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
        Message  = '[AN-016] The file has no #Requires -Version statement. Add one as its first line, for example #Requires -Version 7.6.'
        Extent   = $ScriptBlockAst.Extent
        RuleName = 'Measure-AN016RequiresVersion'
        Severity = 'Warning'
    }
}

Export-ModuleMember -Function 'Measure-AN016RequiresVersion'
