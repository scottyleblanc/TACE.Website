# Runbook — Economic Indicators Lambda (Stages 3 / 5 / 6)

One-time setup for the econ dashboard server-side data pipeline.
Run from the repo root unless otherwise noted.
All commands use the `tace-aws-admin` AWS profile.

**Windows note:** `file://` path arguments fail with the AWS CLI on Windows (Git Bash converts
the path). Use inline JSON strings for all `--policy-document` and `--assume-role-policy-document`
arguments. Commands below use inline JSON where applicable.

---

## Prerequisites

- AWS CLI installed and configured
- Profile `tace-aws-admin` available
- Twelve Data API key (free tier — register at twelvedata.com)
- FRED API key (free tier — register at fred.stlouisfed.org)
- Lambda function code in `lambda/indicators.py` (deployed via GitHub Actions after initial setup)

---

## Stage 3 Setup — Core Lambda Pipeline

### 1. Create Lambda Execution Role

Trust policy: `config/lambda-trust-policy.json`

```powershell
aws iam create-role `
  --role-name <ECON_LAMBDA_EXECUTION_ROLE_NAME> `
  --assume-role-policy-document file://config/lambda-trust-policy.json `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Apply the permissions policy (inline JSON — see `config/lambda-execution-policy.json` for the
current policy; replace placeholders before running):

```powershell
aws iam put-role-policy `
  --role-name <ECON_LAMBDA_EXECUTION_ROLE_NAME> `
  --policy-name econ-lambda-execution-policy `
  --policy-document '<JSON from config/lambda-execution-policy.json with placeholders replaced>' `
  --profile tace-aws-admin
```

Note the role ARN from the create-role output:
`arn:aws:iam::<AWS_ACCOUNT_ID>:role/<ECON_LAMBDA_EXECUTION_ROLE_NAME>`

---

### 2. Create Lambda Function

Package and deploy the initial function code:

```powershell
Compress-Archive -Path lambda/indicators.py -DestinationPath function.zip -Force

aws lambda create-function `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --runtime python3.12 `
  --role arn:aws:iam::<AWS_ACCOUNT_ID>:role/<ECON_LAMBDA_EXECUTION_ROLE_NAME> `
  --handler indicators.handler `
  --zip-file fileb://function.zip `
  --timeout 120 `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

### 3. Set Environment Variables

All sensitive values set here — never in source code.

```powershell
aws lambda update-function-configuration `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --environment "Variables={TD_API_KEY=<TWELVE_DATA_API_KEY>,FRED_API_KEY=<FRED_API_KEY>,S3_BUCKET=<S3_BUCKET_NAME>,S3_KEY=tacedata-site/data/indicators.json,DYNAMODB_TABLE=econ-indicators-history,SNS_TOPIC_ARN=<SNS_TOPIC_ARN>}" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Note: `DYNAMODB_TABLE` and `SNS_TOPIC_ARN` are added in Stages 5 and 6. Include them from the
start if setting up all stages at once.

---

### 4. Create EventBridge Schedule

Using EventBridge Rules (not Scheduler — no separate execution role required).

```powershell
aws events put-rule `
  --name econ-indicators-30min `
  --schedule-expression "cron(0/30 * * * ? *)" `
  --state ENABLED `
  --region ca-central-1 `
  --profile tace-aws-admin

aws lambda add-permission `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --statement-id EventBridgeInvoke `
  --action lambda:InvokeFunction `
  --principal events.amazonaws.com `
  --source-arn arn:aws:events:ca-central-1:<AWS_ACCOUNT_ID>:rule/econ-indicators-30min `
  --region ca-central-1 `
  --profile tace-aws-admin

aws events put-targets `
  --rule econ-indicators-30min `
  --targets '[{"Id":"<ECON_LAMBDA_FUNCTION_NAME>","Arn":"arn:aws:lambda:ca-central-1:<AWS_ACCOUNT_ID>:function:<ECON_LAMBDA_FUNCTION_NAME>"}]' `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

### 5. Add CloudFront Cache Behavior for /data/*

In the AWS CloudFront console:
- Distribution: `<CLOUDFRONT_DISTRIBUTION_ID>`
- Add behavior: Path pattern `data/*` (no leading slash — CloudFront rejects `/data/*`)
- Cache policy: Caching Disabled
- Origin: same S3 origin as the default behavior
- Compress: Yes (optional — not shown in all console views, safe to skip)

This ensures visitors always get data from the most recent Lambda run (max 30 minutes stale).

---

### 6. Add GitHub Actions Variable

In `scottyleblanc/TACE.Website` → Settings → Variables → Actions:

| Variable name | Value |
|---|---|
| `ECON_LAMBDA_FUNCTION_NAME` | `<ECON_LAMBDA_FUNCTION_NAME>` |

The GitHub Actions deploy workflow uses this variable when running `aws lambda update-function-code`.

---

### 7. Update Deploy Role Permissions

The GitHub Actions deploy role needs `lambda:UpdateFunctionCode`. Update the inline policy:

```powershell
aws iam put-role-policy `
  --role-name <GITHUB_DEPLOY_ROLE_NAME> `
  --policy-name tacedata-deploy-policy `
  --policy-document file://config/iam-permissions-policy.json `
  --profile tace-aws-admin
```

---

### 8. Test Lambda Manually

```powershell
aws lambda invoke `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --payload '{}' `
  --cli-binary-format raw-in-base64-out `
  /tmp/response.json

Get-Content /tmp/response.json

# Verify S3 write
aws s3 ls s3://<S3_BUCKET_NAME>/tacedata-site/data/ `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

### 9. Validate Dashboard

1. Load `https://tacedata.ca/projects/econ/interest-rate/`
2. Verify all eight cards render with live data
3. Verify `Generated:` timestamp matches the Lambda run time
4. Verify no error banner appears

---

## Stage 5 Setup — DynamoDB Historical Storage

### 10. Create DynamoDB Table

```powershell
aws dynamodb create-table `
  --table-name econ-indicators-history `
  --attribute-definitions `
    AttributeName=pk,AttributeType=S `
    AttributeName=ts,AttributeType=S `
  --key-schema `
    AttributeName=pk,KeyType=HASH `
    AttributeName=ts,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Enable TTL (auto-expires items older than 1 year):

```powershell
aws dynamodb update-time-to-live `
  --table-name econ-indicators-history `
  --time-to-live-specification Enabled=true,AttributeName=ttl `
  --region ca-central-1 `
  --profile tace-aws-admin
```

### 11. Update Lambda Execution Role Policy

Apply the current policy from `config/lambda-execution-policy.json` as inline JSON (replace
`<AWS_ACCOUNT_ID>` with the real value):

```powershell
aws iam put-role-policy `
  --role-name <ECON_LAMBDA_EXECUTION_ROLE_NAME> `
  --policy-name econ-lambda-execution-policy `
  --policy-document '<JSON from config/lambda-execution-policy.json with placeholders replaced>' `
  --profile tace-aws-admin
```

Changes from Stage 3 policy:
- S3 resource widened from `data/indicators.json` to `data/*` (covers history files)
- Added `dynamodb:PutItem` and `dynamodb:Query` on `econ-indicators-history`

### 12. Add DYNAMODB_TABLE Environment Variable

```powershell
aws lambda update-function-configuration `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --environment "Variables={TD_API_KEY=<TWELVE_DATA_API_KEY>,FRED_API_KEY=<FRED_API_KEY>,S3_BUCKET=<S3_BUCKET_NAME>,S3_KEY=tacedata-site/data/indicators.json,DYNAMODB_TABLE=econ-indicators-history}" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

### 13. Backfill Historical Data (one-time)

Run the backfill script to populate 180 days of history from upstream APIs:

```powershell
$env:TD_API_KEY   = "<TWELVE_DATA_API_KEY>"
$env:FRED_API_KEY = "<FRED_API_KEY>"
python scripts/backfill_history.py
```

The script is non-destructive — skips any date already present in DynamoDB.

### 14. Generate History Files

History files are generated on the midnight UTC Lambda run. To trigger immediately:

```powershell
aws lambda invoke `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --payload '{"force_history": true}' `
  --cli-binary-format raw-in-base64-out `
  /tmp/response.json

# Verify both history files exist
aws s3 ls s3://<S3_BUCKET_NAME>/tacedata-site/data/ `
  --region ca-central-1 `
  --profile tace-aws-admin
```

### 15. Validate Stage 5

1. Invoke Lambda and confirm `{"statusCode": 200, "errors": {}}`
2. Verify DynamoDB snapshot written:
```powershell
aws dynamodb query `
  --table-name econ-indicators-history `
  --key-condition-expression "pk = :pk" `
  --expression-attribute-values '{":pk":{"S":"SNAPSHOT"}}' `
  --limit 1 `
  --no-scan-index-forward `
  --region ca-central-1 `
  --profile tace-aws-admin
```
3. Verify `history-90d.json` and `history-180d.json` exist in S3
4. Load dashboard — verify 3M and 6M period buttons render sparklines

---

## Stage 6 Setup — Threshold Alerting

### 16. Create SNS Topic

```powershell
aws sns create-topic `
  --name econ-indicators-alerts `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Note the TopicArn from the output.

### 17. Subscribe Email to Topic

```powershell
aws sns subscribe `
  --topic-arn <SNS_TOPIC_ARN> `
  --protocol email `
  --notification-endpoint <YOUR_EMAIL> `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Confirm the subscription via the email AWS sends before proceeding.

### 18. Update Lambda Execution Role Policy

Apply the current `config/lambda-execution-policy.json` as inline JSON with `<AWS_ACCOUNT_ID>`
replaced. Changes from Stage 5 policy:
- Added `sns:Publish` on `econ-indicators-alerts`

### 19. Add SNS_TOPIC_ARN Environment Variable

```powershell
aws lambda update-function-configuration `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --environment "Variables={TD_API_KEY=<TWELVE_DATA_API_KEY>,FRED_API_KEY=<FRED_API_KEY>,S3_BUCKET=<S3_BUCKET_NAME>,S3_KEY=tacedata-site/data/indicators.json,DYNAMODB_TABLE=econ-indicators-history,SNS_TOPIC_ARN=<SNS_TOPIC_ARN>}" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

### 20. Validate Stage 6

1. Invoke Lambda and confirm `{"statusCode": 200, "errors": {}}`
2. To test alerting without waiting for a real crossing: temporarily lower a threshold in the
   code (e.g. change `0.30` to `0.001` for the 5yr yield trigger), deploy, invoke, verify email
   arrives, then revert and redeploy
