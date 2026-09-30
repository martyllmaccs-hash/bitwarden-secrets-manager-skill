---
name: hermes-vps-operations
description: "Diagnose Hermes container incidents and peer links."
version: 0.3.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, gateway, incident-response, a2a, connectivity]
    related_skills: [hermes-agent, dockerized-agent-operations]
---

# Hermes VPS Operations

Diagnose incidents in a containerized Hermes gateway and establish authenticated cross-machine links. This is not a general Docker deployment or standalone bot-creation guide; use `dockerized-agent-operations` for production containers, mounts, managed-image settings, and initial secret-manager setup.

## When to Use

- A containerized Hermes gateway platform is offline, degraded, rejecting credentials, or answering from two processes.
- An existing Bitwarden-backed deployment is failing secret sync or consuming the wrong effective value.
- Two Hermes deployments need an A2A or peer-DM link, or a private link fails in one direction.
- A remote Hermes operation needs its target machine and authenticated route verified.

Do not use for standalone Bot Mode/profile creation, mail or iCloud setup, ordinary chat, host-native systemd, or generic Docker administration.

## Change Gates

- **Confirm the route before writing.** For deployments with an operator-set primary-model requirement, read `model.default` / `model.provider` and runtime metadata. If on a fallback or reduced-tier route, perform read-only diagnosis and hold changes.
- **Prove the target and boundary.** Identify the gateway PID, active `HERMES_HOME`, shell/container context, served profile, and actual host/volume before changing state. A local path, agent name, or SSH refusal does not locate a peer's files. If the CLI already runs inside the container, do not double-wrap it in `docker exec`. See `dockerized-agent-operations` for container discovery.
- **Back up before changing files in `HERMES_HOME`.** Prefer changes inert until the next process start; never restart a gateway from its own session. Hand the restart to the operator. Without a Docker socket or host access, publishing ports and recreating containers are operator steps.
- **Distinguish write, live state, and verification.** A changed config is not a running adapter: compare process start, `gateway_state.json` platforms, fresh logs, and listener/application probes. On a mid-change stop, list every file/key written, whether each is live, what was not done, and rollback.
- **Protect secrets.** Never paste values into chat, commands, screenshots, or logs. `hermes config get` expands `${VAR}` and can print live secrets. `bws secret list` and `bws secret create` can print values; redirect unavoidable output to a permission-restricted scratch file, parse only names or fingerprints, and remove it. Keep `BWS_ACCESS_TOKEN` out of the project it bootstraps. Do not widen a profile's `.env` access before checking project and machine-account scope.

## Procedure

1. **Classify the incident at the running boundary.** Use `terminal` to identify hostname, `HERMES_HOME`, gateway PID/argv, version, and `gateway_state.json`; scope `search_files` to relevant log files (`logs/gateway.log`, `logs/errors.log`, `logs/agent.log`, and `logs/gateways/<profile>/current`). Exclude caches, sessions, package trees, and large model catalogs; match short agent names on word boundaries. Completion: actual serving process, home, latest failure class, and log timestamp are known.
2. **Check secret and provider layers separately.** In the gateway's container context, use `terminal(command="hermes secrets bitwarden status")` and `terminal(command="hermes secrets bitwarden sync")` when enabled. Sync proves vault access, not downstream token validity. Before rotation, compare effective process source to `.env`, entrypoint, and secret-manager candidates using only MATCH/MISMATCH or short fingerprints; managed-image exports can override other sources. A Telegram API token rejection is not a Docker or machine-account outage. Completion: failing layer and effective source named without exposing values.
3. **Rule out a second platform consumer.** For pairing/unrecognized-user symptoms, compare `hermes pairing list`, local pairing/authorization logs, and the exact reply wording in this build. An empty local store, absent event, and absent template point to another process; `Conflict: terminated by other getUpdates request` is evidence of two clients polling one Telegram token and potential exposure. Do not call `getUpdates`: it consumes the queue. Follow `references/shared-platform-credential-diagnosis.md`; attribute the competing host by measurement, not agent name. Completion: producing instance identified or attribution explicitly unverified.
4. **Apply the smallest scoped fix.** Replace the configured secret name rather than creating a duplicate. Keep machine-specific platform and A2A credentials out of projects shared with another machine; give each machine its own scoped project and read-only account. A read-only account cannot repair a shared-project override; granting write access widens exposure. Verify vault write capability before promising edits; space writes to avoid partial HTTP 429 batches and read back secret names/fingerprints. Let the operator restart after update, then inspect fresh adapter startup rather than inferring success from sync or stale `gateway status`. Completion: actual provider connection or explicit pending-restart/blocker state.
5. **Test cross-machine topology before config changes.** Use `references/agent-to-agent-links.md` to choose A2A versus `hermes peer`; `scripts/probe_reachability.py` classifies open/refused/timeout from the caller's container. MagicDNS resolution is not liveness. Bind an inbound published port to the private tailnet address, not the public interface, and require authentication. Each direction needs its own credential and authenticated application-layer round trip with receiving-side evidence; a TCP open port, Agent Card, health check, or HTTP 200 task acceptance alone is not completion. Use `scripts/probe_a2a_peer.py` for an A2A direction check. Never infer local identity from a peer key or Bot roster label. Completion: state separately directions completed and those lacking route, credential, or listener.
6. **Verify remote work on the target.** Check current-session tools, rebuild log, and configured peer routes before declaring a machine inaccessible; SSH refusal or missing local file proves only that direct path failed. For a remote GUI, verify the target's running driver/browser through the authenticated peer, not an installed binary or Agent Card label. Poll an accepted A2A task to completion and inspect evidence. For remote file writes, request independent target-side read-back and compare byte counts and SHA-256 hashes. Do not open a new public port or retain screenshots for this workflow. Completion: target-side evidence or named missing route/tool.
7. **Record the outcome.** Append a secret-free entry to `<HERMES_HOME>/plans/hermes-rebuild-log.md` for material decisions, commands/results, remediation, verification, and pending operator steps. Never record tokens, chat IDs, private content, full error transcripts, or screenshots. Mark intent pending and append superseding corrections rather than erasing wrong conclusions. For copying the log to another machine or Obsidian vault, confirm the target path and transfer route and read back exact contents; a local write is not a remote copy. Completion: report verified platform/link state and record path.

## Pitfalls

- `hermes gateway status` can retain an older failure; fresh connection and message events decide current health. Do not restart a healthy gateway for stale status.
- A pairing code belongs to the instance that minted it. Approving it on another box fails; clearing pairing state cannot remove a competing token consumer.
- A project read by two machines can override both local `.env` files with the same A2A trust table or bot token. Repeated 401s or Telegram polling conflicts may recur on restart until project/account scope is separated. A peer's “fixed” claim needs an authenticated re-test in the affected direction.
- A recipient replying inside an inbound task is not proof it can initiate a reverse-direction send. Verify both directions independently.
- Keep the operator's requested communication boundary: if an authorized peer does work, require secret-free evidence and report through the established point of contact. A queued DM is not delivery.
- If asked for commands, give the exact command for the actual shell/container boundary first; for a whole runbook, mark each machine's steps done or pending in one sequence. Keep short status answers short.

## Verification

A recovery is complete only when fresh gateway logs show the affected platform connected, `hermes gateway status` has no current platform failure, and the secret-free rebuild log records the verified state. Where Bitwarden is enabled, status and sync must be checked in the gateway context. Cross-machine success additionally requires authenticated application-layer evidence in each claimed direction.

## Support files

- `references/agent-to-agent-links.md` — A2A versus peer DM, configuration, and directional verification.
- `references/shared-platform-credential-diagnosis.md` — pairing attribution and shared-platform-token investigation.
- `scripts/probe_reachability.py` — caller-side TCP classification.
- `scripts/probe_a2a_peer.py` — authenticated A2A direction probe; takes an env-var name and never prints the token.
