---
name: bitwarden-secrets-manager
description: "Use when managing Hermes secrets through Bitwarden."
version: "0.1"
author: Martin (martyllmaccs-hash), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bitwarden, bws, secrets, hermes]
    related_skills: []
---

# Bitwarden Secrets Manager

One workflow for Hermes' built-in BWS integration: scoped setup, rotation, and verification. No custom SDK, container deployment, A2A client, or Bitwarden Password Manager operations.

## When to Use

Set up BWS for a Hermes runtime, rotate its bootstrap token or provider keys, or diagnose sync/configuration failures. Do not use for personal passwords or general Docker/platform incidents.

## Prerequisites

- Confirm active home/profile and consumer process. In Docker, use the verified existing container/mount; never create another deployment for setup.
- Scope a read-only machine account to one runtime's project, with valid env-var names. Separate projects/accounts per deployment: project access exposes all permitted keys.
- Enter `BWS_ACCESS_TOKEN` only through an operator-owned masked prompt or protected secret facility. Never paste values into chat, argv, Git, screenshots, or logs. Keep the bootstrap token outside the project it bootstraps.

## How to Run

Use `terminal` in the identified runtime for non-secret checks:

```python
terminal(command="hermes secrets bitwarden --help")
terminal(command="hermes secrets bitwarden status")
terminal(command="hermes secrets bitwarden sync")
```

The operator runs `hermes secrets bitwarden setup` in a real terminal: masked token prompt, region/project selection, then integration enablement. For bootstrap rotation, use the masked `hermes secrets bitwarden token` prompt. Never put token values in flags.

## Procedure

1. **Scope before setup.** Confirm target home/profile, project, machine account, and region. Run setup only when unconfigured or changing that scope. Completion: the intended runtime uses the intended project and least-privilege account.
2. **Verify fetch once.** Check status, then dry-run `sync` after a change or fetch failure. In this implementation sync bypasses cache reuse and reports names/actions, not values. Completion: expected project keys fetched, not downstream provider validity.
3. **Manage values in the vault.** Prefer operator BWS UI writes; keep runtime accounts read-only. Raw `bws secret list/get/create/edit` output contains values; never send it to transcripts or pass values in argv. Automation requires a separately authorized secret-safe path and exact-target read-back. Reconcile ambiguous writes before retrying.
4. **Activate deliberately.** Hermes normally applies fetched values at process startup. After a change, have the operator restart only the affected supervised process if required, then inspect fresh startup evidence and perform a non-sensitive functional test. Dry-run sync is not activation. `sync --apply` changes the invoked CLI process, not its parent shell or an already-running gateway.
5. **Diagnose only if needed.** Check region/project, scope, `override_existing`, startup timing, and consumer diagnostics. BWS overrides existing values by default; later managed layers may differ. Equality is not source provenance; `/proc` startup environment does not prove later Python env mutations.
6. **Finish rotation safely.** Verify new credentials before revoking old ones where overlap is supported. Suspected exposure prioritizes revocation; report downtime. Remove duplicates only after activation and rollback are verified. Log no values.

## Pitfalls

- Fetch caches can delay startup freshness; reconcile `cache_ttl_seconds` before declaring a rotation active. Keep encrypted stale fallback disabled unless its availability/security trade-off is explicitly approved. Treat any disk cache as sensitive; exclude it from Git/backups not designed for secrets.
- Hermes can continue startup after BWS failure using other available credentials. A running process or exit 0 alone does not prove BWS recovery.
- Stop on authentication/permission failure rather than repeated retries or wider runtime grants. Honor 429 retry guidance with bounded backoff; do not blindly repeat a create.
- A dry-run child CLI cannot prove the gateway's live secret scope. Sandbox credential stripping can also produce missing-token results; recheck at the actual consumer boundary before diagnosing a vault outage.

## Verification

Confirmed runtime/project/region; expected keys fetched without disclosure; activation evidenced by fresh consumer behavior; least-privilege scope preserved. Report pending restart or uncertain source explicitly. No `.env`, token, vault export, or cache belongs in this repository.

## Sources

[Hermes BWS docs](https://hermes-agent.nousresearch.com/docs/user-guide/secrets/bitwarden). Derived from MIT-licensed Hermes BWS guidance; unofficial. Recheck installed CLI help on version mismatch.
