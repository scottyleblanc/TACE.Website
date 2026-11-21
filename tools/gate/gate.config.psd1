@{
    # The kit's own gate configuration: the kit is gated by itself (Docs/decisions.md,
    # DEC-006). See Templates/gate.config.psd1 for every key.

    SchemaVersion = 1

    Checks = @{
        # Off for the kit itself: its pull requests carry no model review record
        # (DEC-020). The template default stays on for target repositories.
        Review  = $false
        Version = $false
        Unit    = $false
        Files   = $true
    }

    Analyzer = @{
        Paths        = @('Scripts', 'Analyzer')
        Exclude      = @('*.Tests.ps1')
        ExcludeRules = @()
        Baseline     = ''
    }

    StaticTests     = 'Tests'
    Gitleaks        = ''
    MessagePatterns = ''
    Permissions     = ''

    Review = @{
        Record = 'Review/LastReview.json'
        Exempt = @()
    }

    # The checks the pre-push hook skips; .github/workflows/gate.yml runs them on every
    # pull request (DEC-020).
    Quick = @('GK03', 'GK04')
}
