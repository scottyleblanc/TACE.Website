# Websavers Account Review

Checklist to complete before Stage 3 decisions can be finalized.

---

## Billing

- [x] What is the exact renewal date (month and year)?
- [x] What is the renewal cost?
- [x] What does the renewal cover — is it one line item, or separate charges for hosting, domain registration, and email?
- [x] Is domain registration billed separately from web hosting?

**Findings:**
- Renewal date: **July 14, 2026**
- Hosting and email are bundled free with domain registration — no separate line items
- Real cost is domain registration only: **~$25 CAD/domain/year**
- **5 domains registered** (all variants of tacedata.ca) = **~$125 CAD/year total**

---

## Domain

- [x] Confirm `tacedata.ca` is registered through Websavers (they are the registrar, not just the host)
- [x] Is there a transfer lock / registrar lock on the domain?

**Findings:**
- Websavers is the registrar for all 5 domains
- Registrar lock is active on all 5 — configured by owner, can be released when ready
- 5 domain variants registered (exact list TBD — confirm in Websavers dashboard)

**Open decision:** Do all 5 variants need to stay registered? Route 53 charges ~$10 USD (~$14 CAD)
per .ca domain. Transferring all 5 saves ~$55 CAD/year. Letting unused variants lapse saves more.
At minimum, `tacedata.ca` must be kept. See decisions section below.

---

## Email

- [x] What email address(es) exist under `tacedata.ca`?
- [x] Is email hosted on Websavers, or forwarded somewhere else?
- [x] Is there anything in the inbox that matters, or is it effectively unused?

**Findings:**
- 3 email addresses hosted on Websavers:
  - Personal address (primary)
  - Accounting address
  - Contact address
- Email is hosted directly on Websavers — not forwarded elsewhere
- Inbox history exists and should be preserved

**Constraints for email provider selection:**
- Must support IMAP import (to migrate inbox history from Websavers before cutover)
- 3 addresses: need to decide if accounting and contact require separate inboxes
  or can be aliases/forwards to the primary address
- If aliases are acceptable: Zoho free tier (1 user, up to 30 aliases) may work
- If separate inboxes are required: Zoho free tier is insufficient; Fastmail or Google Workspace needed

**Migration requirement:** Export inbox history via IMAP before cancelling Websavers.
Do not cancel email hosting until export is confirmed complete.

---

## Hosting

- [x] What hosting plan is active (shared hosting, WordPress-specific, etc.)?
- [x] Are any other sites or services tied to the same Websavers account?

**Findings:**
- WordPress hosting plan — bundled free with domain registration
- No other sites or services on the account
- Hosting has very limited space and no meaningful service level

---

## Findings Summary

| Item | Finding |
|---|---|
| Renewal date | July 14, 2026 |
| Renewal cost | ~$125 CAD/year (5 domains at ~$25 CAD each) |
| Billing breakdown | Domain registration only — hosting and email are bundled free |
| Domain registrar confirmed | Yes — Websavers is registrar for all 5 domains |
| Number of domains | 5 (all tacedata.ca variants) |
| Transfer lock status | Active on all 5 — owner-configured, can be released |
| Email addresses | 3: personal, accounting, contact |
| Email hosting | Hosted on Websavers (not forwarded) |
| Inbox history | Exists — must be exported before cutover |
| Hosting plan | WordPress, bundled free |
| Other services on account | None |

---

## Open Decisions (unblock before Stage 3)

1. **Which domains to keep?** Confirm the 5 domain variants. Decide which to transfer to
   Route 53 and which to let lapse at renewal. At minimum, `tacedata.ca` must transfer.

2. **Accounting and contact email — separate inboxes or aliases?** If aliases are
   acceptable, Zoho free tier may be sufficient. If separate inboxes with independent
   history are needed, Fastmail or Google Workspace is required.

3. **Email inbox export** — must be completed before Websavers email is cancelled.
   Use an IMAP client (Thunderbird is the standard tool) to export to local storage
   before the cutover date.
