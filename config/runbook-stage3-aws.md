# Runbook — Stage 3 AWS Infrastructure

Commands used to build the Stage 3 AWS infrastructure.
Run from the repo root unless otherwise noted.
All commands use the `tace-aws-admin` AWS profile.

---

## Prerequisites

- AWS CLI installed and configured
- Profile `tace-aws-admin` available (`aws sts get-caller-identity --profile tace-aws-admin`)
- GitHub repo: `scottyleblanc/TACE.Website`
- AWS account: `REDACTED_AWS_ACCOUNT_ID`
- Region: `ca-central-1`

---

## 1. Verify S3 Bucket Settings

Bucket `REDACTED_S3_BUCKET` must have public access blocked and no static website hosting.

```powershell
aws s3api get-public-access-block `
  --bucket REDACTED_S3_BUCKET `
  --region ca-central-1 `
  --profile tace-aws-admin

aws s3api get-bucket-website `
  --bucket REDACTED_S3_BUCKET `
  --region ca-central-1 `
  --profile tace-aws-admin

aws s3api get-bucket-policy `
  --bucket REDACTED_S3_BUCKET `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

## 2. Create CloudFront Distribution

Done via AWS console:
- Origin: `REDACTED_S3_BUCKET`
- Origin path: `/tacedata-site`
- Private S3 access via OAC (Origin Access Control)
- Default root object: `index.html`
- WAF: disabled
- Pricing: Free tier / Pay as you go

**Distribution details:**
- Distribution ID: `REDACTED_CF_DIST_ID`
- Domain: `REDACTED_CF_DOMAIN`
- ARN: `arn:aws:cloudfront::REDACTED_AWS_ACCOUNT_ID:distribution/REDACTED_CF_DIST_ID`

---

## 3. Apply S3 Bucket Policy

Allows CloudFront OAC to read from the `tacedata-site/` prefix only.
Policy file: `config/s3.bucket.policy.json`

```powershell
aws s3api put-bucket-policy `
  --bucket REDACTED_S3_BUCKET `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --policy file://config/s3.bucket.policy.json
```

Verify:

```powershell
aws s3api get-bucket-policy `
  --bucket REDACTED_S3_BUCKET `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --query Policy `
  --output text
```

---

## 4. Create GitHub Actions OIDC Provider

Only needs to be done once per AWS account.

```powershell
aws iam create-open-id-connect-provider `
  --url https://token.actions.githubusercontent.com `
  --client-id-list sts.amazonaws.com `
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 `
  --profile tace-aws-admin
```

Verify:

```powershell
aws iam list-open-id-connect-providers `
  --profile tace-aws-admin `
  --query 'OpenIDConnectProviderList[*].Arn' `
  --output table
```

---

## 5. Create IAM Role

Trust policy: `config/iam-trust-policy.json`
Permissions policy: `config/iam-permissions-policy.json`

```powershell
aws iam create-role `
  --role-name REDACTED_DEPLOY_ROLE `
  --assume-role-policy-document file://config/iam-trust-policy.json `
  --profile tace-aws-admin

aws iam put-role-policy `
  --role-name REDACTED_DEPLOY_ROLE `
  --policy-name tacedata-deploy-policy `
  --policy-document file://config/iam-permissions-policy.json `
  --profile tace-aws-admin
```

**Role ARN:** `arn:aws:iam::REDACTED_AWS_ACCOUNT_ID:role/REDACTED_DEPLOY_ROLE`

---

## 6. GitHub Secret

Add to `scottyleblanc/TACE.Website` → Settings → Secrets and variables → Actions:

| Secret name | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::REDACTED_AWS_ACCOUNT_ID:role/REDACTED_DEPLOY_ROLE` |

---

## 7. GitHub Actions Workflow

File: `.github/workflows/deploy.yml`

Triggers on push to `main`. Steps:
1. Checkout (with submodules for Blowfish theme)
2. Build Hugo Extended v0.158.0 with `--minify`
3. Authenticate to AWS via OIDC (no long-lived credentials)
4. Sync `hugo-eval/public/` to `s3://REDACTED_S3_BUCKET/tacedata-site/`
5. Invalidate CloudFront distribution `REDACTED_CF_DIST_ID`
