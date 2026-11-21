@{
    # Commit message patterns for gate check GK07 (rule CM-001). Copy into the
    # repository (for example gate/message-patterns.psd1) and name the copy in
    # gate.config.psd1 under MessagePatterns. The copy replaces the kit's default, so
    # keep the default entries below and add this repository's own.
    #
    # Each entry: Id and Title name the check; Pattern is the regular expression; Allow,
    # when not empty, is a regular expression for matched values that are acceptable.

    Patterns = @(
        @{
            Id      = 'CM-001'
            Title   = 'no AWS access key ID'
            Pattern = '\b(AKIA|ASIA)[A-Z0-9]{16}\b'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no private key block'
            Pattern = '-----BEGIN [A-Z ]*PRIVATE KEY-----'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no local user-profile path'
            Pattern = '(?i)\b[A-Z]:[\\/]{1,2}Users[\\/]{1,2}[A-Za-z0-9._-]+|(?<![\w.])/Users/[A-Za-z0-9._-]+'
            Allow   = ''
        }

        # Examples of repository entries. Uncomment and adjust.
        #
        # @{
        #     Id      = 'CM-001'
        #     Title   = 'no email address outside the reserved example domains'
        #     Pattern = '[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'
        #     Allow   = '@example\.(com|org|net)$|@users\.noreply\.github\.com$'
        # }
        # @{
        #     Id      = 'CM-001'
        #     Title   = 'no AWS account ID'
        #     Pattern = '(?<![\w.\-])\d{12}(?![\w.\-])'
        #     Allow   = ''
        # }
    )
}
