@{
    # Gate configuration for this repository. Copy to the repository root, or to Gate/
    # beside the repository's other gate files, as gate.config.psd1; one copy only
    # (DEC-018). Read by tools/gate/Scripts/Invoke-Gate.ps1 (check GK01, rules CF-001 to
    # CF-005). Every path is relative to the repository root, wherever this file sits,
    # and uses / separators. A key left out takes the default shown here.

    SchemaVersion = 1

    # The optional checks. The core checks (GK01 to GK08) always run.
    Checks = @{
        Review       = $true    # GK10, with -Base: the second-model review record
        Version      = $false   # GK09: one version everywhere, and the tag rule with -Base
        Unit         = $false   # GK11, with -Unit: the repository's unit test script
        Evidence     = $false   # GK12, with -Base: a recorded run of tests CI cannot run
        Package      = $false   # GK13, with -Base: the module package holds only its FileList
        Instructions = $false   # GK14: AGENTS.md matches the standards it is built from
        Files        = $false   # GK15: no file holds a value the message patterns match
    }

    # GK03. The folders analyzed, recursively. Files matching Exclude are skipped.
    # ExcludeRules turns off analyzer rules for this repository; each one is a gap, so
    # say why beside it. ExcludeRulesByPath turns rules off under one folder only, as
    # folder = rule names; say why beside each. Baseline names the file
    # Update-AnalyzerBaseline.ps1 writes, or '' for none.
    Analyzer = @{
        Paths              = @()     # for example @('source', 'scripts')
        Exclude            = @('*.Tests.ps1')
        ExcludeRules       = @()
        ExcludeRulesByPath = @{}     # for example @{ 'scripts' = @('PSAvoidUsingWriteHost') }
        Baseline           = ''      # for example 'gate/analyzer-baseline.psd1'
    }

    # GK04. A folder of Pester tests that read source text, or '' for none.
    StaticTests = ''

    # GK05 to GK07. This repository's gitleaks config, or '' for the kit's default
    # (tools/gate/Config/gitleaks.toml). Start from tools/gate/Templates/gitleaks.toml.
    Gitleaks = ''

    # GK05 to GK07. The file of gitleaks fingerprints to ignore, or '' for
    # .gitleaksignore at the repository root. Fingerprints stay relative to the root
    # wherever the file sits.
    GitleaksIgnore = ''   # for example 'Gate/gitleaksignore'

    # GK07 and GK15. This repository's message patterns, or '' for the kit's default
    # (tools/gate/Config/message-patterns.psd1). Start from
    # tools/gate/Templates/message-patterns.psd1.
    MessagePatterns = ''

    # GK08. The documented agent permission rules, or '' when no agent settings file is
    # committed. Start from tools/gate/Templates/agent-permissions.psd1.
    Permissions = ''

    # GK10. Record is the file Invoke-ModelReview.ps1 writes. Exempt lists files whose
    # change alone needs no review. The evidence record (GK12) is exempt already.
    Review = @{
        Record = 'Review/LastReview.json'
        Exempt = @()
    }

    # GK09. Manifest holds ModuleVersion; Changelog has '## [x.y.z]' release headings;
    # NotesFiles each hold a 'Version : x.y.z' line. With -Base, tags are TagPrefix plus
    # the version, and a change to a PackageInputs path (a file, or a folder ending in /)
    # under a version already tagged fails until the version is bumped.
    Version = @{
        Manifest      = ''
        Changelog     = ''
        NotesFiles    = @()
        TagPrefix     = 'v'
        PackageInputs = @()
    }

    # GK11. A script that runs the unit tests and exits 0 only when they pass. It owns
    # its own coverage floor.
    Unit = @{
        Script = ''
    }

    # GK12. Script runs the tests CI cannot run (for example integration tests against
    # a local database) and exits 0 only when they pass. Invoke-EvidenceRun.ps1 runs it
    # and writes Record. When a branch changes a Paths entry (a file, or a folder ending
    # in /), the record must show a passing run on a clean tree, with nothing but the
    # evidence and review records changed after it.
    Evidence = @{
        Script = ''        # for example 'scripts/Invoke-IntegrationTest.ps1'
        Record = 'Evidence/LastRun.json'
        Paths  = @()       # for example @('source/')
    }

    # GK13. Manifest is the module manifest as it is published; its FileList must name
    # every file in its folder. Build is a script that writes that folder first, or ''
    # when the manifest is in the source tree.
    Package = @{
        Manifest = ''      # for example 'source/MyModule/MyModule.psd1'
        Build    = ''      # for example 'scripts/Build-Module.ps1'
    }

    # GK14. Export-AgentInstruction.ps1 joins Sources, in order, into Output under a
    # header titled Title.
    Instructions = @{
        Output  = 'AGENTS.md'
        Title   = 'Agent instructions'
        Sources = @()      # for example @('docs/standards/coding.md', 'docs/standards/testing.md')
    }

    # GK15. Files and folders (ending in /) the file scan skips, such as test fixtures
    # that hold sample values on purpose.
    Files = @{
        Exclude = @()      # for example @('tests/fixtures/')
    }

    # The checks the pre-push hook (-Quick) skips; CI runs them. Any of GK03, GK04,
    # GK09, GK14 and GK15. The config, tool, secret and permission checks always run.
    Quick = @('GK03')
}
