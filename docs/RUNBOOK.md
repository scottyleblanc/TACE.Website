# RUNBOOK — tacedata.ca Operations

Operational procedures and troubleshooting commands for the tacedata.ca site.

---

## Deploy Pipeline Troubleshooting

### Check recent workflow runs

```powershell
gh run list --repo scottyleblanc/TACE.Website --limit 5
```

Shows the last 5 runs with status (completed/failed), trigger (push/schedule), run ID, duration, and timestamp.

### View full log for a specific run

```powershell
gh run view <run-id> --repo scottyleblanc/TACE.Website --log
```

Replace `<run-id>` with the ID from `gh run list`. Streams the complete step-by-step log.

### Search the log for specific output

```powershell
gh run view <run-id> --repo scottyleblanc/TACE.Website --log 2>&1 | Select-String -Pattern "invalidat|upload|error" -CaseSensitive:$false
```

Useful patterns:
- `upload` — confirm which files were synced to S3
- `invalidat` — confirm CloudFront invalidation was issued
- `error|warn` — surface any failures

### Confirm a specific file was uploaded

```powershell
gh run view <run-id> --repo scottyleblanc/TACE.Website --log 2>&1 | Select-String -Pattern "posts/my-post-slug" -CaseSensitive:$false
```

---

## Site Not Updating After Push

If a deploy succeeds but the live site still shows old content:

1. Check the run completed successfully — `gh run list` shows `completed success`
2. Confirm the file was uploaded — search the log for the post slug (see above)
3. Confirm a CloudFront invalidation was issued — search the log for `invalidat`
4. Wait 2–5 minutes for CloudFront propagation to complete
5. Hard refresh the page — `Ctrl+Shift+R`

If the file was not uploaded, the Hugo build may not have generated it — check for draft status or future date in the front matter.

---

## CloudFront Cache — Manual Invalidation

If you need to force a cache clear outside of a deploy:

```powershell
aws cloudfront create-invalidation --distribution-id <DISTRIBUTION_ID> --paths "/*"
```

Replace `<DISTRIBUTION_ID>` with the value from the private repo runbook.
