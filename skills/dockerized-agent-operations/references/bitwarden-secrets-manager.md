# Bitwarden Secrets Manager in a Dockerized Hermes Deployment

Use Bitwarden **Secrets Manager**, not the personal-password vault integration, for headless provider credentials.

## Prerequisites in Bitwarden

1. Create a dedicated project containing only the environment variables the agent needs, such as `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`.
2. Create a machine account with read access only to that project.
3. Create its access token. Do not transmit it through chat or place it in version control.

## Locate the production deployment first

On the VPS host, identify the live container and its state mount **before** running any setup command:

```bash
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
C='<actual-container-name>'
docker inspect --format '{{range .Mounts}}{{printf "%s -> %s (%s)\\n" .Source .Destination .Type}}{{end}}' "$C"
docker exec -it "$C" hermes secrets bitwarden status
```

Managed deployments often use generated container names, custom images, and non-default volumes. Never infer a container name from a tutorial or assume `~/.hermes` is the active state store; setup against the wrong mount succeeds but leaves the real gateway unchanged.

## Setup against the persistent Hermes volume

If the production container is running and contains the `hermes` CLI, run the wizard in that exact container:

```bash
docker exec -it "$C" hermes secrets bitwarden setup
```

Otherwise, run a short-lived container only after confirming it mounts the same host directory as the production gateway:

```bash
docker run --rm -it \
  -v <confirmed-host-data-dir>:/opt/data \
  nousresearch/hermes-agent:latest \
  secrets bitwarden setup
```

The wizard stores the bootstrap `BWS_ACCESS_TOKEN` in the mounted `.env`, stores the selected region and project ID in mounted configuration, tests the project fetch, and enables the integration. The provider credentials remain in Bitwarden.

## Production and verification

For a messaging-only gateway, avoid unnecessary published ports:

```bash
docker run -d \
  --name hermes \
  --restart unless-stopped \
  -v ~/.hermes:/opt/data \
  nousresearch/hermes-agent:latest \
  gateway run
```

Verify the configured process, not just the one-off wizard. Reuse the discovered production container name:

```bash
docker exec "$C" hermes secrets bitwarden status
docker exec "$C" hermes secrets bitwarden sync
docker logs --tail 100 "$C"
```

Restart the production gateway only if its process does not reload configuration automatically; then repeat the same status, sync, and log checks.

Bitwarden is authoritative by default: provider-key rotation in Bitwarden is picked up when Hermes processes start. After a successful cutover, remove duplicated provider keys from the mounted `.env`; retain the Bitwarden bootstrap token only.

## Adding individual secrets later (the `bws` CLI)

The wizard bootstraps the integration; adding one more secret afterwards is a `bws` call or a vault-UI edit:

```bash
bws secret create <KEY> <VALUE> <PROJECT_ID> --note "what it is, and which machine consumes it"
```

- **`bws secret create` prints the created secret, value included**, as does `bws secret list`. Redirect stdout to a `chmod 600` file in the scratch directory and parse only `id` and `key` back out; never let either command write to a terminal whose output reaches a log or a transcript.
- **Expect HTTP 429 on a burst.** Several creates in a row reliably trips `Slow down! Too many requests. Try again in 1s.` Space successive creates about 3 seconds apart, track each one's exit code, and re-run only the failures rather than assuming the batch landed.
- **Verify by round-trip, not by exit code.** Read the project back and compare every key against the intended value in-process, printing only `MATCH` / `MISMATCH` / `MISSING` plus the secret count before and after. Exit 0 proves the call; only the read-back proves the store holds what you sent.
- **Generate values in-shell and wipe them afterwards.** Build the value with `python3 -c 'import secrets; print(secrets.token_hex(32))'`, never as literal text in the command, and once the round-trip passes overwrite the temp copy with random bytes before unlinking it.
- **A read-only machine account cannot write.** Read-only is the recommended posture, so a `create` can legitimately fail: hand the operator the key, value, and note for the vault UI instead of retrying.
- Values a plugin reads *only* from the environment, and settings that exist in no `config.yaml` section, have no other home and are stored here too even when they are not secret — this project is the deployment's env source at startup. Say so when adding them, so the next reader does not mistake a plain setting for a credential.

## Security decisions

- Keep the encrypted stale-secret cache disabled unless availability requirements justify the residual risk.
- Scope the machine account to one project and set a token-expiry and rotation process.
- Do not include `BWS_ACCESS_TOKEN` in the synchronized Bitwarden project; Hermes intentionally refuses to import it from that project.
- Do not expose API or dashboard ports without explicit authentication, TLS/proxy, and network-access decisions.
