# Runbook — Stage 5: DNS Cutover

## Overview

Migrate tacedata.ca from Websavers DNS to AWS Route 53. Attach the custom domain
and ACM SSL certificate to the CloudFront distribution. Update the site baseURL.

**Registrar:** Websavers (stays here — domain registration not transferred)
**DNS:** AWS Route 53 (authoritative after nameserver change)
**SSL:** AWS ACM (us-east-1, attached to CloudFront)

---

## Architecture

```mermaid
graph TD
    subgraph Websavers
        REG[Domain Registrar\ntacedata.ca]
    end

    subgraph AWS
        R53[Route 53\nHosted Zone\nREDACTED_R53_ZONE_ID]
        ACM[ACM Certificate\nus-east-1]
        CF[CloudFront\nREDACTED_CF_DIST_ID]
        S3[S3 Bucket\nHugo static files]
    end

    subgraph Fastmail
        MX[Email\nscott.leblanc@tacedata.ca]
    end

    subgraph GitHub
        GHA[GitHub Actions\nbuild + deploy]
    end

    REG -->|NS delegation| R53
    R53 -->|A alias| CF
    R53 -->|CNAME www| CF
    R53 -->|MX records| MX
    ACM -->|attached to| CF
    CF -->|OAC| S3
    GHA -->|s3 sync| S3
```

---

## AWS Resources

| Resource | Value |
|---|---|
| Route 53 hosted zone | `REDACTED_R53_ZONE_ID` |
| ACM certificate ARN | `arn:aws:acm:us-east-1:REDACTED_AWS_ACCOUNT_ID:certificate/REDACTED_ACM_CERT_ID` |
| CloudFront distribution | `REDACTED_CF_DIST_ID` |
| CloudFront domain | `REDACTED_CF_DOMAIN` |
| AWS profile | `tace-aws-admin` |

---

## Route 53 Nameservers

These are entered in Websavers under domain registration → Nameservers:

```
ns-196.awsdns-24.com
ns-977.awsdns-58.net
ns-1108.awsdns-10.org
ns-1726.awsdns-23.co.uk
```

---

## DNS Records in Route 53

Records added to hosted zone `REDACTED_R53_ZONE_ID`:

| Name | Type | Value |
|---|---|---|
| `tacedata.ca` | MX 10 | `in1-smtp.messagingengine.com.` |
| `tacedata.ca` | MX 20 | `in2-smtp.messagingengine.com.` |
| `tacedata.ca` | TXT | `v=spf1 include:spf.messagingengine.com ?all` |
| `_dmarc.tacedata.ca` | TXT | `v=DMARC1; p=quarantine; adkim=s; aspf=s` |
| `fm1._domainkey.tacedata.ca` | CNAME | `fm1.tacedata.ca.dkim.fmhosted.com.` |
| `fm2._domainkey.tacedata.ca` | CNAME | `fm2.tacedata.ca.dkim.fmhosted.com.` |
| `fm3._domainkey.tacedata.ca` | CNAME | `fm3.tacedata.ca.dkim.fmhosted.com.` |
| `www.tacedata.ca` | CNAME | `REDACTED_CF_DOMAIN.` |
| `tacedata.ca` | A (alias) | CloudFront distribution — added after cert issued |
| `_e2a12bc48260c6dc74c0eaf3ccea3a0c.tacedata.ca` | CNAME | ACM validation record |
| `_9b0a3a566c55cb82061462b6eb668dcb.www.tacedata.ca` | CNAME | ACM validation record |

---

## Step-by-Step Procedure

### Step 1 — Create Route 53 hosted zone (complete)

```powershell
aws route53 create-hosted-zone `
  --name tacedata.ca `
  --caller-reference "tacedata-$(Get-Date -Format 'yyyyMMddHHmmss')" `
  --profile tace-aws-admin `
  --query '{HostedZoneId:HostedZone.Id,NameServers:DelegationSet.NameServers}'
```

### Step 2 — Add DNS records (complete)

```powershell
aws route53 change-resource-record-sets `
  --hosted-zone-id REDACTED_R53_ZONE_ID `
  --change-batch "file://config/route53-records.json" `
  --profile tace-aws-admin
```

### Step 3 — Request ACM certificate (complete)

```powershell
aws acm request-certificate `
  --domain-name tacedata.ca `
  --subject-alternative-names www.tacedata.ca `
  --validation-method DNS `
  --region us-east-1 `
  --profile tace-aws-admin
```

### Step 4 — Add ACM validation records to Route 53 (complete)

```powershell
aws route53 change-resource-record-sets `
  --hosted-zone-id REDACTED_R53_ZONE_ID `
  --change-batch "file://config/route53-acm-validation.json" `
  --profile tace-aws-admin
```

### Step 5 — Change nameservers at Websavers (complete)

Websavers → Domain Management → tacedata.ca → Name Servers & DNS
Select: "Host my DNS records elsewhere"
Enter the 4 Route 53 nameservers listed above.

### Step 6 — Poll for certificate issuance

```powershell
do {
    $status = aws acm describe-certificate `
        --certificate-arn "arn:aws:acm:us-east-1:REDACTED_AWS_ACCOUNT_ID:certificate/REDACTED_ACM_CERT_ID" `
        --region us-east-1 `
        --profile tace-aws-admin `
        --query 'Certificate.Status' `
        --output text
    Write-Host "$(Get-Date -Format 'HH:mm:ss') — $status"
    if ($status -eq 'ISSUED') { break }
    Start-Sleep -Seconds 30
} while ($true)
```

### Step 7 — Attach domain and certificate to CloudFront

Get current ETag:

```powershell
aws cloudfront get-distribution-config `
  --id REDACTED_CF_DIST_ID `
  --profile tace-aws-admin `
  --query 'ETag' `
  --output text
```

Update distribution config to add:
- Aliases: `tacedata.ca`, `www.tacedata.ca`
- ACM certificate ARN (above)
- SSL support method: `sni-only`
- Minimum protocol: `TLSv1.2_2021`

```powershell
aws cloudfront update-distribution `
  --id REDACTED_CF_DIST_ID `
  --if-match <ETag> `
  --distribution-config "file://config/dist-config-updated.json" `
  --profile tace-aws-admin
```

### Step 8 — Add A alias record for tacedata.ca root

```powershell
aws route53 change-resource-record-sets `
  --hosted-zone-id REDACTED_R53_ZONE_ID `
  --change-batch "file://config/route53-alias.json" `
  --profile tace-aws-admin
```

### Step 9 — Update SITE_URL GitHub variable

GitHub repo → Settings → Secrets and variables → Actions → Variables
Update `SITE_URL` from `https://REDACTED_CF_DOMAIN` to `https://tacedata.ca`

### Step 10 — Trigger deploy

```powershell
git commit --allow-empty -m "chore: trigger deploy for domain cutover"
git push origin main
```

### Step 11 — Validate

```powershell
# Check DNS resolution
nslookup tacedata.ca
nslookup www.tacedata.ca

# Check certificate
aws acm describe-certificate `
  --certificate-arn "arn:aws:acm:us-east-1:REDACTED_AWS_ACCOUNT_ID:certificate/REDACTED_ACM_CERT_ID" `
  --region us-east-1 `
  --profile tace-aws-admin `
  --query 'Certificate.Status'
```

- Browse to `https://tacedata.ca` — site loads, padlock shows
- Browse to `https://www.tacedata.ca` — site loads
- Send test email to `scott.leblanc@tacedata.ca` — confirm receipt in Fastmail

---

## Rollback

If anything goes wrong before the site is confirmed working:

1. Revert nameservers in Websavers back to `ns80.websaversdns.com` / `ns81.websaversdns.com`
2. DNS reverts within TTL period (~5 minutes at 300s TTL)
3. WordPress site on Websavers resumes serving tacedata.ca
