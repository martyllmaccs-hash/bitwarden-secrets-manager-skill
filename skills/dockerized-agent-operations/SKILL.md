---
name: dockerized-agent-operations
description: "Use when administering agents that run in Docker."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [docker, deployment, secrets, bitwarden, gateway]
    related_skills: [hermes-agent, hermes-vps-operations]
---

# Dockerized Agent Operations

## When to Use

Use this skill when the agent process itself runs in Docker: identify the production container and mounted state, administer its lifecycle, and bootstrap its external secret manager. For platform failures, credential-sharing incidents, or cross-machine A2A/peer connectivity, use `hermes-vps-operations`. An agent merely using Docker as its terminal backend is not a Dockerized deployment.

## Procedure

1. **Identify which Docker model applies before issuing commands.** Distinguish an agent that *runs inside Docker* from an agent that merely uses Docker as its terminal backend; their administration paths and state ownership differ.
2. **Establish the control plane before issuing Docker commands.** Check whether the current shell can reach the Docker daemon. If it cannot, treat it as an agent workload container—not the VPS host—and do not guess the production container name or host volume path.
3. **Locate the persistent state volume and the live service definition from the host.** Start with `docker ps -a` and inspect the actual container's mounts; treat the mounted data directory as the source of truth for configuration, sessions, skills, and secrets. Confirm the exact running container name, image, command, and volume mount before changing state. Container names in managed/orchestrated deployments often differ from the product name, so never assume a target named `hermes` or a `~/.hermes` bind mount.
4. **Run one-time interactive administration inside the official image with the confirmed data mount.** Use a short-lived interactive container when no live container is available; use `docker exec -it <container> hermes ...` when it is already running. Never perform setup in an ephemeral container without the persistent data mount.
5. **For an external secret manager, bootstrap only its narrowly scoped machine credential.** Bitwarden Secrets Manager operates headlessly; the Hermes Desktop app and Password Manager vault are not prerequisites. Store provider credentials in the manager, configure the agent from the mounted state volume, then verify fetch and gateway startup.
6. **Resolve Bitwarden identifiers separately.** A machine-account name, its access token, and the selected Secrets Manager project are distinct values. Use the token to discover permitted projects in the interactive wizard, then select the project by its exact displayed identifier; do not request or invent a project UUID when the wizard resolves it.
7. **Start the production gateway as a named, restart-managed container.** Expose no host ports unless a real integration requires them; treat dashboards and API endpoints as public services requiring explicit authentication and network design.
8. **Verify from the running container and its logs.** Check the secret-source status and recent gateway logs after every change; a successful setup command alone is not proof the supervised gateway consumes the configuration. If the secret source is enabled after the gateway started, restart the exact production container once, then verify status and a dry-run sync within that same container.
9. **Design remote Desktop access from the actual deployment boundary.** Keep Tailscale on the VPS host, then inspect the live container's published host ports before giving a remote URL. Use the full MagicDNS hostname plus the host-published dashboard/backend port; never substitute Hermes' default `9119` when a managed image maps a different port. Treat the messaging gateway and the Desktop remote backend as distinct services, and configure a deliberate auth provider before connecting Desktop.
10. **Test the effective config source before telling the user what controls a behavior.** Managed images ship an entrypoint that exports its own defaults into the same variables the agent reads, and that export is the presumptive winner: a config file or secret-manager value for the same variable is inert until measured otherwise. Compare the running process's environment against each candidate source (including the configured secret manager) using equality checks that print only MATCH/MISMATCH, never values, then name the source that actually wins. Editing the losing source has no effect, and telling the user to edit it wastes their time. Never infer precedence from documentation, and never let the secret manager be assumed authoritative because it is newer or because secrets are known to apply at startup: the entrypoint runs in the same process tree and wins a same-variable collision until a MATCH/MISMATCH check says otherwise.
11. **Keep a portable change record when requested.** Store one durable Markdown log on the persistent volume with non-secret decisions, commands/results, verification, and corrections. Treat inherited configuration as untrusted; never record secret values, bearer tokens, screenshots, or credential-bearing logs.

## Rules and pitfalls

- Verify the production container's actual host volume mount before giving a one-off `docker run` recipe; plausible defaults such as `~/.hermes` may target the wrong state store.
- Mount the same persistent data directory for setup and production startup; otherwise an interactive wizard writes state that disappears with its one-off container.
- Do not run two Hermes containers concurrently against one data volume; concurrent writers can corrupt session and memory state.
- Use an SSH terminal for token-bearing Docker commands on a VPS; browser consoles can corrupt pasted shell characters and credentials.
- Keep secret-manager bootstrap credentials out of Compose files and command history where possible; use the tool's masked prompt and retain only the bootstrap token in the mounted secret file.
- Preserve exact casing and spelling for secret-manager identifiers; a machine account and a project are separate access-control objects, so validate their relationship rather than conflating their names.
- Do not publish agent API or dashboard ports by default; a messaging-only gateway does not need them, and an exposed control plane needs a deliberate authentication and proxy design.
- Separate the Desktop connection label from its network URL and authentication; a human-readable name never substitutes for a MagicDNS hostname, and a remote form's session-token field must never receive a Bitwarden bootstrap token or provider API key.
- Do not retain screenshots in operation logs; they can quietly consume persistent storage and usually add no durable diagnostic value.
- Expect the image's own entrypoint to export defaults for the same variables the secret manager or config file sets. Exactly one source should own each setting; when two compete, the loser silently stops mattering and the user's edit appears to do nothing.
- Distinguish an inert credential from a working one by behavior and timing, not by presence: a setting that cannot take effect without a process restart did not cause a change that happened while the process kept running. A successful login is not evidence that the source you edited is the source in use — determine which source supplied the accepted credential, or the next restart presents the same problem as a fresh mystery.
- Do not verify credentials from inside `execute_code`: the sandbox runs with Hermes-managed credentials stripped, so a secret fetch there can return an empty set while the gateway is happily applying dozens of secrets. Read secret-source state through `terminal` for real verification, and treat a suspiciously empty sandbox result as a sandbox artifact rather than a finding.
- Check provider quota and fallback route separately from deployment failures; an exhausted model endpoint is not a container or secret-manager fault.
- Report observed deployment boundaries, not assumed host facts: if the container, region, provider, or machine class disagrees with the operator's description, name the discrepancy before selecting paths or volumes.
- Interactive wizards need a real terminal: `docker exec -it <container> hermes setup`. With `-T` or no TTY they abort at the first prompt. If `hermes` is not on the container's PATH, read the launcher path from the running gateway's own `argv` in `gateway_state.json` rather than guessing a venv location.
- Expect the setup wizard to rewrite only `model`, `gateway`, and `tools` — not `platforms` or agent/peer sections. Diff the sections you own against `backups/config/config.yaml.good.*` after the operator finishes, and warn them that a provider key typed into the wizard lands in `.env`, where the secret manager overrides it at the next start.

## Secret handoff between agents

- Prefer per-agent machine-account credentials over terminal-pasted token sharing when a second agent exists; shared handoffs obscure which agent received a value.
- Record handoffs as presence and length checks or fingerprints, never raw token values.
