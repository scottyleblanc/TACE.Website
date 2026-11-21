@{
    # Default patterns for check GK07 (rule CM-001): values that must never appear in a
    # commit message. gitleaks also reads each message; these catch values with a known
    # shape that its default rules do not.
    #
    # A repository with more to keep out (account identifiers, host names) copies
    # Templates/message-patterns.psd1, adds its own entries and names the copy in
    # gate.config.psd1 under MessagePatterns. The copy replaces this file.
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
            # A Windows or macOS user folder: the folder name is the account name.
            Pattern = '(?i)\b[A-Z]:[\\/]{1,2}Users[\\/]{1,2}[A-Za-z0-9._-]+|(?<![\w.])/Users/[A-Za-z0-9._-]+'
            Allow   = ''
        }
    )
}
