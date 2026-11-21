@{
    # Gate configuration for this repository, read by tools/gate/Scripts/Invoke-Gate.ps1
    # (check GK01, rules CF-001 to CF-005; tools/gate/Docs/rules.md). Every path is
    # relative to the repository root and uses / separators. A key left out takes the
    # kit's default (tools/gate/Templates/gate.config.psd1).

    SchemaVersion = 1

    # The optional checks. The core checks (GK01 to GK08) always run.
    Checks = @{
        Review       = $false   # GK10: off for this repository; most changes are site content
        Version      = $false   # GK09: needs a module manifest; this repository has none
        Unit         = $true    # GK11, with -Unit: Gate/Invoke-UnitTest.ps1 (pytest and the Hugo build)
        Evidence     = $false   # GK12: every test here runs in CI
        Package      = $false   # GK13: nothing is published to a gallery
        Instructions = $false   # GK14: no AGENTS.md
        Files        = $true    # GK15: the repository is public; no tracked file may hold an identifier
    }

    # GK03. The repository is mostly Python, JavaScript, Hugo and Markdown; the gate's
    # own script is the PowerShell analyzed. app/train/scripts/ is not listed yet.
    Analyzer = @{
        Paths              = @('Gate')
        Exclude            = @('*.Tests.ps1')
        ExcludeRules       = @()
        ExcludeRulesByPath = @{}
        Baseline           = ''
    }

    # GK04. No Pester tests read source text here.
    StaticTests = ''

    # GK05 to GK07. The kit's default gitleaks config and .gitleaksignore at the root.
    Gitleaks       = ''
    GitleaksIgnore = ''

    # GK07 and GK15. The kit's default entries plus the AWS, Cognito, OAuth and email
    # identifier formats this public repository must never hold.
    MessagePatterns = 'Gate/message-patterns.psd1'

    # GK08. The rules .claude/settings.json may hold.
    Permissions = 'Gate/agent-permissions.psd1'

    Review = @{
        Record = 'Review/LastReview.json'
        Exempt = @()
    }

    Unit = @{
        Script = 'Gate/Invoke-UnitTest.ps1'
    }

    # GK15. tools/gate/ is the kit, checked by its own gate; its tests and templates
    # hold sample values on purpose. logo.svg holds its own generated element UUIDs.
    Files = @{
        Exclude = @('tools/gate/', 'hugo/static/logo.svg')
    }

    # The checks the pre-push hook (-Quick) skips; CI runs them.
    Quick = @('GK03')
}
