---
title: "OracleAwsRotation"
date: 2026-03-22
draft: false
tags: ["powershell", "aws", "oracle", "lambda", "secrets-manager"]
summary: "A PowerShell module and AWS Lambda function that automates Oracle credential rotation across EC2 instances using Secrets Manager and SSM Run Command."
---

## Problem

Manual Oracle password rotation at scale is operationally expensive and a
compliance liability. At 600 EC2 instances, each running Oracle and a Tomcat
application server, rotating credentials manually means RDP sessions,
properties file edits, and Tomcat restarts — repeated hundreds of times, with
no audit trail and no rollback if something goes wrong mid-rotation.

## Solution

A Lambda function drives the AWS Secrets Manager four-step rotation lifecycle.
A PowerShell module runs on each EC2 instance via SSM Run Command and handles
the Oracle and Tomcat operations. The two sides are deliberately separated:
Lambda owns the AWS lifecycle, PowerShell owns the instance.

Credentials never travel over the SSM channel. The EC2-side script retrieves
them directly from Secrets Manager using the instance role. A DynamoDB lock
table with TTL prevents concurrent Lambda invocations from corrupting a secret
mid-rotation.

## Architecture

```
EventBridge → Lambda (boto3)
                  |
            Read server manifest
            Acquire DynamoDB lock (lockOwner UUID)
            Write AWSPENDING to Secrets Manager
                  |
            SSM Run Command → EC2 (PowerShell)
                  |
            Retrieve credential from Secrets Manager (instance role)
            ALTER USER (Oracle XEPDB1)
            Update application.properties (Tomcat)
            Stop + Start Tomcat
                  |
            Lambda polls health endpoint
            Lambda tests Oracle connection
            finishSecret → AWSPENDING becomes AWSCURRENT
            Release DynamoDB lock
```

On any failure: rollback to AWSCURRENT, release lock, alert.

## Tech Used

- PowerShell 7 (module with 10 public functions, 173 Pester tests)
- Python 3.12 (Lambda handler via boto3)
- AWS Secrets Manager (rotation lifecycle)
- AWS Lambda + EventBridge (scheduling)
- AWS SSM Run Command (EC2 bridge)
- DynamoDB (rotation lock table)
- Oracle XE 21c (credential target)
- Apache Tomcat 10.1 (application server)
- ASP.NET Core 8 (credential access portal)

## What I Learned

Designing for failure is more interesting than designing for success. The
rollback path — restoring AWSCURRENT to Oracle and Tomcat on any failure — had
to be built with the same care as the forward path. Every step that can fail
must be individually recoverable, and the lock must release on every exit path
including unhandled exceptions.

The `lockOwner` UUID pattern came from observing a real collision between a
scheduled Lambda invocation and a manually run local script. The system
recovered automatically, but the observation shaped the final design.

IAM least-privilege is not an afterthought. The Lambda execution role started
with five broad AWS managed policies. Replacing them with a single scoped
inline policy — restricting Secrets Manager access to the `ora-aws-poc/`
namespace, SSM access to one document and one instance ARN, DynamoDB access
to one table — took an afternoon and caught two things that shouldn't have had
access.

## Links

- [GitHub Repository](https://github.com/scottyleblanc/OracleAwsRotation)
