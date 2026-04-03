# Security Policy

## Reporting a Vulnerability

If you discover a security issue in this repository, please report it by email:

**contact@tacedata.ca**

Please do not open a public GitHub issue for security vulnerabilities.

## Scope

This repository contains the source for a personal portfolio static site.
There are no user accounts, no database, and no server-side code.

AWS infrastructure is accessed via OIDC — no long-lived credentials are stored
in this repository. IAM permissions are least-privilege and scoped to this
repository only.
