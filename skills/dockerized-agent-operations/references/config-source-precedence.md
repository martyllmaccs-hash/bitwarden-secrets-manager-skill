# Configuration Source Precedence in Managed Images

Managed deployment images frequently ship an entrypoint that exports its own defaults into exactly the variables the agent, a secret manager, or a config file also sets. The result is a setting with two owners: one silently wins, and the user edits the loser and concludes their change did not work.

This applies to any platform-managed image, not one vendor's.

## Identify the winning source

1. Find the running process that consumes the setting, and read its environment.

```bash
python3 - <<'PY'
import os
for d in os.listdir('/proc'):
    if not d.isdigit():
        continue
    try:
        cmd = open(f'/proc/{d}/cmdline', 'rb').read().decode('utf-8', 'replace')
    except Exception:
        continue
    if 'dashboard' in cmd and '--port' in cmd:
        env = dict(e.split('=', 1) for e in
                   open(f'/proc/{d}/environ', 'rb').read().decode('utf-8', 'replace').split('\0') if '=' in e)
        print('pid', d)
        for k in ('ADMIN_USERNAME', 'HERMES_DASHBOARD_BASIC_AUTH_USERNAME'):
            v = env.get(k)
            print(f'  {k}: {"SET len=%d" % len(v) if v is not None else "absent"}')
PY
```

2. Read the entrypoint to see what it exports and from which source variable.

```bash
grep -nE 'export |ADMIN_|DASHBOARD_' /entrypoint.sh
```

3. Compare candidate sources with equality checks that print only MATCH/MISMATCH and lengths. Never print the values, even to your own output.

```python
# dash = values from the running process env; cand = values from each other source
for k in KEYS:
    a, b = dash.get(k), cand.get(k)
    verdict = 'n/a' if a is None or b is None else ('MATCH' if a == b else 'MISMATCH')
    print(k, f'len={len(a) if a else None}', verdict)
```

A secret manager whose configured values return MATCH against the running process is the effective source. MISMATCH means it is inert for that setting, no matter what its config claims.

**Do not assume the secret manager wins the collision.** It is the more recently added source and it does apply secrets at process start, which makes "the manager must be authoritative" feel safe. It is not safe: the image entrypoint exports into the same variables from inside the same process tree, and measurement frequently shows the image environment supplying the value while the manager's identical-looking setting is inert. Only the MATCH/MISMATCH comparison decides it. Getting this backwards produces confident, specific, wrong advice — including telling the user to edit a setting that has no effect.

## Read secret state from `terminal`, never from `execute_code`

Hermes strips managed credentials from sandboxed and child processes. A secret fetch executed in `execute_code` can therefore report an empty project or an absent token while the live gateway is applying dozens of secrets from that same project. Treat an implausibly empty credential result as a sandbox artifact, and re-run the check through `terminal` before reporting it as a finding — including before raising it as an alarm to the user.

## Confirm with timing, not with configuration text

A source that can only take effect at process start cannot explain a change that occurred while the process kept running. Compare the timestamp of the observed behavior change against the process start time (`ps -o pid,lstart,cmd -p 1`). If a credential began or stopped working with no restart in between, the runtime is reading `ADMIN_*`-style exports from the image environment, not the secret manager.

## Remediation options

- **Accept the image's owner.** Least invasive when the value is already reachable and changeable where the image defines it.
- **Make the secret manager authoritative.** Requires stopping the entrypoint from exporting into the same variables (derived image, or orchestration-level environment). Do not add a competing variable and assume precedence resolves as documented — verify with the comparison above.
- **Move to an identity-based login.** Register the dashboard with the model provider's OAuth so no shared secret is stored anywhere. A stable session-signing secret is still required for sessions to survive restarts.

## Pitfalls

- Do not conclude a credential is correct because a login succeeded; determine which source supplied it, or the next restart will look like a new mystery.
- Do not infer source precedence from documentation when a running process can be measured directly.
- Delete abandoned duplicate settings once the true owner is known; an inert duplicate is a trap for the next diagnosis.
