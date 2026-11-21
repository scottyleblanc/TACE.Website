@{
    # Message and file patterns for gate checks GK07 (rule CM-001, commit messages) and
    # GK15 (rule FP-001, tracked files). This repository is public, so this file is too:
    # every entry describes the format of an identifier and never holds a real value.
    # Real values belong in the private repository only.
    #
    # Each entry: Id and Title name the check; Pattern is the regular expression; Allow,
    # when not empty, is a regular expression for matched values that are acceptable.
    # The first three entries are the kit's defaults (tools/gate/Templates/message-patterns.psd1).

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

        # AWS identifiers.
        @{
            Id      = 'CM-001'
            Title   = 'no AWS account ID'
            Pattern = '(?<![\w.\-])\d{12}(?![\w.\-])'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no CloudFront distribution ID'
            Pattern = '\bE(?=[A-Z0-9]*\d)[A-Z0-9]{12,13}\b'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no CloudFront domain'
            Pattern = '(?i)\b[a-z0-9]{12,14}\.cloudfront\.net\b'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no API Gateway ID'
            Pattern = '(?i)\b[a-z0-9]{10}\.execute-api\.'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no Route 53 hosted zone ID'
            Pattern = '\bZ(?=[A-Z0-9]*\d)[A-Z0-9]{9,31}\b'
            Allow   = '^Z2FDTNDATAQYW2$'   # CloudFront's own hosted zone ID: one public AWS value for every account
        }
        @{
            Id      = 'CM-001'
            Title   = 'no Secrets Manager ARN suffix'
            Pattern = ':secret:[A-Za-z0-9/_+=.@\-]+-[A-Za-z0-9]{6}\b'
            Allow   = ''
        }

        # Cognito and OAuth identifiers.
        @{
            Id      = 'CM-001'
            Title   = 'no Cognito user pool ID'
            Pattern = '\b[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]{9}\b'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no Cognito hosted UI domain'
            Pattern = '(?i)\b[a-z0-9\-]+\.auth\.[a-z]{2}-[a-z]+-\d\.amazoncognito\.com\b'
            Allow   = ''
        }
        @{
            Id      = 'CM-001'
            Title   = 'no Google OAuth client ID'
            Pattern = '\b\d+-[a-z0-9]{32}\.apps\.googleusercontent\.com\b'
            Allow   = ''
        }

        # A UUID: an ACM certificate ID, a Cognito sub or another resource's unique ID.
        @{
            Id      = 'CM-001'
            Title   = 'no UUID'
            Pattern = '(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'
            Allow   = ''
        }

        # Email addresses: the site's own domain and the reserved example domains only.
        @{
            Id      = 'CM-001'
            Title   = 'no email address outside the site domain and the example domains'
            Pattern = '[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'
            # support@github.com is the address in every Dependabot commit's Signed-off-by line.
            Allow   = '(?i)@tacedata\.ca$|@example\.(com|org|net)$|@users\.noreply\.github\.com$|^noreply@anthropic\.com$|^support@github\.com$'
        }
    )
}
