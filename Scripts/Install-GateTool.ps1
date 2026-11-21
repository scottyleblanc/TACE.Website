#Requires -Version 7.6

<#
.SYNOPSIS
    Installs the exact tool versions the gate needs: PSScriptAnalyzer, Pester and
    gitleaks.

.DESCRIPTION
    Installs each tool only when the required version is not already present, so it is
    safe to run on a machine that has them.

      PSScriptAnalyzer 1.25.0   from PSGallery, CurrentUser scope
      Pester 5.7.1              from PSGallery, CurrentUser scope
      gitleaks 8.30.1           the windows_x64 zip or linux_x64 tarball from the
                                gitleaks GitHub release, into -Destination. Its SHA-256
                                must equal the hash pinned below, from the release's
                                checksums file; any other file is deleted unread and the
                                script stops

    gitleaks is added to PATH for this PowerShell session only, so run the gate in the
    same session (the CI templates run both scripts in one step).

.PARAMETER Destination
    The folder gitleaks is unpacked into. Created when missing.

.EXAMPLE
    & ./tools/gate/Scripts/Install-GateTool.ps1 -Destination (Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath 'gate-tools')
    & ./tools/gate/Scripts/Invoke-Gate.ps1 -Unit -Base origin/main

    Installs the tools, then runs the gate in the same session, as CI does.

.NOTES
    **Invocation:** Standalone — self-contained; call with `&` in the session that runs
    the gate, so the PATH change reaches it. Needs network access to PSGallery and
    github.com. Supports Windows x64 and Linux x64.
    [SEC] Versions are pinned and the gitleaks download is checked against a pinned
    SHA-256 before it is unpacked. When the gitleaks version changes, take the new
    hashes from the release's gitleaks_<version>_checksums.txt and update both here
    and in Scripts/Invoke-Gate.ps1.
#>
[CmdletBinding(SupportsShouldProcess)]
[OutputType([string])]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Destination
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$modules = @(
    @{ Name = 'PSScriptAnalyzer'; Version = '1.25.0' }
    @{ Name = 'Pester'; Version = '5.7.1' }
)
$gitleaksVersion = '8.30.1'
$assets = @{
    Windows = @{ File = "gitleaks_${gitleaksVersion}_windows_x64.zip"; Sha256 = 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e'; Binary = 'gitleaks.exe' }
    Linux   = @{ File = "gitleaks_${gitleaksVersion}_linux_x64.tar.gz"; Sha256 = '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'; Binary = 'gitleaks' }
}

$platform = if ($IsWindows) { 'Windows' } elseif ($IsLinux) { 'Linux' } else { $null }
if ($null -eq $platform) { throw '[Install-GateTool] Windows x64 and Linux x64 only.' }
if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne [System.Runtime.InteropServices.Architecture]::X64) {
    throw '[Install-GateTool] x64 only: no gitleaks hash is pinned for this architecture.'
}
$asset = $assets[$platform]

# -- Modules -----------------------------------------------------------------

foreach ($module in $modules) {
    $present = @(Get-Module -Name $module.Name -ListAvailable | Where-Object { $PSItem.Version -eq [version]$module.Version })
    if ($present.Count -gt 0) {
        Write-Output "[INFO] $($module.Name) $($module.Version) already installed"
        continue
    }
    if ($PSCmdlet.ShouldProcess("$($module.Name) $($module.Version)", 'Install from PSGallery')) {
        $installParams = @{
            Name            = $module.Name
            Version         = $module.Version
            Repository      = 'PSGallery'
            Scope           = 'CurrentUser'
            TrustRepository = $true
        }
        Install-PSResource @installParams
        Write-Output "[INFO] $($module.Name) $($module.Version) installed"
    }
}

# -- gitleaks ----------------------------------------------------------------

$existing = Get-Command -Name gitleaks -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $existing -and ((& $existing.Source version) | Select-Object -First 1).Trim() -eq $gitleaksVersion) {
    Write-Output "[INFO] gitleaks $gitleaksVersion already on PATH"
    return
}

if (-not $PSCmdlet.ShouldProcess($Destination, "Download, verify and unpack gitleaks $gitleaksVersion")) { return }

$null    = New-Item -Path $Destination -ItemType Directory -Force
$archive = Join-Path -Path $Destination -ChildPath $asset.File
$url     = "https://github.com/gitleaks/gitleaks/releases/download/v$gitleaksVersion/$($asset.File)"
Invoke-WebRequest -Uri $url -OutFile $archive

$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $asset.Sha256) {
    Remove-Item -LiteralPath $archive -Force
    throw "[Install-GateTool] $($asset.File) failed its SHA-256 check; the download was deleted."
}

if ($platform -eq 'Windows') {
    Expand-Archive -LiteralPath $archive -DestinationPath $Destination -Force
}
else {
    & tar -xzf $archive -C $Destination $asset.Binary
    if ($LASTEXITCODE -ne 0) { throw "[Install-GateTool] tar could not unpack $($asset.File)." }
}
Remove-Item -LiteralPath $archive -Force

$env:PATH  = $Destination + [System.IO.Path]::PathSeparator + $env:PATH
$installed = ((& (Join-Path -Path $Destination -ChildPath $asset.Binary) version) | Select-Object -First 1).Trim()
if ($installed -ne $gitleaksVersion) { throw "[Install-GateTool] gitleaks reports $installed; $gitleaksVersion was expected." }
Write-Output "[INFO] gitleaks $gitleaksVersion verified and added to PATH for this session"
