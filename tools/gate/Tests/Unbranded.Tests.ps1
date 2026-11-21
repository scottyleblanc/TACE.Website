#Requires -Version 7.6

# Rule KT-001: the kit carries no owner branding and no identifiers from another
# repository's rule set. The kit is copied into other repositories, so a name or rule
# ID that belongs elsewhere would travel with it.
#
# The patterns are built with character classes so that this file does not contain the
# words it looks for.
#
# LICENSE is the one exception (DEC-010): it names the copyright holder, and is the only
# file that may.

BeforeDiscovery {
    $kitRoot = Split-Path -Path $PSScriptRoot -Parent
    $script:files = @(& git -C $kitRoot ls-files --cached --others --exclude-standard | Where-Object { $PSItem -ne 'LICENSE' } | ForEach-Object {
            @{ Relative = $PSItem; Full = Join-Path -Path $kitRoot -ChildPath $PSItem }
        })
}

BeforeAll {
    $script:patterns = @(
        @{ Name = 'owner name'; Regex = '(?i)\bt[a]ce\b|t[a]cedata' }
        @{ Name = 'database product name'; Regex = '(?i)\bor[a]cle\b' }
        @{ Name = 'copyright line'; Regex = '(?i)copyr[i]ght\s+(\(c\)|©)' }
        @{ Name = 'rule ID from another rule set'; Regex = '\b[CSTDI]-\d{2}\b' }
        @{ Name = 'unnumbered decision reference'; Regex = '(?i)\bdecision\s+\d+\b' }
        @{ Name = 'stage name from another project'; Regex = '(?i)\bst[a]ck\s+\d+\b' }
    )
}

Describe 'Unbranded kit' -Tag 'Static' {

    It 'finds the files to check' -TestCases @(@{ FileCount = $script:files.Count }) {
        $FileCount | Should -BeGreaterThan 10
    }

    It 'KT-001 <Relative> carries no branding' -ForEach $script:files {
        $text = [System.IO.File]::ReadAllText($Full)
        $hits = @(foreach ($pattern in $script:patterns) {
                foreach ($match in [regex]::Matches($text, $pattern.Regex)) {
                    $line = $text.Substring(0, $match.Index).Split("`n").Count
                    "line ${line}: $($pattern.Name)"
                }
            })
        ($hits -join "`n") | Should -BeNullOrEmpty
    }
}
