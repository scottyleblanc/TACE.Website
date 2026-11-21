@{
    # PSScriptAnalyzer settings the gate applies (check GK03, rule AN-001). Pinned to
    # PSScriptAnalyzer 1.25.0 (Docs/PREREQUISITES.md).
    #
    # The gate adds the custom rules in Analyzer/Rules (AN-002 to AN-018) and any
    # ExcludeRules a repository lists in gate.config.psd1. Which folders are analyzed
    # is set by the repository's gate.config.psd1, not here.
    #
    # Every finding fails, Information included, unless the repository's analyzer
    # baseline already holds it (AN-001). A justified exception is a
    # SuppressMessageAttribute with a Justification at the narrowest scope that covers
    # it.

    Severity = @('Error', 'Warning', 'Information')

    IncludeDefaultRules = $true

    ExcludeRules = @(
        # PowerShell 7 writes UTF-8 without a BOM by default. This rule fires on any
        # non-ASCII character in a file without a BOM, which is a false positive there.
        'PSUseBOMForUnicodeEncodedFile'
    )
}
