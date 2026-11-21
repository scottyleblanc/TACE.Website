#Requires -Version 7.6

function Measure-AN018NoRegistryWrite {
    <#
    .SYNOPSIS
        Rule AN-018: code does not change the Windows registry.

    .DESCRIPTION
        Reports each of these:
          - A provider cmdlet that changes an item or property (Set-, New-, Remove-,
            Rename-, Clear-, Copy- or Move-Item and -ItemProperty, and Set-Item), or an
            alias of one, given a literal registry path: a drive such as HKLM: or HKCU:,
            or a Registry:: path.
          - A call to CreateSubKey, DeleteSubKey, DeleteSubKeyTree or DeleteValue on
            any object; SetValue on the [Microsoft.Win32.Registry] type; and SetValue
            or SetAccessControl in a file that names a registry type, because both
            names are also used outside the registry.
          - OpenSubKey asked for write access, such as OpenSubKey(name, $true).
          - reg.exe with add, delete, import, copy, restore, load or unload, and
            regedit or regini with any argument.
        Reading the registry is not reported. A change that is intended carries a
        SuppressMessageAttribute with a Justification (AN-012), so the exception is
        recorded where it is made (DEC-019). Custom PSScriptAnalyzer rule.

    .PARAMETER ScriptBlockAst
        The script block PSScriptAnalyzer passes in. The rule runs once per file, on the
        root script block, and ignores the nested ones it is also called for.

    .EXAMPLE
        Invoke-ScriptAnalyzer -Path .\source -Recurse -CustomRulePath .\tools\gate\Analyzer\Rules\*.psm1

    .OUTPUTS
        Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord, one per
        registry change.

    .NOTES
        Returns diagnostic records, not the Success/Data/Message object: this is the
        contract PSScriptAnalyzer requires of a rule.
        Limitation: the rule reads source text, not values at run time. A path held in a
        variable, a relative path after Set-Location HKLM:, a command built as a string
        (Invoke-Expression, pwsh -Command), and WMI or CIM calls to StdRegProv are not
        seen; review covers them.
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

    $registryPath = '(?i)^\s*(Microsoft\.PowerShell\.Core\\)?Registry::|^\s*HK(LM|CU|CR|U|CC):'
    $changeCmdlets = @(
        'Set-Item', 'New-Item', 'Remove-Item', 'Rename-Item', 'Clear-Item', 'Copy-Item', 'Move-Item',
        'Set-ItemProperty', 'New-ItemProperty', 'Remove-ItemProperty', 'Rename-ItemProperty',
        'Clear-ItemProperty', 'Copy-ItemProperty', 'Move-ItemProperty'
    )
    $regVerbs   = @('add', 'delete', 'import', 'copy', 'restore', 'load', 'unload')
    $keyChanges = @('CreateSubKey', 'DeleteSubKey', 'DeleteSubKeyTree', 'DeleteValue')

    # SetValue and SetAccessControl are also used on arrays and files, so they count only
    # where a registry type is named.
    $namesRegistryType = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        ($Node -is [System.Management.Automation.Language.TypeExpressionAst] -or
            $Node -is [System.Management.Automation.Language.TypeConstraintAst]) -and
            $Node.TypeName.FullName -match '(?i)(^|\.)Registry(Key)?$'
    }, $true)).Count -gt 0

    $resolved = @{}

    function ConvertTo-RegistryRecord {
        [OutputType([Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord])]
        param([string]$What, [System.Management.Automation.Language.IScriptExtent]$Extent)
        [Microsoft.Windows.PowerShell.ScriptAnalyzer.Generic.DiagnosticRecord]@{
            Message  = "[AN-018] $What changes the Windows registry. Remove it, or, if the change is intended, suppress AN-018 on the function with a Justification that says why."
            Extent   = $Extent
            RuleName = 'Measure-AN018NoRegistryWrite'
            Severity = 'Warning'
        }
    }

    $commands = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.CommandAst]
    }, $true))

    foreach ($command in $commands) {
        $name = $command.GetCommandName()
        if ([string]::IsNullOrEmpty($name)) { continue }

        $strings = @($command.CommandElements | Select-Object -Skip 1 | Where-Object {
            $PSItem -is [System.Management.Automation.Language.StringConstantExpressionAst] -or
            $PSItem -is [System.Management.Automation.Language.ExpandableStringExpressionAst]
        } | ForEach-Object { [string]$PSItem.Value })

        $leaf = ([System.IO.Path]::GetFileNameWithoutExtension($name)).ToLowerInvariant()
        if ($leaf -eq 'reg') {
            if ($strings.Count -gt 0 -and $strings[0].ToLowerInvariant() -in $regVerbs) {
                ConvertTo-RegistryRecord -What "'reg $($strings[0].ToLowerInvariant())'" -Extent $command.Extent
            }
            continue
        }
        if ($leaf -in @('regedit', 'regini')) {
            if ($command.CommandElements.Count -gt 1) {
                ConvertTo-RegistryRecord -What "'$leaf' with arguments" -Extent $command.Extent
            }
            continue
        }

        if (-not $resolved.ContainsKey($name)) {
            $found = Get-Command -Name $name -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($null -ne $found -and $found.CommandType -eq 'Alias') { $found = $found.ResolvedCommand }
            $resolved[$name] = if ($null -ne $found -and $found.CommandType -eq 'Cmdlet') { $found.Name } else { $name }
        }
        $cmdlet = $resolved[$name]
        if ($cmdlet -notin $changeCmdlets) { continue }

        if (@($strings | Where-Object { $PSItem -match $registryPath }).Count -gt 0) {
            ConvertTo-RegistryRecord -What "'$cmdlet' on a registry path" -Extent $command.Extent
        }
    }

    $calls = @($ScriptBlockAst.FindAll({
        param([System.Management.Automation.Language.Ast]$Node)
        $Node -is [System.Management.Automation.Language.InvokeMemberExpressionAst]
    }, $true))

    foreach ($call in $calls) {
        $member = $call.Member.Extent.Text.Trim("'", '"')
        $arguments = @($call.Arguments)

        $isChange = $member -in $keyChanges
        if (-not $isChange -and $member -eq 'SetAccessControl') { $isChange = $namesRegistryType }
        if (-not $isChange -and $member -eq 'SetValue') {
            $onRegistryType = $call.Expression -is [System.Management.Automation.Language.TypeExpressionAst] -and
                $call.Expression.TypeName.FullName -match '(?i)(^|\.)Registry$'
            $isChange = $onRegistryType -or $namesRegistryType
        }
        if (-not $isChange -and $member -eq 'OpenSubKey' -and $arguments.Count -ge 2) {
            $isChange = $arguments[1].Extent.Text -match '(?i)^\$true$|ReadWriteSubTree|WriteKey|FullControl'
        }
        if ($isChange) {
            ConvertTo-RegistryRecord -What "'$member'" -Extent $call.Extent
        }
    }

}

Export-ModuleMember -Function 'Measure-AN018NoRegistryWrite'
