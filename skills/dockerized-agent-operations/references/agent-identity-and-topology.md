# Agent identity and multi-agent topology

How an agent's identity is stored, how to establish which agent and which machine you are
actually operating, and how agents in one deployment talk to each other.

## The identity file: `$HERMES_HOME/SOUL.md`

An agent's identity is a plain file, injected into the system prompt as identity slot #1 on
every turn (`agent/prompt_builder.py: load_soul_md`). It is independent of project context
files (`AGENTS.md`, `CLAUDE.md`, `.hermes.md`) and is not scoped to a working directory.

What that means when editing it:

- It applies from the next turn onward — no restart needed. The wording is what the agent will
  believe about itself, so write facts, not instructions.
- It sits in the same trust class as `config.yaml`: an agent writing to it goes through the
  write-approval path. `load_soul_md` skips the injection scan only for a user-authored file
  in a real `$HERMES_HOME`; a `SOUL.md` owned by an installed profile distribution is scanned.
- `hermes --ignore-rules` suppresses `SOUL.md` along with project context and memory — the way
  to isolate whether a behavior comes from the identity file or from Hermes itself.
- Back up before editing and report the path:
  `cp "$HERMES_HOME/SOUL.md" "$HERMES_HOME/../backups/SOUL.md.bak-$(date -u +%Y%m%dT%H%M%SZ)"`.
  It is small, unversioned, and read every turn, so a bad edit is felt immediately and has no
  history to fall back on.
- Durable soul content: where the agent runs (host, provider, region), its hardware, its
  operator and that operator's devices, and any sibling agents. The operator owns voice and
  temperament — write the placement and structure, and leave the character section explicitly
  open rather than inventing one for a machine you may never have seen.

## Establishing which agent you are, and on which machine

Do this before answering any question about "your" host, and before editing any identity file.
`$HERMES_HOME` and `HERMES_SESSION_PROFILE` say *which profile* is live, not where it runs.

1. **Container or host** — `hostname` (a bare container id plus an `overlay` root means
   containerized), `ls -la /`, `df -h / /opt/data` (a data directory bind-mounted from the host
   usually shows a real device such as `/dev/sda1`), `systemd-detect-virt`, `lscpu`.
2. **Location and provider** — `curl -s --max-time 6 https://ipinfo.io/json` gives city, region,
   country, timezone, and hosting org for the egress address; a hostname resolving to a provider
   FQDN corroborates it.
3. **Which process serves this chat** — `$HERMES_HOME/gateway_state.json` (pid, argv,
   `code_version`, served profiles, per-platform connection state), plus `gateway.pid`,
   `gateway.sock`, `gateway-starts.log`. `env | grep -i hermes` gives the live `HERMES_HOME`,
   session id, source, and platform.
4. **Who the operator is** — `$HERMES_HOME/channel_directory.json` lists messaging contacts by
   display name; deployment auth logs and the configured dashboard user identify the login.
   Strong evidence, not proof of a legal name — say which it is.
5. **Recent intent** — `$HERMES_HOME/.hermes_history` holds the operator's recent prompts as
   plain lines; the fastest way to reconstruct what a half-finished setup session was doing.
6. **What agents exist here** — `$HERMES_HOME/bot_relay/roster.json` (agents and their
   connection ids) and `served_profiles` in `gateway_state.json`. A managed image typically
   multiplexes one profile and therefore serves exactly one agent; a name the operator uses for
   a *second* agent will have no local file at all.

When a named agent has no reference anywhere in the home, the conclusion is that it is either
on another machine or does not exist yet. State which — and do not author its soul from a probe
of a machine that cannot see it.

## Two agents in one deployment: peers

A *peer* is another Hermes gateway running the `api_server` platform; that stock API is the
transport.

- Registration: `hermes peer add <name> --url http://<host>:<port> --key <API_SERVER_KEY>`,
  then `hermes peer list` / `hermes peer remove <name>`.
- The URL lives in `config.yaml → bot_peers`; the credential lives in the profile secret
  store or `.env` as `HERMES_PEER_<NAME>_KEY` (uppercased, `-` becomes `_`).
- Messaging: `hermes peer dm <peer> "message"` runs one synchronous turn in the peer's
  canonical "Bot Chat" session; `run` / `status` / `stop` do the same asynchronously.
  The `<peer>/<profile>` form targets the `/p/<profile>/` mirror on a multiplexed peer.
- **Key present is not link present.** A `HERMES_PEER_<NAME>_KEY` in an environment is a key for
  a peer *named* `<name>`; it proves nothing about registration (the `bot_peers` URL), about
  reachability, or about the local agent's own name. Check both halves before claiming a link.
- **Duplicate-name trap.** When a peer name equals the local agent's own identity, assume a
  collision — a leftover from an earlier topology, or a credential placed on the wrong machine —
  and resolve it with the operator. The same name meaning two different agents is how the wrong
  secret gets rotated or the wrong volume gets written.

## Searching inside a deployment home

`$HERMES_HOME` contains multi-megabyte caches (`models_dev_cache.json`, `cache/`,
`lazy-packages/`, `home/.cache/`, request dumps under `sessions/`). One unscoped recursive
content search from the home root can return millions of characters and be truncated past the
part you needed. Always scope the search: a specific subdirectory, or a file glob such as
`*.md` / `*.py`, with caches and package trees excluded. Use the file-search tooling for
discovery (find by name), and reserve content search for files you have already located.
