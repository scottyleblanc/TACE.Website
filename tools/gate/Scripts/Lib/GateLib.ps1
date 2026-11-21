#Requires -Version 7.6
<#
.SYNOPSIS
    Helpers shared by Invoke-Gate.ps1 and the other scripts in Scripts\.

.DESCRIPTION
    Reads and checks gate.config.psd1 (rules CF-001 to CF-005), resolves the paths it
    names, runs PSScriptAnalyzer with the kit's settings and rules, reads the analyzer
    baseline (AN-001), matches changed paths against config paths, and builds the
    agent instruction file (AG-001).

.NOTES
    **Invocation:** lib helper — dot-sourced by the scripts in Scripts\. Defines
    functions only; running it does nothing else.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The config keys and their defaults. A key missing from a repository's config takes
# the default; a key not listed here fails CF-003.
$script:GateConfigDefault = [ordered]@{
    SchemaVersion   = 1
    Checks          = [ordered]@{ Review = $true; Version = $false; Unit = $false; Evidence = $false; Package = $false; Instructions = $false; Files = $false }
    Analyzer        = [ordered]@{ Paths = @(); Exclude = @('*.Tests.ps1'); ExcludeRules = @(); ExcludeRulesByPath = @{}; Baseline = '' }
    StaticTests     = ''
    Gitleaks        = ''
    GitleaksIgnore  = ''
    MessagePatterns = ''
    Permissions     = ''
    Review          = [ordered]@{ Record = 'Review/LastReview.json'; Exempt = @() }
    Version         = [ordered]@{ Manifest = ''; Changelog = ''; NotesFiles = @(); TagPrefix = 'v'; PackageInputs = @() }
    Unit            = [ordered]@{ Script = '' }
    Evidence        = [ordered]@{ Script = ''; Record = 'Evidence/LastRun.json'; Paths = @() }
    Package         = [ordered]@{ Manifest = ''; Build = '' }
    Instructions    = [ordered]@{ Output = 'AGENTS.md'; Title = 'Agent instructions'; Sources = @() }
    Files           = [ordered]@{ Exclude = @() }
    Quick           = @('GK03')
}

# The checks -Quick may skip. The config, tool, secret and permission checks always run.
$script:GateQuickAllowed = @('GK03', 'GK04', 'GK09', 'GK14', 'GK15')

function Get-GateRepoRoot {
    <#
    .SYNOPSIS
        Returns the root of the git checkout that holds a folder.
    .DESCRIPTION
        Asks git for the top level of the working tree that holds the folder.
    .PARAMETER Path
        A folder inside the checkout.
    .EXAMPLE
        $repoRoot = Get-GateRepoRoot -Path (Get-Location).Path
    .OUTPUTS
        System.String. The root, as a full path. Throws when the folder is not in a
        git checkout.
    .NOTES
        Needs git on the PATH (GK02 checks for it).
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Path
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $root = @(& git -C $Path rev-parse --show-toplevel 2>$null) | Select-Object -First 1
    if ($LASTEXITCODE -ne 0 -or -not $root) { throw "[Get-GateRepoRoot] '$Path' is not inside a git checkout." }
    [System.IO.Path]::GetFullPath($root)
}

function Resolve-GatePath {
    <#
    .SYNOPSIS
        Turns a config path into a full path under the repository root (rule CF-004).
    .DESCRIPTION
        Rejects an absolute path, a drive letter, a '\' separator and a '..' segment,
        then joins the '/' separated segments under the root.
    .PARAMETER RepoRoot
        The repository root.
    .PARAMETER RelativePath
        A path from gate.config.psd1: relative, '/' separated, with no '..' segment.
    .EXAMPLE
        $baseline = Resolve-GatePath -RepoRoot $repoRoot -RelativePath 'Gate/analyzer-baseline.psd1'
    .OUTPUTS
        System.String. The full path. Throws when the path is absolute or leaves the
        repository.
    .NOTES
        Does not check that the path exists; Import-GateConfig does that where a rule
        needs it.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$RepoRoot,

        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$RelativePath
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ([System.IO.Path]::IsPathRooted($RelativePath) -or $RelativePath -match '^[A-Za-z]:' -or $RelativePath.Contains('\')) {
        throw "[Resolve-GatePath] '$RelativePath' must be relative to the repository root and use / separators (CF-004)."
    }
    $parts = @($RelativePath.Split('/') | Where-Object { $PSItem -and $PSItem -ne '.' })
    if ($parts -contains '..' -or $parts.Count -eq 0) {
        throw "[Resolve-GatePath] '$RelativePath' must name a path inside the repository (CF-004)."
    }
    if ($parts.Count -eq 1) { return Join-Path -Path $RepoRoot -ChildPath $parts[0] }
    Join-Path -Path $RepoRoot -ChildPath $parts[0] -AdditionalChildPath $parts[1..($parts.Count - 1)]
}

function Import-GateConfig {
    <#
    .SYNOPSIS
        Reads gate.config.psd1 from the repository root, or from Gate/ under it, and
        checks it (rules CF-001 to CF-005).
    .DESCRIPTION
        Reads the copy at the root, else the one at Gate/gate.config.psd1 (DEC-018).
        Starts from the defaults, overlays the keys the file sets, and lists every
        problem found: no copy or a copy in both places, an unreadable file, an unknown
        key, a value of the wrong shape, and a path that is absolute, leaves the
        repository or does not exist. Paths in the file are relative to the repository
        root wherever the file sits.
    .PARAMETER RepoRoot
        The repository root.
    .EXAMPLE
        $read = Import-GateConfig -RepoRoot $repoRoot
        if ($read.Problems.Count -gt 0) { $read.Problems }
    .OUTPUTS
        PSCustomObject with Config (an ordered hashtable with every default filled in)
        and Problems (a string array; empty when the config is valid).
    .NOTES
        Reads the file with Import-PowerShellDataFile, so no code in it runs.
    #>
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$RepoRoot
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $problems = [System.Collections.Generic.List[string]]::new()
    $config   = [ordered]@{}
    foreach ($key in $script:GateConfigDefault.Keys) {
        $value = $script:GateConfigDefault[$key]
        $config[$key] = if ($value -is [System.Collections.IDictionary]) { [ordered]@{} + $value } else { $value }
    }

    $atRoot = Join-Path -Path $RepoRoot -ChildPath 'gate.config.psd1'
    $inGate = Join-Path -Path $RepoRoot -ChildPath 'Gate' -AdditionalChildPath 'gate.config.psd1'
    $found  = @($atRoot, $inGate | Where-Object { Test-Path -LiteralPath $PSItem -PathType Leaf })
    if ($found.Count -eq 0) {
        $problems.Add('gate.config.psd1 is not at the repository root or in Gate/ (CF-001)')
        return [PSCustomObject]@{ Config = $config; Problems = @($problems) }
    }
    if ($found.Count -gt 1) {
        $problems.Add('gate.config.psd1 is both at the repository root and in Gate/; keep one (CF-001)')
        return [PSCustomObject]@{ Config = $config; Problems = @($problems) }
    }
    $file = $found[0]

    # Import-PowerShellDataFile accepts only data: no command or expression runs.
    $read = $null
    try {
        $read = Import-PowerShellDataFile -LiteralPath $file
    }
    catch {
        $problems.Add("gate.config.psd1 is not a valid data file: $($PSItem.Exception.Message) (CF-001)")
        return [PSCustomObject]@{ Config = $config; Problems = @($problems) }
    }

    foreach ($key in $read.Keys) {
        if (-not $config.Contains($key)) {
            $problems.Add("gate.config.psd1: unknown key '$key' (CF-003)")
            continue
        }
        $default = $script:GateConfigDefault[$key]
        if ($default -is [System.Collections.IDictionary]) {
            if ($read[$key] -isnot [System.Collections.IDictionary]) {
                $problems.Add("gate.config.psd1: '$key' must be a hashtable (CF-003)")
                continue
            }
            foreach ($inner in $read[$key].Keys) {
                if (-not $default.Contains($inner)) { $problems.Add("gate.config.psd1: unknown key '$key.$inner' (CF-003)") }
                else { $config[$key][$inner] = $read[$key][$inner] }
            }
        }
        else {
            $config[$key] = $read[$key]
        }
    }

    if ($config.SchemaVersion -ne 1) { $problems.Add("gate.config.psd1: SchemaVersion must be 1 (CF-002)") }

    foreach ($name in @($config.Checks.Keys)) {
        if ($config.Checks[$name] -isnot [bool]) { $problems.Add("gate.config.psd1: Checks.$name must be `$true or `$false (CF-003)") }
    }

    foreach ($id in @($config.Quick)) {
        if ($id -notin $script:GateQuickAllowed) {
            $problems.Add("gate.config.psd1: Quick may list only $($script:GateQuickAllowed -join ', '); '$id' always runs (CF-003)")
        }
    }

    # Every path is relative and inside the repository (CF-004); a file the config names
    # must exist, except the review record, which a branch adds later.
    $mustExist = [System.Collections.Generic.List[object]]::new()
    foreach ($path in @($config.Analyzer.Paths)) { $mustExist.Add(@('Analyzer.Paths', $path, 'Container')) }

    # Analyzer.ExcludeRulesByPath maps a folder to the rule names not reported under it.
    $byPath = $config.Analyzer.ExcludeRulesByPath
    if ($byPath -isnot [System.Collections.IDictionary]) {
        $problems.Add("gate.config.psd1: 'Analyzer.ExcludeRulesByPath' must be a hashtable of folder = rule names (CF-003)")
        $config.Analyzer.ExcludeRulesByPath = @{}
    }
    else {
        foreach ($folder in @($byPath.Keys)) {
            $mustExist.Add(@('Analyzer.ExcludeRulesByPath', [string]$folder, 'Container'))
            $rules = @($byPath[$folder])
            if ($rules.Count -eq 0 -or @($rules | Where-Object { $PSItem -isnot [string] -or -not $PSItem }).Count -gt 0) {
                $problems.Add("gate.config.psd1: Analyzer.ExcludeRulesByPath '$folder' must list one or more rule names (CF-003)")
            }
        }
    }
    # The leading commas keep each triple whole: @() would flatten them otherwise.
    $optionalPaths = @(
        , @('Analyzer.Baseline', $config.Analyzer.Baseline, 'Leaf')
        , @('StaticTests', $config.StaticTests, 'Container')
        , @('Gitleaks', $config.Gitleaks, 'Leaf')
        , @('GitleaksIgnore', $config.GitleaksIgnore, 'Leaf')
        , @('MessagePatterns', $config.MessagePatterns, 'Leaf')
        , @('Permissions', $config.Permissions, 'Leaf')
    )
    foreach ($pair in $optionalPaths) {
        if ($pair[1]) { $mustExist.Add($pair) }
    }
    if ($config.Checks.Version) {
        $versionFiles = @(
            , @('Version.Manifest', $config.Version.Manifest, 'Leaf')
            , @('Version.Changelog', $config.Version.Changelog, 'Leaf')
        )
        foreach ($pair in $versionFiles) {
            if (-not $pair[1]) { $problems.Add("gate.config.psd1: Checks.Version is on, so $($pair[0]) must name a file (CF-005)") }
            else { $mustExist.Add($pair) }
        }
        foreach ($path in @($config.Version.NotesFiles)) { $mustExist.Add(@('Version.NotesFiles', $path, 'Leaf')) }
        if ($config.Version.TagPrefix -notmatch '^[A-Za-z0-9._-]*$') { $problems.Add('gate.config.psd1: Version.TagPrefix may hold only letters, digits, ., _ and - (CF-005)') }
    }
    if ($config.Checks.Unit) {
        if (-not $config.Unit.Script) { $problems.Add('gate.config.psd1: Checks.Unit is on, so Unit.Script must name a script (CF-005)') }
        else { $mustExist.Add(@('Unit.Script', $config.Unit.Script, 'Leaf')) }
    }
    if ($config.Checks.Review -and -not $config.Review.Record) {
        $problems.Add('gate.config.psd1: Checks.Review is on, so Review.Record must name a file (CF-005)')
    }
    # The evidence record, like the review record, is added by a branch later.
    $resolveOnly = [System.Collections.Generic.List[string]]::new()
    if ($config.Checks.Evidence) {
        if (-not $config.Evidence.Script) { $problems.Add('gate.config.psd1: Checks.Evidence is on, so Evidence.Script must name a script (CF-005)') }
        else { $mustExist.Add(@('Evidence.Script', $config.Evidence.Script, 'Leaf')) }
        if (-not $config.Evidence.Record) { $problems.Add('gate.config.psd1: Checks.Evidence is on, so Evidence.Record must name a file (CF-005)') }
        else { $resolveOnly.Add([string]$config.Evidence.Record) }
        if (@($config.Evidence.Paths | Where-Object { $PSItem }).Count -eq 0) { $problems.Add('gate.config.psd1: Checks.Evidence is on, so Evidence.Paths must list one or more paths (CF-005)') }
        foreach ($path in @($config.Evidence.Paths)) { if ($path) { $resolveOnly.Add([string]$path) } }
    }
    if ($config.Checks.Package) {
        # A manifest that a build script writes need not exist until the build runs.
        if (-not $config.Package.Manifest) { $problems.Add('gate.config.psd1: Checks.Package is on, so Package.Manifest must name the module manifest (CF-005)') }
        elseif ($config.Package.Build) { $resolveOnly.Add([string]$config.Package.Manifest) }
        else { $mustExist.Add(@('Package.Manifest', $config.Package.Manifest, 'Leaf')) }
        if ($config.Package.Manifest -and -not ([string]$config.Package.Manifest).EndsWith('.psd1')) { $problems.Add('gate.config.psd1: Package.Manifest must name a .psd1 file (CF-005)') }
        if ($config.Package.Build) { $mustExist.Add(@('Package.Build', $config.Package.Build, 'Leaf')) }
    }
    if ($config.Checks.Instructions) {
        if (@($config.Instructions.Sources | Where-Object { $PSItem }).Count -eq 0) { $problems.Add('gate.config.psd1: Checks.Instructions is on, so Instructions.Sources must list one or more files (CF-005)') }
        foreach ($path in @($config.Instructions.Sources)) { $mustExist.Add(@('Instructions.Sources', $path, 'Leaf')) }
        if (-not $config.Instructions.Output) { $problems.Add('gate.config.psd1: Checks.Instructions is on, so Instructions.Output must name a file (CF-005)') }
        else { $resolveOnly.Add([string]$config.Instructions.Output) }
        if ($config.Instructions.Title -isnot [string] -or -not $config.Instructions.Title) { $problems.Add('gate.config.psd1: Instructions.Title must be a non-empty string (CF-005)') }
    }
    if ($config.Checks.Files) {
        foreach ($path in @($config.Files.Exclude)) { if ($path) { $resolveOnly.Add([string]$path) } }
    }

    foreach ($entry in $mustExist) {
        try {
            $full = Resolve-GatePath -RepoRoot $RepoRoot -RelativePath ([string]$entry[1])
            if (-not (Test-Path -LiteralPath $full -PathType $entry[2])) {
                $kind = if ($entry[2] -eq 'Leaf') { 'file' } else { 'folder' }
                $problems.Add("gate.config.psd1: $($entry[0]) names '$($entry[1])', which is not a $kind in the repository (CF-004)")
            }
        }
        catch {
            $problems.Add("gate.config.psd1: $($entry[0]): $($PSItem.Exception.Message -replace '^\[Resolve-GatePath\] ', '')")
        }
    }
    foreach ($path in @($config.Review.Exempt) + @($config.Review.Record) + @($config.Version.PackageInputs) + @($resolveOnly)) {
        if (-not $path) { continue }
        try { $null = Resolve-GatePath -RepoRoot $RepoRoot -RelativePath ([string]$path) }
        catch { $problems.Add("gate.config.psd1: $($PSItem.Exception.Message -replace '^\[Resolve-GatePath\] ', '')") }
    }

    [PSCustomObject]@{ Config = $config; Problems = @($problems) }
}

function Invoke-GateAnalyzer {
    <#
    .SYNOPSIS
        Runs PSScriptAnalyzer over the folders the config names, with the kit's
        settings and custom rules.
    .DESCRIPTION
        Analyzes every .ps1, .psm1 and .psd1 file under Analyzer.Paths except those
        matching Analyzer.Exclude. A finding from a rule that
        Analyzer.ExcludeRulesByPath lists for a folder is dropped for files under it.
    .PARAMETER RepoRoot
        The repository root.
    .PARAMETER KitRoot
        The kit's root folder (the parent of Scripts\).
    .PARAMETER Config
        The config returned by Import-GateConfig.
    .EXAMPLE
        $analysis = Invoke-GateAnalyzer -RepoRoot $repoRoot -KitRoot $kitRoot -Config $read.Config
    .OUTPUTS
        PSCustomObject with FileCount and Findings; each finding has Path (relative,
        '/' separated), Line, Rule and Message.
    .NOTES
        Tries a file again when PSScriptAnalyzer throws while it loads the custom
        rules, up to three times.
    #>
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$RepoRoot,

        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$KitRoot,

        [Parameter(Mandatory)]
        [ValidateNotNull()]
        [System.Collections.IDictionary]$Config
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $settingsFile = Join-Path -Path $KitRoot -ChildPath 'Analyzer' -AdditionalChildPath 'AnalyzerSettings.psd1'
    $kitSettings  = Import-PowerShellDataFile -LiteralPath $settingsFile
    $settings = @{
        Severity            = [string[]]$kitSettings.Severity
        IncludeDefaultRules = $true
        ExcludeRules        = [string[]]@(@($kitSettings.ExcludeRules) + @($Config.Analyzer.ExcludeRules) | Where-Object { $PSItem } | Select-Object -Unique)
        CustomRulePath      = [string](Join-Path -Path $KitRoot -ChildPath 'Analyzer' -AdditionalChildPath 'Rules', '*.psm1')
    }

    $folders = @($Config.Analyzer.Paths | ForEach-Object { Resolve-GatePath -RepoRoot $RepoRoot -RelativePath $PSItem })
    $files   = @()
    if ($folders.Count -gt 0) {
        $files = @(Get-ChildItem -LiteralPath $folders -Include '*.ps1', '*.psm1', '*.psd1' -Recurse -File | Where-Object {
                $name = $PSItem.Name
                @($Config.Analyzer.Exclude | Where-Object { $name -like $PSItem }).Count -eq 0
            } | Sort-Object -Property FullName -Unique)
    }

    # Folder prefixes ('scripts/') and the rules not reported under each. A prefix is
    # text compared with a relative path, not a path, so it is not built with Join-Path.
    $byPath = @(foreach ($folder in @($Config.Analyzer.ExcludeRulesByPath.Keys)) {
            [PSCustomObject]@{ Prefix = '{0}/' -f ([string]$folder).Trim('/'); Rules = [string[]]@($Config.Analyzer.ExcludeRulesByPath[$folder]) }
        })

    $findings = @(foreach ($file in $files) {
            # PSScriptAnalyzer 1.25.0 sometimes throws while it loads the custom rule
            # modules ("more than one dynamic module in each dynamic assembly", or a null
            # reference); the same file then passes on the next call. A throw is not a
            # finding, so the file is tried again, up to three times; a third throw
            # stops the analysis and the check fails.
            $records = $null
            for ($attempt = 1; $null -eq $records; $attempt++) {
                try {
                    $records = @(Invoke-ScriptAnalyzer -Path $file.FullName -Settings $settings)
                }
                catch {
                    if ($attempt -ge 3) {
                        $relativeFile = [System.IO.Path]::GetRelativePath($RepoRoot, $file.FullName).Replace('\', '/')
                        throw "[Invoke-GateAnalyzer] PSScriptAnalyzer failed 3 times on ${relativeFile}: $($PSItem.Exception.Message)"
                    }
                }
            }
            foreach ($record in $records) {
                $relative = [System.IO.Path]::GetRelativePath($RepoRoot, $record.ScriptPath).Replace('\', '/')
                $skip     = @($byPath | Where-Object { $relative.StartsWith($PSItem.Prefix, [System.StringComparison]::OrdinalIgnoreCase) -and $PSItem.Rules -contains $record.RuleName })
                if ($skip.Count -gt 0) { continue }
                [PSCustomObject]@{
                    Path    = $relative
                    Line    = $record.Line
                    Rule    = $record.RuleName
                    Message = $record.Message
                }
            }
        })

    [PSCustomObject]@{ FileCount = $files.Count; Findings = $findings }
}

function Compare-AnalyzerBaseline {
    <#
    .SYNOPSIS
        Splits analyzer findings into those the baseline holds and new ones (rule
        AN-001).
    .DESCRIPTION
        The baseline counts findings per file and rule, so it survives line moves.
        Findings for a file and rule beyond the baseline's count are new; when a file
        and rule have more findings than the baseline allows, every finding of that
        pair is listed, because which one is new cannot be told apart.
    .PARAMETER Findings
        The findings from Invoke-GateAnalyzer.
    .PARAMETER BaselineFile
        The baseline file, or an empty string for none.
    .EXAMPLE
        $compared = Compare-AnalyzerBaseline -Findings $analysis.Findings -BaselineFile $baselinePath
    .OUTPUTS
        PSCustomObject with New (findings that fail), Held (the count the baseline
        holds) and Shrinkable (file and rule pairs with fewer findings than the
        baseline allows).
    .NOTES
        Update-AnalyzerBaseline.ps1 writes the baseline file this reads.
    #>
    [CmdletBinding()]
    [OutputType([PSCustomObject])]
    param(
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [object[]]$Findings,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$BaselineFile
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $allowed = @{}
    if ($BaselineFile) {
        foreach ($entry in @((Import-PowerShellDataFile -LiteralPath $BaselineFile).Findings)) {
            $allowed["$($entry.Path)|$($entry.Rule)"] = [int]$entry.Count
        }
    }

    $new        = [System.Collections.Generic.List[object]]::new()
    $held       = 0
    $shrinkable = [System.Collections.Generic.List[string]]::new()
    $groups     = @($Findings | Group-Object -Property { "$($PSItem.Path)|$($PSItem.Rule)" })
    foreach ($group in $groups) {
        $limit = if ($allowed.ContainsKey($group.Name)) { $allowed[$group.Name] } else { 0 }
        if ($group.Count -gt $limit) { foreach ($finding in $group.Group) { $new.Add($finding) } }
        else { $held += $group.Count }
    }
    foreach ($key in $allowed.Keys) {
        $found = @($groups | Where-Object { $PSItem.Name -eq $key })
        $count = if ($found.Count -gt 0) { $found[0].Count } else { 0 }
        if ($count -lt $allowed[$key]) { $shrinkable.Add($key) }
    }

    [PSCustomObject]@{ New = @($new); Held = $held; Shrinkable = @($shrinkable) }
}

function Select-GateChangedPath {
    <#
    .SYNOPSIS
        Returns the changed paths that a list of config paths covers.
    .DESCRIPTION
        A path is covered when it equals an input, or starts with an input that ends
        in /.
    .PARAMETER Changed
        Repository-relative paths, as git diff --name-only prints them.
    .PARAMETER Inputs
        Config paths: a file, or a folder ending in / that covers everything under it.
    .EXAMPLE
        $touched = @(Select-GateChangedPath -Changed $changed -Inputs $config.Version.PackageInputs)
    .OUTPUTS
        System.String. Each changed path that an input covers.
    .NOTES
        Used by GK09 (package inputs), GK12 (evidence paths) and GK15 (excluded files).
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [string[]]$Changed,

        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [string[]]$Inputs
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    foreach ($path in @($Changed | Where-Object { $PSItem })) {
        $covered = @($Inputs | Where-Object { $PSItem -and ($path -eq $PSItem -or ($PSItem.EndsWith('/') -and $path.StartsWith($PSItem))) })
        if ($covered.Count -gt 0) { $path }
    }
}

function Get-GateAgentInstruction {
    <#
    .SYNOPSIS
        Builds the agent instruction file from the files Instructions.Sources lists
        (rule AG-001).
    .DESCRIPTION
        Joins the source files in the listed order under a generated header. Each
        file's first-level title becomes a second-level heading followed by a Source
        line, and its other headings move down one level. A relative link is rewritten
        to resolve from the repository root, where the output file sits. Text inside
        code fences is carried unchanged.
    .PARAMETER RepoRoot
        The repository root.
    .PARAMETER KitPath
        The kit's folder relative to the repository root, as './tools/gate', or '.'
        when the repository is the kit itself.
    .PARAMETER Config
        The config from Import-GateConfig.
    .EXAMPLE
        $text = Get-GateAgentInstruction -RepoRoot $repoRoot -KitPath './tools/gate' -Config $read.Config
    .OUTPUTS
        System.String. The file's text, with LF line endings and a final newline.
        Throws when a source file has no first-level title or an unclosed code fence.
    .NOTES
        Export-AgentInstruction.ps1 writes the result; GK14 compares it with the
        committed file.
    #>
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('Measure-AN006PathWithJoinPath', '', Justification = 'A Markdown link target is joined with / on every platform; it is a URL, not a file system path.')]
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$RepoRoot,

        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$KitPath,

        [Parameter(Mandatory)]
        [ValidateNotNull()]
        [System.Collections.IDictionary]$Config
    )

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    $out = [System.Collections.Generic.List[string]]::new()
    $out.Add("# $($Config.Instructions.Title)")
    $out.Add('')
    $out.Add("Generated by ``$KitPath/Scripts/Export-AgentInstruction.ps1`` from the files listed")
    $out.Add('under `Instructions.Sources` in `gate.config.psd1`. Do not edit it by hand: change')
    $out.Add('a source file, then run the script again. Gate check GK14 fails when this file does')
    $out.Add('not match its sources.')
    $out.Add('')
    $out.Add('## Checking your work')
    $out.Add('')
    $out.Add("Run ``pwsh -NoProfile -File $KitPath/Scripts/Invoke-Gate.ps1`` before you report a")
    $out.Add('change as done. A change is done only when every check passes.')

    foreach ($source in @($Config.Instructions.Sources)) {
        $full  = Resolve-GatePath -RepoRoot $RepoRoot -RelativePath $source
        $lines = @(([System.IO.File]::ReadAllText($full) -replace "`r`n", "`n").TrimEnd() -split "`n")
        # The folder the source sits in, as path segments from the root.
        $folder = @($source.Split('/') | Where-Object { $PSItem -and $PSItem -ne '.' })
        $folder = if ($folder.Count -gt 1) { @($folder[0..($folder.Count - 2)]) } else { @() }

        $rewrite = {
            param([System.Text.RegularExpressions.Match]$Match)
            $target = $Match.Groups[1].Value
            # Absolute URLs, mail links, anchors and rooted paths stay as they are.
            if ($target -match '^([A-Za-z][A-Za-z0-9+.-]*:|#|/)') { return $Match.Value }
            $fragment = ''
            $hash = $target.IndexOf('#')
            if ($hash -ge 0) { $fragment = $target.Substring($hash); $target = $target.Substring(0, $hash) }
            $stack = [System.Collections.Generic.List[string]]::new()
            foreach ($segment in @($folder) + @($target.Split('/'))) {
                if (-not $segment -or $segment -eq '.') { continue }
                if ($segment -eq '..') {
                    # A link that climbs above the root is left for review to catch.
                    if ($stack.Count -eq 0) { return $Match.Value }
                    $stack.RemoveAt($stack.Count - 1)
                }
                else { $stack.Add($segment) }
            }
            ']({0}{1})' -f ($stack -join '/'), $fragment
        }

        $inFence = $false
        $seenH1  = $false
        $out.Add('')
        foreach ($line in $lines) {
            if ($line -match '^\s*```') {
                $inFence = -not $inFence
                $out.Add($line)
                continue
            }
            if ($inFence) {
                $out.Add($line)
                continue
            }
            if (-not $seenH1 -and $line -match '^# (.+)$') {
                $seenH1 = $true
                $out.Add("## $($Matches[1])")
                $out.Add('')
                $out.Add("Source: ``$source``.")
                continue
            }
            if ($line -match '^#{1,5} ') { $line = "#$line" }
            $out.Add([regex]::Replace($line, '\]\(([^)\s]+)\)', $rewrite))
        }
        if (-not $seenH1) { throw "[Get-GateAgentInstruction] '$source' has no first-level title (AG-001)." }
        if ($inFence) { throw "[Get-GateAgentInstruction] '$source' has an unclosed code fence (AG-001)." }
    }

    ($out -join "`n") + "`n"
}
