#Requires -Version 7.6

# The gate's behaviour, run against throwaway repositories. Each fixture is a new git
# repository under TestDrive with the kit copied in at tools/gate, as a target
# repository holds it. Each case proves a check passes clean input and fails the
# defect it exists for.
#
# Values that look like secrets are built at run time, so this file holds none and the
# kit's own secret scan stays clean.

BeforeAll {
    $script:kitRoot = Split-Path -Path $PSScriptRoot -Parent

    # Runs git in a fixture with a fixed test identity and no signing or hooks.
    function Invoke-FixtureGit {
        param([string]$Repo, [string[]]$Argument)
        $common = @('-C', $Repo, '-c', 'user.name=gate-test', '-c', 'user.email=gate-test@example.com', '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null')
        $out = & git @common @Argument 2>&1
        if ($LASTEXITCODE -ne 0) { throw "git $($Argument -join ' ') failed: $out" }
        $out
    }

    # Creates a fixture repository with the kit at tools/gate and the given config.
    function New-FixtureRepo {
        param([string]$Name, [string]$Config, [switch]$NoConfig)
        $repo = Join-Path -Path $TestDrive -ChildPath $Name
        $null = New-Item -Path $repo -ItemType Directory
        $null = Invoke-FixtureGit -Repo $repo -Argument @('init', '--quiet', '-b', 'main')
        $kit = Join-Path -Path $repo -ChildPath 'tools' -AdditionalChildPath 'gate'
        $null = New-Item -Path $kit -ItemType Directory -Force
        foreach ($folder in 'Scripts', 'Analyzer', 'Config', 'Review', 'Docs') {
            Copy-Item -Path (Join-Path -Path $script:kitRoot -ChildPath $folder) -Destination $kit -Recurse
        }
        if (-not $NoConfig) { Set-FixtureFile -Repo $repo -Path 'gate.config.psd1' -Text $Config }
        $repo
    }

    function Set-FixtureFile {
        param([string]$Repo, [string]$Path, [string]$Text)
        $full = Join-Path -Path $Repo -ChildPath $Path
        $null = New-Item -Path (Split-Path -Path $full -Parent) -ItemType Directory -Force
        [System.IO.File]::WriteAllText($full, $Text, [System.Text.UTF8Encoding]::new($false))
    }

    function Save-FixtureCommit {
        param([string]$Repo, [string]$Message)
        $null = Invoke-FixtureGit -Repo $Repo -Argument @('add', '--all')
        $null = Invoke-FixtureGit -Repo $Repo -Argument @('commit', '--quiet', '-m', $Message)
        (Invoke-FixtureGit -Repo $Repo -Argument @('rev-parse', 'HEAD')) | Select-Object -First 1
    }

    # Runs the fixture's gate in its own process and returns its output and exit code.
    function Invoke-FixtureGate {
        param([string]$Repo, [string[]]$Argument = @())
        $gate   = Join-Path -Path $Repo -ChildPath 'tools' -AdditionalChildPath 'gate', 'Scripts', 'Invoke-Gate.ps1'
        $output = @(& pwsh -NoProfile -File $gate @Argument 2>&1 | ForEach-Object { "$PSItem" -replace '\x1b\[[0-9;]*m', '' })
        [PSCustomObject]@{ Output = $output; ExitCode = $LASTEXITCODE; Text = $output -join "`n" }
    }

    $script:minimal = "@{ SchemaVersion = 1 }"
}

Describe 'Invoke-Gate' -Tag 'Static' {

    Context 'A fresh, empty repository' {

        It 'GK01 to GK08 pass on a repository with no commits and the minimal config' {
            $repo   = New-FixtureRepo -Name 'fresh' -Config $script:minimal
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] gate: all 8 checks passed'
            $result.Text | Should -Match 'GK06 commits : no commits yet; nothing to scan'
            $result.ExitCode | Should -Be 0
        }
    }

    Context 'GK01 config' {

        It 'CF-001 fails and stops when gate.config.psd1 is missing' {
            $repo   = New-FixtureRepo -Name 'noconfig' -NoConfig
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[FAIL\] GK01 config'
            $result.Text | Should -Match 'CF-001'
            $result.Text | Should -Not -Match 'GK02'
            $result.ExitCode | Should -Be 1
        }

        It 'CF-001 reads gate.config.psd1 from Gate/ when the root has none' {
            $repo = New-FixtureRepo -Name 'gateconfig' -NoConfig
            Set-FixtureFile -Repo $repo -Path 'Gate/gate.config.psd1' -Text $script:minimal
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK01 config'
            $result.ExitCode | Should -Be 0
        }

        It 'CF-001 fails and stops when gate.config.psd1 is both at the root and in Gate/' {
            $repo = New-FixtureRepo -Name 'twoconfigs' -Config $script:minimal
            Set-FixtureFile -Repo $repo -Path 'Gate/gate.config.psd1' -Text $script:minimal
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'both at the repository root and in Gate/; keep one \(CF-001\)'
            $result.Text | Should -Not -Match 'GK02'
            $result.ExitCode | Should -Be 1
        }

        It 'CF-003 fails an unknown key' {
            $repo   = New-FixtureRepo -Name 'unknownkey' -Config "@{ SchemaVersion = 1; Analyser = @{} }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match "unknown key 'Analyser' \(CF-003\)"
            $result.ExitCode | Should -Be 1
        }

        It 'CF-004 fails a path that leaves the repository' {
            $repo   = New-FixtureRepo -Name 'escape' -Config "@{ SchemaVersion = 1; StaticTests = '../elsewhere' }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'CF-004'
            $result.ExitCode | Should -Be 1
        }

        It 'CF-005 fails an optional check turned on without its settings' {
            $repo   = New-FixtureRepo -Name 'unitnoscript' -Config "@{ SchemaVersion = 1; Checks = @{ Unit = `$true } }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'CF-005'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK03 analyzer' {

        BeforeAll {
            $script:analyzerRepo = New-FixtureRepo -Name 'analyzer' -Config "@{ SchemaVersion = 1; Analyzer = @{ Paths = @('source') } }"
            Set-FixtureFile -Repo $script:analyzerRepo -Path 'source/Get-Thing.ps1' -Text "function Get-Thing { param([string]`$Name) 1..3 | ForEach-Object { `$_ } }`n"
        }

        It 'AN-001 fails a finding the baseline does not hold, including a kit rule' {
            $result = Invoke-FixtureGate -Repo $script:analyzerRepo
            $result.Text | Should -Match '\[FAIL\] GK03 analyzer'
            $result.Text | Should -Match 'Measure-AN008UsePSItem'
            $result.ExitCode | Should -Be 1
        }

        It 'AN-001 passes once Update-AnalyzerBaseline.ps1 records the findings' {
            Set-FixtureFile -Repo $script:analyzerRepo -Path 'gate.config.psd1' -Text "@{ SchemaVersion = 1; Analyzer = @{ Paths = @('source'); Baseline = 'gate/analyzer-baseline.psd1' } }"
            $update = Join-Path -Path $script:analyzerRepo -ChildPath 'tools' -AdditionalChildPath 'gate', 'Scripts', 'Update-AnalyzerBaseline.ps1'
            $null   = & pwsh -NoProfile -File $update 2>&1
            $LASTEXITCODE | Should -Be 0
            $result = Invoke-FixtureGate -Repo $script:analyzerRepo
            $result.Text | Should -Match '\[PASS\] GK03 analyzer : 0 new finding\(s\) over 1 files; \d+ held by the baseline'
        }

        It 'AN-001 fails a new finding added after the baseline' {
            Set-FixtureFile -Repo $script:analyzerRepo -Path 'source/Get-Other.ps1' -Text "function Get-Other { [OutputType([int])] param([int]`$N) `$N }`nif (`$env:OS) { 1 }`n"
            $result = Invoke-FixtureGate -Repo $script:analyzerRepo
            $result.Text | Should -Match 'source/Get-Other.ps1:\d+ Measure-AN003PlatformFromAutomaticVariable'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK03 analyzer with ExcludeRulesByPath' {

        It 'drops a listed rule under its folder only, and keeps the other rules there' {
            $config = "@{ SchemaVersion = 1; Analyzer = @{ Paths = @('source', 'scripts'); ExcludeRulesByPath = @{ 'scripts' = @('Measure-AN008UsePSItem') } } }"
            $repo   = New-FixtureRepo -Name 'bypath' -Config $config
            $text   = "function Get-Thing { [OutputType([int])] param([int]`$N) 1..`$N | ForEach-Object { `$_ } }`n"
            Set-FixtureFile -Repo $repo -Path 'source/Get-Thing.ps1' -Text $text
            Set-FixtureFile -Repo $repo -Path 'scripts/Get-Thing.ps1' -Text ($text + "if (`$env:OS) { 1 }`n")
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'source/Get-Thing.ps1:\d+ Measure-AN008UsePSItem'
            $result.Text | Should -Not -Match 'scripts/Get-Thing.ps1:\d+ Measure-AN008UsePSItem'
            $result.Text | Should -Match 'scripts/Get-Thing.ps1:\d+ Measure-AN003PlatformFromAutomaticVariable'
            $result.ExitCode | Should -Be 1
        }

        It 'CF-004 fails a folder that does not exist, and CF-003 an entry with no rule names' {
            $config = "@{ SchemaVersion = 1; Analyzer = @{ ExcludeRulesByPath = @{ 'missing' = @('PSAvoidUsingWriteHost'); 'source' = @() } } }"
            $repo   = New-FixtureRepo -Name 'bypathbad' -Config $config
            Set-FixtureFile -Repo $repo -Path 'source/Get-Thing.ps1' -Text "1`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match "Analyzer.ExcludeRulesByPath names 'missing', which is not a folder in the repository \(CF-004\)"
            $result.Text | Should -Match "Analyzer.ExcludeRulesByPath 'source' must list one or more rule names \(CF-003\)"
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK03 analyzer with -Quick' {

        It 'is off with -Quick, so a finding the baseline does not hold passes; the other checks still run' {
            $repo = New-FixtureRepo -Name 'quick' -Config "@{ SchemaVersion = 1; Analyzer = @{ Paths = @('source') } }"
            Set-FixtureFile -Repo $repo -Path 'source/Get-Thing.ps1' -Text "function Get-Thing { param([string]`$Name) 1..3 | ForEach-Object { `$_ } }`n"
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Quick')
            $result.Text | Should -Match '\[OFF\]  GK03 analyzer : skipped by -Quick; CI runs it'
            $result.Text | Should -Not -Match 'Measure-AN008UsePSItem'
            $result.Text | Should -Match '\[PASS\] GK05 secrets'
            $result.Text | Should -Match '\[PASS\] gate: all 7 checks passed'
            $result.ExitCode | Should -Be 0
        }

        It 'skips every check the Quick key lists, and only with -Quick' {
            $config = "@{ SchemaVersion = 1; StaticTests = 'tests'; Checks = @{ Files = `$true }; Quick = @('GK03', 'GK04', 'GK15') }"
            $repo = New-FixtureRepo -Name 'quicklist' -Config $config
            Set-FixtureFile -Repo $repo -Path 'tests/Fails.Tests.ps1' -Text "Describe 'x' { It 'fails' { 1 | Should -Be 2 } }`n"
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Quick')
            $result.Text | Should -Match '\[OFF\]  GK04 static : skipped by -Quick; CI runs it'
            $result.Text | Should -Match '\[OFF\]  GK15 files : skipped by -Quick; CI runs it'
            $result.Text | Should -Match '\[PASS\] GK05 secrets'
            $result.ExitCode | Should -Be 0

            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[FAIL\] GK04 static'
            $result.Text | Should -Match '\[PASS\] GK15 files'
            $result.ExitCode | Should -Be 1
        }

        It 'CF-003 fails a Quick entry for a check that always runs' {
            $repo   = New-FixtureRepo -Name 'quickbad' -Config "@{ SchemaVersion = 1; Quick = @('GK03', 'GK05') }"
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Quick')
            $result.Text | Should -Match "Quick may list only GK03, GK04, GK09, GK14, GK15; 'GK05' always runs \(CF-003\)"
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK05 to GK07 secrets, commits and messages' {

        It 'SE-001 fails a secret in the working tree' {
            $repo  = New-FixtureRepo -Name 'secret' -Config $script:minimal
            $token = 'gh' + 'p_' + ('aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY3z5A' )
            Set-FixtureFile -Repo $repo -Path 'notes.txt' -Text "token = $token`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[FAIL\] GK05 secrets'
            $result.Text | Should -Not -Match $token
            $result.ExitCode | Should -Be 1
        }

        It 'SE-001 passes a finding whose fingerprint is in .gitleaksignore' {
            $repo  = New-FixtureRepo -Name 'ignored' -Config $script:minimal
            $token = 'gh' + 'p_' + ('aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY3z5A')
            Set-FixtureFile -Repo $repo -Path 'notes.txt' -Text "token = $token`n"
            Set-FixtureFile -Repo $repo -Path '.gitleaksignore' -Text "# fixture value, not a credential`nnotes.txt:github-pat:1`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK05 secrets'
            $result.ExitCode | Should -Be 0
        }

        It 'SE-001 passes a finding whose fingerprint is in the file GitleaksIgnore names, and SE-002 reads it too' {
            $repo  = New-FixtureRepo -Name 'ignoredgate' -Config "@{ SchemaVersion = 1; GitleaksIgnore = 'Gate/gitleaksignore' }"
            $token = 'gh' + 'p_' + ('aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY3z5A')
            Set-FixtureFile -Repo $repo -Path 'notes.txt' -Text "token = $token`n"
            Set-FixtureFile -Repo $repo -Path 'Gate/gitleaksignore' -Text "# fixture value, not a credential`nnotes.txt:github-pat:1`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK05 secrets'
            $result.ExitCode | Should -Be 0

            $commit = Save-FixtureCommit -Repo $repo -Message 'add notes'
            Set-FixtureFile -Repo $repo -Path 'Gate/gitleaksignore' -Text "# fixture value, not a credential`nnotes.txt:github-pat:1`n${commit}:notes.txt:github-pat:1`n"
            $null   = Save-FixtureCommit -Repo $repo -Message 'ignore the fixture value in history'
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK06 commits'
            $result.ExitCode | Should -Be 0
        }

        It 'CF-004 fails a GitleaksIgnore that names no file' {
            $repo   = New-FixtureRepo -Name 'ignoremissing' -Config "@{ SchemaVersion = 1; GitleaksIgnore = 'Gate/gitleaksignore' }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match "GitleaksIgnore names 'Gate/gitleaksignore', which is not a file in the repository \(CF-004\)"
            $result.ExitCode | Should -Be 1
        }

        It 'SE-002 fails a secret in an unpushed commit that a later commit removed' {
            $repo  = New-FixtureRepo -Name 'history' -Config $script:minimal
            $token = 'gh' + 'p_' + ('aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY3z5A')
            Set-FixtureFile -Repo $repo -Path 'notes.txt' -Text "token = $token`n"
            $null = Save-FixtureCommit -Repo $repo -Message 'add notes'
            Set-FixtureFile -Repo $repo -Path 'notes.txt' -Text "no token`n"
            $null = Save-FixtureCommit -Repo $repo -Message 'remove the token'
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK05 secrets'
            $result.Text | Should -Match '\[FAIL\] GK06 commits'
            $result.ExitCode | Should -Be 1
        }

        It 'CM-001 fails a commit message that holds a private key header' {
            $repo = New-FixtureRepo -Name 'message' -Config $script:minimal
            Set-FixtureFile -Repo $repo -Path 'readme.txt' -Text "hello`n"
            $null = Save-FixtureCommit -Repo $repo -Message ("add readme`n`n" + '-----BEGIN ' + 'RSA PRIVATE KEY-----')
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[FAIL\] GK07 messages'
            $result.Text | Should -Match 'no private key block'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK08 permissions' {

        BeforeAll {
            $script:settings = '{ "permissions": { "allow": ["Bash(git status *)"], "deny": ["Bash(git push *)"] } }'
            $script:documented = @'
@{ Files = @( @{ Path = '.claude/settings.json'; Keys = @('permissions'); PermissionKeys = @('allow', 'deny'); Allow = @('Bash(git status *)'); Deny = @('Bash(git push *)') } ) }
'@
        }

        It 'PM-002 fails a committed agent settings file that is not documented' {
            $repo = New-FixtureRepo -Name 'pmundocumented' -Config $script:minimal
            Set-FixtureFile -Repo $repo -Path '.claude/settings.json' -Text $script:settings
            $null   = Save-FixtureCommit -Repo $repo -Message 'add settings'
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'PM-002'
            $result.ExitCode | Should -Be 1
        }

        It 'PM-001 passes a file that matches its documented rules' {
            $repo = New-FixtureRepo -Name 'pmmatch' -Config "@{ SchemaVersion = 1; Permissions = 'gate/agent-permissions.psd1' }"
            Set-FixtureFile -Repo $repo -Path '.claude/settings.json' -Text $script:settings
            Set-FixtureFile -Repo $repo -Path 'gate/agent-permissions.psd1' -Text $script:documented
            $null   = Save-FixtureCommit -Repo $repo -Message 'add settings'
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK08 permissions : 1 agent settings file\(s\) match'
        }

        It 'PM-001 fails a removed deny rule, a new allow rule and a new setting' {
            $repo = New-FixtureRepo -Name 'pmloosened' -Config "@{ SchemaVersion = 1; Permissions = 'gate/agent-permissions.psd1' }"
            Set-FixtureFile -Repo $repo -Path '.claude/settings.json' -Text '{ "defaultMode": "bypassPermissions", "permissions": { "allow": ["Bash(git status *)", "Bash(git push *)"], "deny": [] } }'
            Set-FixtureFile -Repo $repo -Path 'gate/agent-permissions.psd1' -Text $script:documented
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match "undocumented setting 'defaultMode'"
            $result.Text | Should -Match 'documented deny rule missing'
            $result.Text | Should -Match 'undocumented allow rule'
            $result.ExitCode | Should -Be 1
        }

        It 'PM-001 passes the kit''s two agent templates together, registry deny rules included' {
            $repo = New-FixtureRepo -Name 'pmtemplates' -Config "@{ SchemaVersion = 1; Permissions = 'gate/agent-permissions.psd1' }"
            $templates = Join-Path -Path $script:kitRoot -ChildPath 'Templates'
            $settings  = [System.IO.File]::ReadAllText((Join-Path -Path $templates -ChildPath 'claude-settings.json'))
            $settings | Should -Match ([regex]::Escape('"Bash(reg* add *)"'))
            $settings | Should -Match ([regex]::Escape('"PowerShell(Set-* *HK*:*)"'))
            Set-FixtureFile -Repo $repo -Path '.claude/settings.json' -Text $settings
            Set-FixtureFile -Repo $repo -Path 'gate/agent-permissions.psd1' -Text ([System.IO.File]::ReadAllText((Join-Path -Path $templates -ChildPath 'agent-permissions.psd1')))
            $null   = Save-FixtureCommit -Repo $repo -Message 'add agent settings'
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK08 permissions : 1 agent settings file\(s\) match'
        }
    }

    Context 'GK09 version' {

        BeforeAll {
            $script:versionConfig = "@{ SchemaVersion = 1; Checks = @{ Version = `$true }; Version = @{ Manifest = 'source/Thing.psd1'; Changelog = 'CHANGELOG.md'; PackageInputs = @('source/') } }"
        }

        It 'VR-001 fails when the manifest and the changelog disagree' {
            $repo = New-FixtureRepo -Name 'vrmismatch' -Config $script:versionConfig
            Set-FixtureFile -Repo $repo -Path 'source/Thing.psd1' -Text "@{ ModuleVersion = '1.2.0' }"
            Set-FixtureFile -Repo $repo -Path 'CHANGELOG.md' -Text "# Changelog`n`n## [1.1.0] - 2026-01-01`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'newest release 1.1.0 \(VR-001\)'
            $result.ExitCode | Should -Be 1
        }

        It 'VR-002 fails a package change under a version already tagged' {
            $repo = New-FixtureRepo -Name 'vrtagged' -Config $script:versionConfig
            Set-FixtureFile -Repo $repo -Path 'source/Thing.psd1' -Text "@{ ModuleVersion = '1.2.0' }"
            Set-FixtureFile -Repo $repo -Path 'CHANGELOG.md' -Text "# Changelog`n`n## [1.2.0] - 2026-01-01`n"
            $null = Save-FixtureCommit -Repo $repo -Message 'release 1.2.0'
            $null = Invoke-FixtureGit -Repo $repo -Argument @('tag', 'v1.2.0')
            $null = Invoke-FixtureGit -Repo $repo -Argument @('switch', '--quiet', '-c', 'feature')
            Set-FixtureFile -Repo $repo -Path 'source/Thing.ps1' -Text "# changed`n"
            $null   = Save-FixtureCommit -Repo $repo -Message 'change the package'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match 'a package input changed since main but v1.2.0 is already released'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK10 review' {

        BeforeAll {
            # A repository with one commit on main and a branch that changes a file.
            $script:reviewRepo = New-FixtureRepo -Name 'review' -Config $script:minimal
            Set-FixtureFile -Repo $script:reviewRepo -Path 'readme.txt' -Text "one`n"
            $script:mainCommit = Save-FixtureCommit -Repo $script:reviewRepo -Message 'first'
            $null = Invoke-FixtureGit -Repo $script:reviewRepo -Argument @('switch', '--quiet', '-c', 'feature')
            Set-FixtureFile -Repo $script:reviewRepo -Path 'readme.txt' -Text "two`n"
            $script:changeCommit = Save-FixtureCommit -Repo $script:reviewRepo -Message 'change the readme'

            function Set-ReviewRecord {
                param([string]$Response)
                $record = [ordered]@{
                    SchemaVersion = 1
                    Commit        = $script:changeCommit
                    BaseCommit    = $script:mainCommit
                    Completed     = $true
                    Findings      = @([ordered]@{ Id = 'F1'; Severity = 'Low'; Response = $Response })
                }
                Set-FixtureFile -Repo $script:reviewRepo -Path 'Review/LastReview.json' -Text (ConvertTo-Json -InputObject $record -Depth 4)
                $null = Save-FixtureCommit -Repo $script:reviewRepo -Message 'record the review'
            }
        }

        It 'is off without -Base' {
            $result = Invoke-FixtureGate -Repo $script:reviewRepo
            $result.Text | Should -Match '\[OFF\]  GK10 review : runs only with -Base'
        }

        It 'RV-001 fails a branch with no review record' {
            $result = Invoke-FixtureGate -Repo $script:reviewRepo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[FAIL\] GK10 review'
            $result.Text | Should -Match 'Review/LastReview.json is not in HEAD'
        }

        It 'RV-001 fails a finding with no answer' {
            Set-ReviewRecord -Response ''
            $result = Invoke-FixtureGate -Repo $script:reviewRepo -Argument @('-Base', 'main')
            $result.Text | Should -Match 'finding F1 is not answered'
        }

        It 'RV-001 passes a record that covers the branch with every finding answered' {
            Set-ReviewRecord -Response 'Accepted: a test record'
            $result = Invoke-FixtureGate -Repo $script:reviewRepo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[PASS\] GK10 review'
            $result.ExitCode | Should -Be 0
        }
    }

    Context 'GK11 unit' {

        It 'UT-001 fails when the unit script exits 1, and is off without -Unit' {
            $repo = New-FixtureRepo -Name 'unit' -Config "@{ SchemaVersion = 1; Checks = @{ Unit = `$true }; Unit = @{ Script = 'scripts/Invoke-UnitTest.ps1' } }"
            Set-FixtureFile -Repo $repo -Path 'scripts/Invoke-UnitTest.ps1' -Text "Write-Output '[FAIL] unit: 1 failed'`nexit 1`n"
            (Invoke-FixtureGate -Repo $repo).Text | Should -Match '\[OFF\]  GK11 unit : runs only with -Unit'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Unit')
            $result.Text | Should -Match '\[FAIL\] GK11 unit'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK12 evidence' {

        BeforeAll {
            $script:evidenceConfig = "@{ SchemaVersion = 1; Checks = @{ Review = `$false; Evidence = `$true }; Evidence = @{ Script = 'scripts/Invoke-IntegrationTest.ps1'; Paths = @('source/') } }"

            # A repository with main, and a branch that changes a file under source/.
            function New-EvidenceRepo {
                param([string]$Name, [int]$ExitCode)
                $repo = New-FixtureRepo -Name $Name -Config $script:evidenceConfig
                Set-FixtureFile -Repo $repo -Path 'scripts/Invoke-IntegrationTest.ps1' -Text "Write-Output 'integration ran'`nexit $ExitCode`n"
                Set-FixtureFile -Repo $repo -Path 'source/Thing.ps1' -Text "# one`n"
                Set-FixtureFile -Repo $repo -Path 'readme.txt' -Text "one`n"
                $null = Save-FixtureCommit -Repo $repo -Message 'first'
                $null = Invoke-FixtureGit -Repo $repo -Argument @('switch', '--quiet', '-c', 'feature')
                $repo
            }

            function Invoke-FixtureEvidence {
                param([string]$Repo)
                $script = Join-Path -Path $Repo -ChildPath 'tools' -AdditionalChildPath 'gate', 'Scripts', 'Invoke-EvidenceRun.ps1'
                $output = @(& pwsh -NoProfile -File $script 2>&1 | ForEach-Object { "$PSItem" })
                [PSCustomObject]@{ ExitCode = $LASTEXITCODE; Text = $output -join "`n" }
            }
        }

        It 'EV-001 needs no evidence when nothing under Evidence.Paths changed, and is off without -Base' {
            $repo = New-EvidenceRepo -Name 'evnone' -ExitCode 0
            Set-FixtureFile -Repo $repo -Path 'readme.txt' -Text "two`n"
            $null = Save-FixtureCommit -Repo $repo -Message 'change the readme'
            (Invoke-FixtureGate -Repo $repo).Text | Should -Match '\[OFF\]  GK12 evidence : runs only with -Base'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[PASS\] GK12 evidence : nothing under Evidence.Paths changed since main'
            $result.ExitCode | Should -Be 0
        }

        It 'EV-001 fails a change under Evidence.Paths with no record' {
            $repo = New-EvidenceRepo -Name 'evmissing' -ExitCode 0
            Set-FixtureFile -Repo $repo -Path 'source/Thing.ps1' -Text "# two`n"
            $null   = Save-FixtureCommit -Repo $repo -Message 'change the source'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[FAIL\] GK12 evidence'
            $result.Text | Should -Match 'Evidence/LastRun.json is not in HEAD'
            $result.ExitCode | Should -Be 1
        }

        It 'EV-001 passes a committed passing run, and fails once the source changes after it' {
            $repo = New-EvidenceRepo -Name 'evcurrent' -ExitCode 0
            Set-FixtureFile -Repo $repo -Path 'source/Thing.ps1' -Text "# two`n"
            $null = Save-FixtureCommit -Repo $repo -Message 'change the source'
            $run  = Invoke-FixtureEvidence -Repo $repo
            $run.Text | Should -Match 'integration ran'
            $run.ExitCode | Should -Be 0
            $null   = Save-FixtureCommit -Repo $repo -Message 'record the evidence'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[PASS\] GK12 evidence : Evidence.Paths changed; Evidence/LastRun.json is current'
            Set-FixtureFile -Repo $repo -Path 'source/Thing.ps1' -Text "# three`n"
            $null   = Save-FixtureCommit -Repo $repo -Message 'change the source again'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match 'changed after the run''s commit [0-9a-f]{7}: source/Thing.ps1'
            $result.ExitCode | Should -Be 1
        }

        It 'EV-001 fails a failing run and a run on a tree with uncommitted changes' {
            $repo = New-EvidenceRepo -Name 'evfailed' -ExitCode 1
            Set-FixtureFile -Repo $repo -Path 'source/Thing.ps1' -Text "# two`n"
            $null = Save-FixtureCommit -Repo $repo -Message 'change the source'
            (Invoke-FixtureEvidence -Repo $repo).ExitCode | Should -Be 1
            $null   = Save-FixtureCommit -Repo $repo -Message 'record the failed run'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match 'does not show Evidence = true'

            $dirty = New-EvidenceRepo -Name 'evdirty' -ExitCode 0
            Set-FixtureFile -Repo $dirty -Path 'source/Thing.ps1' -Text "# two`n"
            $run = Invoke-FixtureEvidence -Repo $dirty
            $run.Text | Should -Match 'uncommitted change'
            $run.ExitCode | Should -Be 1
        }

        It 'CF-005 fails Checks.Evidence on with no script or paths' {
            $repo   = New-FixtureRepo -Name 'evnoconfig' -Config "@{ SchemaVersion = 1; Checks = @{ Evidence = `$true } }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'Evidence.Script must name a script \(CF-005\)'
            $result.Text | Should -Match 'Evidence.Paths must list one or more paths \(CF-005\)'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK13 package' {

        BeforeAll {
            $script:packageConfig = "@{ SchemaVersion = 1; Checks = @{ Review = `$false; Package = `$true }; Package = @{ Manifest = 'source/Thing/Thing.psd1' } }"

            function New-PackageRepo {
                param([string]$Name, [string]$FileList)
                $repo = New-FixtureRepo -Name $Name -Config $script:packageConfig
                $manifest = "@{ RootModule = 'Thing.psm1'; ModuleVersion = '1.0.0'; GUID = '0b6f3c47-7d0c-4d55-9a37-2f0e1c5a9b11'; Author = 'gate-test'; Description = 'fixture module'; FunctionsToExport = @('Get-Thing')$FileList }"
                Set-FixtureFile -Repo $repo -Path 'source/Thing/Thing.psd1' -Text $manifest
                Set-FixtureFile -Repo $repo -Path 'source/Thing/Thing.psm1' -Text "function Get-Thing { 1 }`n"
                $null = Save-FixtureCommit -Repo $repo -Message 'first'
                $null = Invoke-FixtureGit -Repo $repo -Argument @('switch', '--quiet', '-c', 'feature')
                $repo
            }
        }

        It 'PK-001 passes a package that holds exactly the FileList, and is off without -Base' {
            $repo = New-PackageRepo -Name 'pkmatch' -FileList "; FileList = @('Thing.psd1', 'Thing.psm1')"
            (Invoke-FixtureGate -Repo $repo).Text | Should -Match '\[OFF\]  GK13 package : runs only with -Base'
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[PASS\] GK13 package : Thing.1.0.0.nupkg holds the 2 files FileList names'
            $result.ExitCode | Should -Be 0
        }

        It 'PK-001 fails a stray file in the module folder that FileList does not name' {
            $repo = New-PackageRepo -Name 'pkstray' -FileList "; FileList = @('Thing.psd1', 'Thing.psm1')"
            Set-FixtureFile -Repo $repo -Path 'source/Thing/notes.txt' -Text "scratch`n"
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match '\[FAIL\] GK13 package'
            $result.Text | Should -Match 'not in FileList: notes.txt'
            $result.ExitCode | Should -Be 1
        }

        It 'PK-001 fails a manifest with no FileList' {
            $repo   = New-PackageRepo -Name 'pknolist' -FileList ''
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Base', 'main')
            $result.Text | Should -Match 'has no FileList'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK14 instructions' {

        BeforeAll {
            $script:instructionConfig = "@{ SchemaVersion = 1; Checks = @{ Instructions = `$true }; Instructions = @{ Sources = @('docs/standards/coding.md') } }"

            function Invoke-FixtureExport {
                param([string]$Repo)
                $script = Join-Path -Path $Repo -ChildPath 'tools' -AdditionalChildPath 'gate', 'Scripts', 'Export-AgentInstruction.ps1'
                $null = & pwsh -NoProfile -File $script 2>&1
                $LASTEXITCODE
            }
        }

        It 'AG-001 fails a missing file, passes once built, and fails when a source changes' {
            $repo = New-FixtureRepo -Name 'agents' -Config $script:instructionConfig
            Set-FixtureFile -Repo $repo -Path 'docs/standards/coding.md' -Text "# Coding`n`n## Naming`n`n- Use approved verbs. See [rules](../rules.md#ids) and [the web](https://example.com).`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'AGENTS.md is missing'
            $result.ExitCode | Should -Be 1

            Invoke-FixtureExport -Repo $repo | Should -Be 0
            $text = [System.IO.File]::ReadAllText((Join-Path -Path $repo -ChildPath 'AGENTS.md'))
            $text | Should -Match '(?m)^# Agent instructions$'
            $text | Should -Match '(?m)^## Coding$'
            $text | Should -Match '(?m)^### Naming$'
            $text | Should -Match 'Source: `docs/standards/coding.md`'
            $text | Should -Match '\[rules\]\(docs/rules.md#ids\)'
            $text | Should -Match '\[the web\]\(https://example.com\)'
            $text | Should -Match 'pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1'
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK14 instructions : AGENTS.md matches its 1 source file\(s\)'

            Set-FixtureFile -Repo $repo -Path 'docs/standards/coding.md' -Text "# Coding`n`n- A new rule.`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'AGENTS.md differs from its sources from line \d+'
            $result.ExitCode | Should -Be 1
        }

        It 'AG-001 fails a source file with no title' {
            $repo = New-FixtureRepo -Name 'agentsnotitle' -Config $script:instructionConfig
            Set-FixtureFile -Repo $repo -Path 'docs/standards/coding.md' -Text "No title here.`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match "'docs/standards/coding.md' has no first-level title"
            $result.ExitCode | Should -Be 1
        }

        It 'CF-005 fails Checks.Instructions on with no sources' {
            $repo   = New-FixtureRepo -Name 'agentsnosources' -Config "@{ SchemaVersion = 1; Checks = @{ Instructions = `$true } }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'Instructions.Sources must list one or more files \(CF-005\)'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'GK15 files' {

        BeforeAll {
            # A private key header, built at run time so this file holds none.
            $script:keyHeader = '-----BEGIN ' + 'RSA PRIVATE KEY-----'
        }

        It 'is off by default, and FP-001 fails a tracked and an untracked file that match a pattern' {
            $repo = New-FixtureRepo -Name 'files' -Config $script:minimal
            Set-FixtureFile -Repo $repo -Path 'docs/notes.md' -Text "Key:`n$script:keyHeader`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[OFF\]\s+GK15 files'

            Set-FixtureFile -Repo $repo -Path 'gate.config.psd1' -Text "@{ SchemaVersion = 1; Checks = @{ Files = `$true } }"
            $null = Save-FixtureCommit -Repo $repo -Message 'add notes'
            Set-FixtureFile -Repo $repo -Path 'scratch.txt' -Text "$script:keyHeader`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'docs/notes.md:2: no private key block: -----B\*\*\*'
            $result.Text | Should -Match 'scratch.txt:1: no private key block'
            $result.Text | Should -Not -Match 'RSA PRIVATE'
            $result.ExitCode | Should -Be 1
        }

        It 'FP-001 skips Files.Exclude, ignored files, binary files and the pattern file itself' {
            $patterns = "@{ Patterns = @( @{ Id = 'CM-001'; Title = 'no internal host name'; Pattern = 'build-host-[0-9]+'; Allow = '' } ) }"
            $config   = "@{ SchemaVersion = 1; Checks = @{ Files = `$true }; MessagePatterns = 'gate/patterns.psd1'; Files = @{ Exclude = @('fixtures/') } }"
            $repo = New-FixtureRepo -Name 'filesskip' -Config $config
            Set-FixtureFile -Repo $repo -Path 'gate/patterns.psd1' -Text "$patterns`n# example: build-host-12`n"
            Set-FixtureFile -Repo $repo -Path 'fixtures/sample.txt' -Text "build-host-12`n"
            Set-FixtureFile -Repo $repo -Path '.gitignore' -Text "out/`n"
            Set-FixtureFile -Repo $repo -Path 'out/log.txt' -Text "build-host-12`n"
            Set-FixtureFile -Repo $repo -Path 'data.bin' -Text "build-host-12`0`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match '\[PASS\] GK15 files : no pattern matches'

            Set-FixtureFile -Repo $repo -Path 'docs/setup.md' -Text "Run on build-host-12.`n"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'docs/setup.md:1: no internal host name: build-\*\*\*'
            $result.ExitCode | Should -Be 1
        }

        It 'CF-004 fails a Files.Exclude path that leaves the repository' {
            $repo   = New-FixtureRepo -Name 'filesbad' -Config "@{ SchemaVersion = 1; Checks = @{ Files = `$true }; Files = @{ Exclude = @('../other/') } }"
            $result = Invoke-FixtureGate -Repo $repo
            $result.Text | Should -Match 'CF-004'
            $result.ExitCode | Should -Be 1
        }
    }

    Context 'Output with -Timestamp' {

        It 'starts every line with the UTC time and ends each [PASS] and [FAIL] line with the check''s duration' {
            $repo   = New-FixtureRepo -Name 'timestamp' -Config $script:minimal
            $result = Invoke-FixtureGate -Repo $repo -Argument @('-Timestamp')
            $lines  = @($result.Output | Where-Object { $PSItem })
            $lines.Count | Should -BeGreaterThan 0
            foreach ($line in $lines) { $line | Should -Match '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z ' }
            @($lines | Where-Object { $PSItem -match '\[(PASS|FAIL)\] GK\d\d ' }) | ForEach-Object { $PSItem | Should -Match ' \(\d+\.\d s\)$' }
            @($lines | Where-Object { $PSItem -match '\[OFF\] ' }) | ForEach-Object { $PSItem | Should -Not -Match ' s\)$' }
            $result.Text | Should -Match '\[PASS\] gate: all 8 checks passed'
            $result.ExitCode | Should -Be 0
        }

        It 'adds no time and no duration without -Timestamp, and times the detail lines of a failure' {
            $repo   = New-FixtureRepo -Name 'notimestamp' -Config $script:minimal
            $result = Invoke-FixtureGate -Repo $repo
            @($result.Output | Where-Object { $PSItem -match '^\d{4}-\d{2}-\d{2}T' }).Count | Should -Be 0
            @($result.Output | Where-Object { $PSItem -match ' \(\d+\.\d s\)$' }).Count | Should -Be 0

            $bad    = New-FixtureRepo -Name 'timestampfail' -Config "@{ SchemaVersion = 1; Unknown = 1 }"
            $result = Invoke-FixtureGate -Repo $bad -Argument @('-Timestamp')
            $result.Text | Should -Match '(?m)^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \[FAIL\] GK01 config : '
            $result.Text | Should -Match '(?m)^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z        gate\.config\.psd1: unknown key'
            $result.ExitCode | Should -Be 1
        }
    }
}
