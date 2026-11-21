#Requires -Version 7.6

# Rules AN-002 to AN-018: each custom analyzer rule reports its defect and stays quiet
# on the corrected code. A rule that never fires would let GK03 pass anything.

BeforeDiscovery {
    $script:cases = @(
        @{
            Rule = 'Measure-AN002OutputTypeDeclared'
            Bad  = 'function Get-Thing { [CmdletBinding()] param([string]$Name) $Name }'
            Good = 'function Get-Thing { [CmdletBinding()] [OutputType([string])] param([string]$Name) $Name }'
        }
        @{
            Rule = 'Measure-AN003PlatformFromAutomaticVariable'
            Bad  = 'if ($env:OS -eq "Windows_NT") { "win" }'
            Good = 'if ($IsWindows) { "win" }'
        }
        @{
            Rule = 'Measure-AN004ParameterTyped'
            Bad  = 'function Get-Thing { [OutputType([string])] param($Name) $Name }'
            Good = 'function Get-Thing { [OutputType([string])] param([string]$Name) $Name }'
        }
        @{
            Rule = 'Measure-AN005NoLineContinuation'
            Bad  = "Get-ChildItem -Path . ``" + [System.Environment]::NewLine + "    -File"
            Good = '$params = @{ Path = "."; File = $true }; Get-ChildItem @params'
        }
        @{
            Rule = 'Measure-AN006PathWithJoinPath'
            Bad  = '$binPath = "$root\bin"'
            Good = '$binPath = Join-Path -Path $root -ChildPath "bin"'
        }
        @{
            Rule = 'Measure-AN007EncodingNamed'
            Bad  = 'Set-Content -Path $target -Value "x"'
            Good = 'Set-Content -Path $target -Value "x" -Encoding UTF8'
        }
        @{
            Rule = 'Measure-AN008UsePSItem'
            Bad  = '1..3 | ForEach-Object { $_ * 2 }'
            Good = '1..3 | ForEach-Object { $PSItem * 2 }'
        }
        @{
            Rule = 'Measure-AN009NoEmoji'
            Bad  = 'Write-Output "done ' + [char]::ConvertFromUtf32(0x2705) + '"'
            Good = 'Write-Output "[INFO] done"'
        }
        @{
            Rule = 'Measure-AN010StrictModeSet'
            Bad  = 'function Get-Thing { [CmdletBinding()] param([string]$Name) $Name }'
            Good = "function Get-Thing { [CmdletBinding()] param([string]`$Name) Set-StrictMode -Version Latest; `$ErrorActionPreference = 'Stop'; `$Name }"
        }
        @{
            Rule = 'Measure-AN011CmdletBindingDeclared'
            Bad  = 'function Get-Thing { param([string]$Name) $Name }'
            Good = 'function Get-Thing { [CmdletBinding()] param([string]$Name) $Name }'
        }
        @{
            Rule = 'Measure-AN012SuppressionJustified'
            Bad  = "function Get-Thing { [Diagnostics.CodeAnalysis.SuppressMessage('PSAvoidUsingWriteHost', '')] [CmdletBinding()] param() }"
            Good = "function Get-Thing { [Diagnostics.CodeAnalysis.SuppressMessage('PSAvoidUsingWriteHost', '', Justification = 'Console output.')] [CmdletBinding()] param() }"
        }
        @{
            Rule = 'Measure-AN013HelpComplete'
            Bad  = 'function Get-Thing { [CmdletBinding()] param([string]$Name) $Name }'
            Good = @'
function Get-Thing {
    <#
    .SYNOPSIS
        Returns a name.
    .DESCRIPTION
        Returns the name it is given.
    .PARAMETER Name
        The name.
    .EXAMPLE
        Get-Thing -Name 'x'
    .NOTES
        None.
    #>
    [CmdletBinding()]
    param([string]$Name)
    $Name
}
'@
        }
        @{
            Rule = 'Measure-AN014WhatIfDecided'
            Bad  = 'function Remove-Thing { [CmdletBinding(SupportsShouldProcess)] param([string]$Path) Remove-Item -Path $Path }'
            Good = 'function Remove-Thing { [CmdletBinding(SupportsShouldProcess)] param([string]$Path) if ($PSCmdlet.ShouldProcess($Path, "Remove")) { Remove-Item -Path $Path } }'
        }
        @{
            Rule = 'Measure-AN016RequiresVersion'
            Bad  = 'Write-Output "x"'
            Good = "#Requires -Version 7.6`nWrite-Output 'x'"
        }
        @{
            Rule = 'Measure-AN017VerboseLabelled'
            Bad  = 'function Get-Thing { [CmdletBinding()] param() Write-Verbose "Reading." }'
            Good = 'function Get-Thing { [CmdletBinding()] param() Write-Verbose "[Get-Thing] Reading." }'
        }
        @{
            Rule = 'Measure-AN018NoRegistryWrite'
            Bad  = 'Set-ItemProperty -Path "HKLM:\SOFTWARE\Thing" -Name Level -Value 1'
            Good = 'Get-ItemProperty -Path "HKLM:\SOFTWARE\Thing" -Name Level'
        }
    )
}

BeforeAll {
    Import-Module -Name PSScriptAnalyzer -RequiredVersion 1.25.0
    $script:rulesPath = Join-Path -Path (Split-Path -Path $PSScriptRoot -Parent) -ChildPath 'Analyzer' -AdditionalChildPath 'Rules', '*.psm1'

    function Get-RuleHit {
        param([string]$Script, [string]$Rule)
        $params = @{
            ScriptDefinition = $Script
            CustomRulePath   = $script:rulesPath
        }
        @(Invoke-ScriptAnalyzer @params | Where-Object { $PSItem.RuleName -eq $Rule })
    }

    function Get-FileRuleHit {
        param([string]$RelativePath, [string]$Script, [string]$Rule)
        $path = Join-Path -Path $TestDrive -ChildPath $RelativePath
        $null = New-Item -Path (Split-Path -Path $path -Parent) -ItemType Directory -Force
        Set-Content -Path $path -Value $Script -Encoding UTF8
        $params = @{
            Path           = $path
            CustomRulePath = $script:rulesPath
        }
        @(Invoke-ScriptAnalyzer @params | Where-Object { $PSItem.RuleName -eq $Rule })
    }
}

Describe 'Custom analyzer rules' -Tag 'Static' {

    It '<Rule> reports the defect' -ForEach $script:cases {
        @(Get-RuleHit -Script $Bad -Rule $Rule).Count | Should -BeGreaterThan 0
    }

    It '<Rule> passes the corrected code' -ForEach $script:cases {
        @(Get-RuleHit -Script $Good -Rule $Rule).Count | Should -Be 0
    }

    It 'Measure-AN002OutputTypeDeclared skips class methods and constructors, and still reports a function beside them' {
        $script = 'class Thing { Thing() { } [string] Name() { return "x" } static [int] Twice([int] $a) { return $a * 2 } }' +
            [System.Environment]::NewLine + 'function Get-Thing { param([string]$Name) $Name }'
        $hits = @(Get-RuleHit -Script $script -Rule 'Measure-AN002OutputTypeDeclared')
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match "Function 'Get-Thing'"
    }

    It '<Rule> checks a script with a param block and skips a function inside it' -ForEach @(
        @{ Rule = 'Measure-AN010StrictModeSet' }
        @{ Rule = 'Measure-AN011CmdletBindingDeclared' }
        @{ Rule = 'Measure-AN013HelpComplete' }
    ) {
        $script = 'param([string]$Name)' + [System.Environment]::NewLine + 'function Get-Inner { $Name }'
        $hits = @(Get-RuleHit -Script $script -Rule $Rule)
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match 'The script'
    }

    It '<Rule> skips a function defined inside another function' -ForEach @(
        @{ Rule = 'Measure-AN010StrictModeSet' }
        @{ Rule = 'Measure-AN011CmdletBindingDeclared' }
        @{ Rule = 'Measure-AN013HelpComplete' }
    ) {
        $script = 'function Get-Outer { function Get-Inner { 1 } Get-Inner }'
        $hits = @(Get-RuleHit -Script $script -Rule $Rule)
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match "Function 'Get-Outer'"
    }

    It 'Measure-AN010StrictModeSet does not count settings made inside a try block' {
        $script = "function Get-Thing { [CmdletBinding()] param() try { Set-StrictMode -Version Latest; `$ErrorActionPreference = 'Stop' } finally { } }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN010StrictModeSet').Count | Should -Be 1
    }

    It 'Measure-AN012SuppressionJustified reports a blank Justification' {
        $script = "function Get-Thing { [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '', Justification = ' ')] [CmdletBinding()] param() }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN012SuppressionJustified').Count | Should -Be 1
    }

    It 'Measure-AN013HelpComplete reports help that a prose line starting with a dot makes unreadable' {
        $script = "function Get-Thing {`n    <#`n    .SYNOPSIS`n        Reads a file.`n    .DESCRIPTION`n        Reads a`n        .properties file.`n    .EXAMPLE`n        Get-Thing`n    .NOTES`n        None.`n    #>`n    [CmdletBinding()]`n    param()`n}"
        $hits = @(Get-RuleHit -Script $script -Rule 'Measure-AN013HelpComplete')
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match 'no help block that Get-Help can read'
    }

    It 'Measure-AN013HelpComplete reports script help written directly below #Requires' {
        $script = "#Requires -Version 7.0`n<#`n.SYNOPSIS`n    Runs.`n.DESCRIPTION`n    Runs.`n.EXAMPLE`n    ./Run.ps1`n.NOTES`n    None.`n#>`n[CmdletBinding()]`nparam()"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN013HelpComplete').Count | Should -Be 1
        $fixed = $script.Replace("7.0`n<#", "7.0`n`n<#")
        @(Get-RuleHit -Script $fixed -Rule 'Measure-AN013HelpComplete').Count | Should -Be 0
    }

    It 'Measure-AN013HelpComplete names a missing and a stale parameter entry' {
        $script = "function Get-Thing {`n    <#`n    .SYNOPSIS`n        Returns.`n    .DESCRIPTION`n        Returns.`n    .PARAMETER Old`n        Gone.`n    .EXAMPLE`n        Get-Thing`n    .NOTES`n        None.`n    #>`n    [CmdletBinding()]`n    param([string]`$Name)`n}"
        $hits = @(Get-RuleHit -Script $script -Rule 'Measure-AN013HelpComplete')
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match 'no \.PARAMETER for Name'
        $hits[0].Message | Should -Match 'names no parameter: OLD'
    }

    It 'Measure-AN014WhatIfDecided skips a command that does not support ShouldProcess' -ForEach @(
        @{ Binding = '[CmdletBinding()]' }
        @{ Binding = '[CmdletBinding(SupportsShouldProcess = $false)]' }
    ) {
        $script = "function Remove-Thing { $Binding param([string]`$Path) Remove-Item -Path `$Path }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN014WhatIfDecided').Count | Should -Be 0
    }

    It 'Measure-AN014WhatIfDecided accepts <Name>' -ForEach @(
        @{ Name = 'an early return when ShouldProcess declines'; Body = 'if (-not $PSCmdlet.ShouldProcess($Path, "Remove")) { return } Remove-Item -Path $Path' }
        @{ Name = 'a gate held in a variable'; Body = '$go = $PSCmdlet.ShouldProcess($Path, "Remove"); if ($go) { Remove-Item -Path $Path }' }
        @{ Name = 'an explicit -WhatIf:$false'; Body = 'New-Item -Path $Path -ItemType Directory -WhatIf:$false' }
        @{ Name = 'a call to a function'; Body = 'Remove-OtherThing -Path $Path' }
    ) {
        $script = "function Remove-Thing { [CmdletBinding(SupportsShouldProcess)] param([string]`$Path) $Body }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN014WhatIfDecided').Count | Should -Be 0
    }

    It 'Measure-AN014WhatIfDecided reports a call outside the gate and not the one inside it' {
        $script = 'function Remove-Thing { [CmdletBinding(SupportsShouldProcess)] param([string]$Path) if ($PSCmdlet.ShouldProcess($Path, "Remove")) { Remove-Item -Path $Path } Set-Content -Path $Path -Value "x" -Encoding UTF8 }'
        $hits = @(Get-RuleHit -Script $script -Rule 'Measure-AN014WhatIfDecided')
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match "'Set-Content'"
    }

    It 'Measure-AN015PublicParameterValidated reports an unvalidated parameter in a Public folder' {
        $script = 'function Get-Thing { [CmdletBinding()] param([string]$Name) $Name }'
        $hits = @(Get-FileRuleHit -RelativePath 'src/Public/Get-Thing.ps1' -Script $script -Rule 'Measure-AN015PublicParameterValidated')
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match "'Name' of 'Get-Thing'"
    }

    It 'Measure-AN015PublicParameterValidated passes validated, switch and credential parameters' {
        $script = 'function Get-Thing { [CmdletBinding()] param([ValidateNotNullOrEmpty()][string]$Name, [switch]$Force, [securestring]$Password, [pscredential]$Credential) $Name }'
        @(Get-FileRuleHit -RelativePath 'src/Public/Get-Thing.ps1' -Script $script -Rule 'Measure-AN015PublicParameterValidated').Count | Should -Be 0
    }

    It 'Measure-AN015PublicParameterValidated skips a file outside a Public folder' {
        $script = 'function Get-Thing { [CmdletBinding()] param([string]$Name) $Name }'
        @(Get-FileRuleHit -RelativePath 'src/Private/Get-Thing.ps1' -Script $script -Rule 'Measure-AN015PublicParameterValidated').Count | Should -Be 0
    }

    It 'Measure-AN016RequiresVersion skips a .psd1 data file and reports a .ps1 file' {
        @(Get-FileRuleHit -RelativePath 'data/Settings.psd1' -Script '@{ Name = "x" }' -Rule 'Measure-AN016RequiresVersion').Count | Should -Be 0
        @(Get-FileRuleHit -RelativePath 'data/Run.ps1' -Script 'Write-Output "x"' -Rule 'Measure-AN016RequiresVersion').Count | Should -Be 1
    }

    It 'Measure-AN017VerboseLabelled accepts <Name>' -ForEach @(
        @{ Name = 'the -Message parameter'; Body = 'Write-Verbose -Message "[Get-Thing] Reading $Path."' }
        @{ Name = 'a -f expression'; Body = 'Write-Verbose ("[Get-Thing] Reading {0}." -f $Path)' }
        @{ Name = 'a message held in a variable'; Body = '$text = "Reading."; Write-Verbose $text' }
        @{ Name = 'the outer name in a nested helper'; Body = 'function Read-Inner { Write-Verbose "[Get-Thing] Inner." } Read-Inner' }
        @{ Name = 'the inner name in a nested helper'; Body = 'function Read-Inner { Write-Verbose "[Read-Inner] Inner." } Read-Inner' }
    ) {
        $script = "function Get-Thing { [CmdletBinding()] param([string]`$Path) $Body }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN017VerboseLabelled').Count | Should -Be 0
    }

    It 'Measure-AN017VerboseLabelled reports a wrong label and names the expected one' {
        $script = 'function Get-Thing { [CmdletBinding()] param() Write-Verbose -Message "[Get-Other] Reading." }'
        $hits = @(Get-RuleHit -Script $script -Rule 'Measure-AN017VerboseLabelled')
        $hits.Count | Should -Be 1
        $hits[0].Message | Should -Match '\[Get-Thing\]'
    }

    It 'Measure-AN017VerboseLabelled uses the script name outside every function' {
        @(Get-FileRuleHit -RelativePath 'scripts/Invoke-Build.ps1' -Script 'Write-Verbose "[Invoke-Build] Starting."' -Rule 'Measure-AN017VerboseLabelled').Count | Should -Be 0
        @(Get-FileRuleHit -RelativePath 'scripts/Invoke-Other.ps1' -Script 'Write-Verbose "Starting."' -Rule 'Measure-AN017VerboseLabelled').Count | Should -Be 1
    }

    It 'Measure-AN018NoRegistryWrite reports <Name>' -ForEach @(
        @{ Name = 'an alias of Set-ItemProperty on HKCU:'; Script = 'sp HKCU:\Software\Thing -Name Level -Value 1' }
        @{ Name = 'Remove-Item on a Registry:: path'; Script = 'Remove-Item -Path "Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Thing"' }
        @{ Name = 'New-Item creating a key'; Script = 'New-Item -Path HKCU:\Software\Thing' }
        @{ Name = 'reg add'; Script = 'reg add HKCU\Software\Thing /v Level /d 1 /f' }
        @{ Name = 'reg.exe delete'; Script = 'reg.exe delete HKCU\Software\Thing /f' }
        @{ Name = 'regedit importing a file'; Script = 'regedit /s settings.reg' }
        @{ Name = 'CreateSubKey'; Script = '$key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("Software\Thing")' }
        @{ Name = 'Registry.SetValue'; Script = '[Microsoft.Win32.Registry]::SetValue("HKEY_CURRENT_USER\Software\Thing", "Level", 1)' }
        @{ Name = 'SetValue on a key in a file that names a registry type'; Script = '[Microsoft.Win32.RegistryKey]$key = $null; $key.SetValue("Level", 1)' }
        @{ Name = 'OpenSubKey for writing'; Script = '[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("SOFTWARE\Thing", $true)' }
    ) {
        @(Get-RuleHit -Script $Script -Rule 'Measure-AN018NoRegistryWrite').Count | Should -BeGreaterThan 0
    }

    It 'Measure-AN018NoRegistryWrite passes <Name>' -ForEach @(
        @{ Name = 'reg query'; Script = 'reg query HKCU\Software\Thing' }
        @{ Name = 'Array.SetValue in a file that names no registry type'; Script = '$a = @(1, 2); $a.SetValue(5, 0)' }
        @{ Name = 'Set-ItemProperty on a file'; Script = 'Set-ItemProperty -Path C:\temp\file.txt -Name IsReadOnly -Value $true' }
        @{ Name = 'OpenSubKey for reading'; Script = '[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("SOFTWARE\Thing")' }
        @{ Name = 'a change suppressed with a justification'; Script = "function Set-Thing { [Diagnostics.CodeAnalysis.SuppressMessageAttribute('Measure-AN018NoRegistryWrite', '', Justification = 'Installer sets its own key.')] [CmdletBinding()] param() Set-ItemProperty -Path HKCU:\Software\Thing -Name Level -Value 1 }" }
    ) {
        @(Get-RuleHit -Script $Script -Rule 'Measure-AN018NoRegistryWrite').Count | Should -Be 0
    }

    It 'Measure-AN014WhatIfDecided accepts an early exit: <Name>' -ForEach @(
        @{ Name = 'continue after a declined ShouldProcess in a loop'; Body = 'foreach ($i in $Items) { if (-not $PSCmdlet.ShouldProcess($i, "Install")) { Write-Output "skip"; continue } Remove-Item -Path $i; New-Item -Path $i -ItemType Directory }' }
        @{ Name = 'break in a loop'; Body = 'foreach ($i in $Items) { if (-not $PSCmdlet.ShouldProcess($i, "Install")) { break } Remove-Item -Path $i }' }
        @{ Name = 'a labelled continue for the outer loop'; Body = ':outer foreach ($a in $Items) { foreach ($b in $a) { if (-not $PSCmdlet.ShouldProcess($b, "Install")) { continue outer } Remove-Item -Path $b } }' }
        @{ Name = 'break in a switch clause'; Body = 'switch ($Items) { default { if (-not $PSCmdlet.ShouldProcess($PSItem, "Install")) { break } Remove-Item -Path $PSItem } }' }
        @{ Name = 'return inside a ForEach-Object block, for a call in the same block'; Body = '$Items | ForEach-Object { if (-not $PSCmdlet.ShouldProcess($PSItem, "Install")) { return } Remove-Item -Path $PSItem }' }
        @{ Name = 'return before a pipeline whose block holds the call'; Body = 'if (-not $PSCmdlet.ShouldProcess("x", "Install")) { return }; $Items | ForEach-Object { Remove-Item -Path $PSItem }' }
        @{ Name = 'throw in a nested block, for a call later in that block'; Body = 'if ($Items) { if (-not $PSCmdlet.ShouldProcess("x", "Install")) { throw "declined" } Remove-Item -Path "x" }' }
    ) {
        $script = "function Install-Thing { [CmdletBinding(SupportsShouldProcess)] param([object[]]`$Items) $Body }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN014WhatIfDecided').Count | Should -Be 0
    }

    It 'Measure-AN014WhatIfDecided reports a call no early exit covers: <Name>' -ForEach @(
        @{ Name = 'the if body does not leave'; Body = 'foreach ($i in $Items) { if (-not $PSCmdlet.ShouldProcess($i, "Install")) { Write-Output "skip" } Remove-Item -Path $i }' }
        @{ Name = 'a call after the loop that continue leaves'; Body = 'foreach ($i in $Items) { if (-not $PSCmdlet.ShouldProcess($i, "Install")) { continue } }; Remove-Item -Path "x"' }
        @{ Name = 'continue inside a ForEach-Object block'; Body = '$Items | ForEach-Object { if (-not $PSCmdlet.ShouldProcess($PSItem, "Install")) { continue } Remove-Item -Path $PSItem }' }
        @{ Name = 'a call after the inner loop that continue leaves'; Body = 'foreach ($a in $Items) { foreach ($b in $a) { if (-not $PSCmdlet.ShouldProcess($b, "Install")) { continue } }; Remove-Item -Path $a }' }
        @{ Name = 'a call after the switch that break leaves'; Body = 'foreach ($i in $Items) { switch ($i) { default { if (-not $PSCmdlet.ShouldProcess($i, "Install")) { break } } }; Remove-Item -Path $i }' }
        @{ Name = 'return inside a ForEach-Object block, for a call after the pipeline'; Body = '$Items | ForEach-Object { if (-not $PSCmdlet.ShouldProcess($PSItem, "Install")) { return } }; Remove-Item -Path "x"' }
        @{ Name = 'return in another branch'; Body = 'if ($Items.Count -gt 5) { if (-not $PSCmdlet.ShouldProcess("x", "Install")) { return } }; Remove-Item -Path "x"' }
        @{ Name = 'a return that is not the last statement of the if body'; Body = 'if (-not $PSCmdlet.ShouldProcess("x", "Install")) { if ($Items) { return } }; Remove-Item -Path "x"' }
    ) {
        $script = "function Install-Thing { [CmdletBinding(SupportsShouldProcess)] param([object[]]`$Items) $Body }"
        @(Get-RuleHit -Script $script -Rule 'Measure-AN014WhatIfDecided').Count | Should -Be 1
    }

    It 'Measure-AN017VerboseLabelled accepts in a class method: <Name>' -ForEach @(
        @{ Name = 'the class name'; Script = 'class RotationJob { [string] GetOracleHome() { Write-Verbose "[RotationJob] Reading."; return "x" } }' }
        @{ Name = 'the method name'; Script = 'class RotationJob { [string] GetOracleHome() { Write-Verbose "[GetOracleHome] Reading."; return "x" } }' }
        @{ Name = 'the class name in a static method'; Script = 'class RotationJob { static [string] Find() { Write-Verbose "[RotationJob] Finding."; return "x" } }' }
        @{ Name = 'the class name in a constructor'; Script = 'class RotationJob { RotationJob() { Write-Verbose "[RotationJob] Created." } }' }
    ) {
        @(Get-RuleHit -Script $Script -Rule 'Measure-AN017VerboseLabelled').Count | Should -Be 0
    }

    It 'Measure-AN017VerboseLabelled reports <Name>' -ForEach @(
        @{ Name = 'another name in a class method'; Script = 'class RotationJob { [string] GetOracleHome() { Write-Verbose "[OtherName] Reading."; return "x" } }' }
        @{ Name = 'the class name in a function outside the class'; Script = 'class RotationJob { [string] Name() { return "x" } }; function Get-Thing { [CmdletBinding()] param() Write-Verbose "[RotationJob] Reading." }' }
    ) {
        @(Get-RuleHit -Script $Script -Rule 'Measure-AN017VerboseLabelled').Count | Should -Be 1
    }
}
