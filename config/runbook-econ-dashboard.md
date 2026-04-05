# Runbook — Economic Indicators Lambda (Stage 3)

One-time setup for the econ dashboard server-side data pipeline.
Run from the repo root unless otherwise noted.
All commands use the `tace-aws-admin` AWS profile.

---

## Prerequisites

- AWS CLI installed and configured
- Profile `tace-aws-admin` available
- Twelve Data API key (free tier — register at twelvedata.com)
- Lambda function code in `lambda/indicators.py` (deployed via GitHub Actions after initial setup)

---

## 1. Create Lambda Execution Role

Trust policy: `config/lambda-trust-policy.json`
Permissions policy: `config/lambda-execution-policy.json`

```powershell
aws iam create-role `
  --role-name <ECON_LAMBDA_EXECUTION_ROLE_NAME> `
  --assume-role-policy-document file://config/lambda-trust-policy.json `
  --region ca-central-1 `
  --profile tace-aws-admin

aws iam put-role-policy `
  --role-name <ECON_LAMBDA_EXECUTION_ROLE_NAME> `
  --policy-name econ-lambda-execution-policy `
  --policy-document file://config/lambda-execution-policy.json `
  --profile tace-aws-admin
```

Note the role ARN from the create-role output:
`arn:aws:iam::<AWS_ACCOUNT_ID>:role/<ECON_LAMBDA_EXECUTION_ROLE_NAME>`

---

## 2. Create Lambda Function

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

## 3. Set Environment Variables

Set the three required environment variables on the Lambda function.
`TD_API_KEY` is sensitive — set it here, never in source code.

```powershell
aws lambda update-function-configuration `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --environment "Variables={TD_API_KEY=<TWELVE_DATA_API_KEY>,S3_BUCKET=<S3_BUCKET_NAME>,S3_KEY=tacedata-site/data/indicators.json}" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

## 4. Create EventBridge Schedule

Triggers Lambda every 30 minutes. Using the scheduler (not EventBridge rules) for cron support.

```powershell
aws scheduler create-schedule `
  --name econ-indicators-30min `
  --schedule-expression "cron(0/30 * * * ? *)" `
  --flexible-time-window '{"Mode": "OFF"}' `
  --target "{\"Arn\": \"arn:aws:lambda:ca-central-1:<AWS_ACCOUNT_ID>:function:<ECON_LAMBDA_FUNCTION_NAME>\", \"RoleArn\": \"arn:aws:iam::<AWS_ACCOUNT_ID>:role/<SCHEDULER_EXECUTION_ROLE_NAME>\"}" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Alternatively, create a Lambda trigger via the Lambda console (Add trigger → EventBridge Scheduler).
The scheduler requires its own execution role with `lambda:InvokeFunction` permission.

---

## 5. Add CloudFront Cache Behavior for /data/*

In the AWS CloudFront console:
- Distribution: `<CLOUDFRONT_DISTRIBUTION_ID>`
- Add behavior: Path pattern `/data/*`
- Cache policy: Caching Disabled (or custom TTL: min=0, default=1800, max=1800)
- Origin: same S3 origin as the default behavior
- Compress: Yes

This ensures visitors always get data from the most recent Lambda run (max 30 minutes stale).

---

## 6. Add GitHub Actions Variable

In `scottyleblanc/TACE.Website` → Settings → Variables → Actions:

| Variable name | Value |
|---|---|
| `ECON_LAMBDA_FUNCTION_NAME` | `<ECON_LAMBDA_FUNCTION_NAME>` |

The GitHub Actions deploy workflow uses this variable when running `aws lambda update-function-code`.

---

## 7. Update Deploy Role Permissions

The GitHub Actions deploy role needs `lambda:UpdateFunctionCode` in addition to existing S3 and CloudFront permissions. Update the inline policy:

```powershell
aws iam put-role-policy `
  --role-name <GITHUB_DEPLOY_ROLE_NAME> `
  --policy-name tacedata-deploy-policy `
  --policy-document file://config/iam-permissions-policy.json `
  --profile tace-aws-admin
```

---

## 8. Test Lambda Manually

Invoke the Lambda and check the result:

```powershell
aws lambda invoke `
  --function-name <ECON_LAMBDA_FUNCTION_NAME> `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --log-type Tail `
  response.json

# Check response
Get-Content response.json

# Verify S3 write
aws s3 cp s3://<S3_BUCKET_NAME>/data/indicators.json - `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

## 9. Validate Dashboard

After a successful Lambda invocation:

1. Load `https://tacedata.ca/projects/econ/interest-rate/`
2. Verify all eight cards render with live data
3. Verify `Generated:` timestamp matches the Lambda run time
4. Verify no error banner appears
5. Simulate a failure: temporarily rename the S3 key and reload — error banner should appear with clear messaging
