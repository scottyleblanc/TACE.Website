# Runbook — CloudWatch Availability Monitoring

Commands used to set up availability monitoring for tacedata.ca.
Run from the repo root unless otherwise noted.
All commands use the `tace-aws-admin` AWS profile.

---

## Prerequisites

- AWS CLI installed and configured
- Profile `tace-aws-admin` available (`aws sts get-caller-identity --profile tace-aws-admin`)
- AWS account: `<AWS_ACCOUNT_ID>`
- Region: `ca-central-1`

---

## Resources Created

| Resource | Name / ID |
|---|---|
| S3 bucket (canary artifacts) | `tacedata-canary-artifacts` |
| IAM role | `<CANARY_ROLE_NAME>` |
| IAM role ARN | `arn:aws:iam::<AWS_ACCOUNT_ID>:role/<CANARY_ROLE_NAME>` |
| Canary name | `tacedata-availability` |
| CloudWatch Alarm | `tacedata-availability-alarm` |
| SNS Topic ARN | `arn:aws:sns:ca-central-1:<AWS_ACCOUNT_ID>:<SNS_TOPIC_NAME>` |
| SNS Subscription ARN | `arn:aws:sns:ca-central-1:<AWS_ACCOUNT_ID>:<SNS_TOPIC_NAME>:<SNS_SUBSCRIPTION_ID>` |
| Alert email | `aws.cloudwatch@tacedata.ca` |

---

## 1. Create S3 Bucket for Canary Artifacts

A separate bucket from the site content bucket — keeps artifact storage isolated
from site content and avoids bucket policy complications.

```powershell
aws s3api create-bucket `
  --bucket tacedata-canary-artifacts `
  --region ca-central-1 `
  --create-bucket-configuration LocationConstraint=ca-central-1 `
  --profile tace-aws-admin

aws s3api put-public-access-block `
  --bucket tacedata-canary-artifacts `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## 2. Create IAM Role for Canary Execution

The canary runs as a Lambda function. Needs permission to write artifacts to S3,
publish metrics to CloudWatch, and write logs.

Trust policy: `config/canary-trust-policy.json`
Permissions policy: `config/canary-permissions-policy.json`

```powershell
aws iam create-role `
  --role-name <CANARY_ROLE_NAME> `
  --assume-role-policy-document file://config/canary-trust-policy.json `
  --profile tace-aws-admin

aws iam put-role-policy `
  --role-name <CANARY_ROLE_NAME> `
  --policy-name tacedata-canary-policy `
  --policy-document file://config/canary-permissions-policy.json `
  --profile tace-aws-admin
```

---

## 3. Create CloudWatch Synthetics Canary

Canary script: `config/canary-script.js`

The script hits `https://tacedata.ca` and validates HTTP 2xx. The CloudFront WAF
requires a browser-like User-Agent header — bare Lambda requests return 403.

Package the script:

```powershell
New-Item -ItemType Directory -Path "config/canary-zip/nodejs/node_modules" -Force
Copy-Item "config/canary-script.js" "config/canary-zip/nodejs/node_modules/canary-script.js" -Force
Compress-Archive -Path "config/canary-zip/nodejs" -DestinationPath "config/canary.zip" -Force
```

Create the canary (base64-encode the zip inline — `fileb://` does not work with `--code`):

```powershell
$zipBase64 = [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes("$PWD/config/canary.zip"))
$schedule = '{"Expression":"rate(5 minutes)","DurationInSeconds":0}'
$runconfig = '{"TimeoutInSeconds":60}'
$code = "{`"ZipFile`":`"$zipBase64`",`"Handler`":`"canary-script.handler`"}"

aws synthetics create-canary `
  --name tacedata-availability `
  --code $code `
  --artifact-s3-location s3://tacedata-canary-artifacts/canary-runs/ `
  --execution-role-arn arn:aws:iam::<AWS_ACCOUNT_ID>:role/<CANARY_ROLE_NAME> `
  --schedule $schedule `
  --run-config $runconfig `
  --success-retention-period-in-days 7 `
  --failure-retention-period-in-days 31 `
  --runtime-version syn-nodejs-puppeteer-9.1 `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --query 'Canary.Status.State' `
  --output text
```

Start the canary:

```powershell
aws synthetics start-canary `
  --name tacedata-availability `
  --region ca-central-1 `
  --profile tace-aws-admin
```

To update the canary script after changes:

```powershell
Copy-Item "config/canary-script.js" "config/canary-zip/nodejs/node_modules/canary-script.js" -Force
Compress-Archive -Path "config/canary-zip/nodejs" -DestinationPath "config/canary.zip" -Force

$zipBase64 = [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes("$PWD/config/canary.zip"))
$code = "{`"ZipFile`":`"$zipBase64`",`"Handler`":`"canary-script.handler`"}"

aws synthetics update-canary `
  --name tacedata-availability `
  --code $code `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

## 4. Create CloudWatch Alarm

Triggers after 2 consecutive 5-minute periods where success rate drops below 100%.
Sends alert on failure and recovery.

```powershell
aws cloudwatch put-metric-alarm `
  --alarm-name tacedata-availability-alarm `
  --alarm-description "tacedata.ca availability — triggers on 2 consecutive canary failures" `
  --namespace CloudWatchSynthetics `
  --metric-name SuccessPercent `
  --dimensions Name=CanaryName,Value=tacedata-availability `
  --statistic Average `
  --period 300 `
  --evaluation-periods 2 `
  --threshold 100 `
  --comparison-operator LessThanThreshold `
  --treat-missing-data breaching `
  --alarm-actions arn:aws:sns:ca-central-1:<AWS_ACCOUNT_ID>:<SNS_TOPIC_NAME> `
  --ok-actions arn:aws:sns:ca-central-1:<AWS_ACCOUNT_ID>:<SNS_TOPIC_NAME> `
  --region ca-central-1 `
  --profile tace-aws-admin
```

---

## 5. Create SNS Topic and Email Subscription

```powershell
aws sns create-topic `
  --name <SNS_TOPIC_NAME> `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --query 'TopicArn' `
  --output text

aws sns subscribe `
  --topic-arn arn:aws:sns:ca-central-1:<AWS_ACCOUNT_ID>:<SNS_TOPIC_NAME> `
  --protocol email `
  --notification-endpoint aws.cloudwatch@tacedata.ca `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Click the confirmation link in the email sent to `aws.cloudwatch@tacedata.ca`.

Verify confirmed:

```powershell
aws sns get-subscription-attributes `
  --subscription-arn arn:aws:sns:ca-central-1:<AWS_ACCOUNT_ID>:<SNS_TOPIC_NAME>:<SNS_SUBSCRIPTION_ID> `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --query 'Attributes.PendingConfirmation' `
  --output text
```

Returns `false` when confirmed.

---

## 6. Validate

Confirm the canary is passing:

```powershell
aws synthetics get-canary-runs `
  --name tacedata-availability `
  --region ca-central-1 `
  --profile tace-aws-admin `
  --query 'CanaryRuns[0].Status.State' `
  --output text
```

Returns `PASSED` when healthy.

### Test alarm and recovery notifications

Force the alarm into ALARM state to verify the SNS email is delivered:

```powershell
aws cloudwatch set-alarm-state `
  --alarm-name tacedata-availability-alarm `
  --state-value ALARM `
  --state-reason "Manual test — verifying SNS notification delivery" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Check `aws.cloudwatch@tacedata.ca` for the alert email. Then reset to OK:

```powershell
aws cloudwatch set-alarm-state `
  --alarm-name tacedata-availability-alarm `
  --state-value OK `
  --state-reason "Manual test complete — resetting to OK" `
  --region ca-central-1 `
  --profile tace-aws-admin
```

Confirm the recovery notification is also received. Both directions confirmed working 2026-04-03.
