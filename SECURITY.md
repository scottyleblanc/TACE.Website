# Security Policy

## Reporting a Vulnerability

If you discover a security issue in this repository, please report it by email:

**contact@tacedata.ca**

Please do not open a public GitHub issue for security vulnerabilities.

---

## Scope

This repository contains the source for a static portfolio site (tacedata.ca).
There are no user accounts, no database, and no server-side code.

AWS infrastructure is accessed via OIDC — no long-lived credentials are stored
in this repository. IAM permissions are least-privilege and scoped to this
repository only. No AWS resource identifiers are committed to this repository.

---

## License

All content and code in this repository is proprietary.
Copyright © 2026 TACE Data Management Inc. All rights reserved.
