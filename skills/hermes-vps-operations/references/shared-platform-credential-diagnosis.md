# Two instances on one platform credential

Use when a platform bot (Telegram, Discord, Slack) answers its own owner as a stranger — a pairing
prompt, "I don't recognize you", an authorisation denial — while the local gateway reports the
platform connected, or when inbound messages only *sometimes* reach the agent.

## The question to answer first: did THIS deployment emit it?

A pairing prompt looks like local state (a wiped store, a fresh profile) and usually is not. Three
cheap measurements separate "my store is empty" from "someone else is holding my credential".

```bash
# 1. The store the prompt would have written to (empty = we minted nothing)
hermes pairing list                      # reads <HERMES_HOME>/platforms/pairing
find "$HERMES_HOME/platforms/pairing" "$HERMES_HOME/pairing" -type f

# 2. Did we log an unauthorised/pairing event?
grep -ri "unauthor\|pairing" "$HERMES_HOME/logs/gateway.log" "$HERMES_HOME/logs/errors.log"

# 3. Does the exact wording the user quoted exist in the running build?
grep -rn "recognize you yet" /opt/hermes --include=*.py   # gateway/run_inbound_unauthorized.py
```

Search the whole install rather than a `--include=*.py` subset: a prompt can also be assembled by a
plugin from a YAML/JSON template string, and a Python-only miss reads as "this build cannot send
this" when the build could.

Shipped prompt text lives in `gateway/run_inbound_unauthorized.py` (`pairing_code_reply()`), and the
CLI-side template is in `hermes_cli/pairing.py`. Compare the user's quoted wording character by
character — greeting punctuation, "Your pairing code" versus "Here's your pairing code", and the
shape of the approval line. A prompt the running install does not contain was produced by other
software.

**Verdict:** empty store + no log event + wording absent from the build = this deployment did not
send it. Another process holds the same bot token. Any one of the three alone is weak; all three
are conclusive.

## Confirm a second consumer

```bash
# Telegram refuses concurrent getUpdates; the loser logs a conflict id.
grep -c "polling conflict" "$HERMES_HOME/logs/gateway.log"
grep "polling conflict" "$HERMES_HOME/logs/gateway.log" | head -1   # first appearance = when it started
grep "polling conflict" "$HERMES_HOME/logs/gateway.log" | tail -1   # still active?
```

`Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`
is only reachable by two clients polling one token. The first occurrence timestamps when the second
instance began — a far more useful fact than any guess about which machine it is.

Quantify interception with the per-bot receipt file in `HERMES_HOME`:
`telegram_update_receipts_<bot_id>.json` maps every update id this poller consumed to a timestamp.
The filename's bot id also identifies which bot identity this home polls. Gaps in the id range are
updates the other instance swallowed; a max timestamp that stops advancing while the user keeps
messaging means every inbound update is currently going elsewhere.

**Do not reach for `getUpdates` to see what the other client is receiving.** A getUpdates call is a
consume, not a read: it takes updates off the queue and can displace the legitimate poller's own
stream, so the diagnostic steals exactly the traffic it was meant to observe. The receipt file above
answers the same question without touching the queue.

## Pairing-code forensics

A code quoted by the user is evidence about *who minted it*, and it is worth reading before anyone
tries to clear the symptom by approving it.

```bash
grep -n -E "ALPHABET|CODE_LENGTH" /opt/hermes/gateway/pairing.py
# ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  (excludes 0/O and 1/I), CODE_LENGTH = 8
```

Codes are generated from that unambiguous alphabet and persisted only as salted hashes in the minting
instance's own pending store (`<HERMES_HOME>/platforms/pairing`). Two consequences:

- Nobody can recover a code from disk, so a code that reached an inbox came from the sender's own
generation — matching format proves the sender knows the Hermes flow, and rules out a code lifted
from the victim's state.
- `hermes pairing approve <platform> <code>` only resolves against the store that minted the code. Run
on the wrong box it returns "not found or expired", so a prompt instructing the owner to approve a
foreign code could never have worked. Do not present approving it as the fix, and say plainly that
the command was a dead end: the remediation is removing the other consumer's access.

## Establish the identity and the shared vector

```bash
# Token stays in-shell; print only identity metadata.
TOK=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$HERMES_HOME/.env" | cut -d= -f2-)
curl -s "https://api.telegram.org/bot$TOK/getMe"                 # -> bot id, username
curl -s "https://api.telegram.org/bot$TOK/getWebhookInfo"       # -> url, pending_update_count
unset TOK
```

Then compare the local value against the secret manager without printing either: hash both with
`sha256[:8]` and compare digests. Matching digests prove a shared source, which turns the search
space into "every machine holding a machine account for that project" — such a machine fetches the
platform token at every startup, so its token is not necessarily in a file on the box you are
looking at.

## Consequence and remediation

- Treat it as credential exposure, not a reconnect loop: the other process can read the owner's
  direct messages and send as the bot.
- Rotation at the provider (for Telegram, @BotFather `/revoke`) is the only control that removes the
  other instance's access without touching that host, and it needs nothing from your side.
- Deliver the new value through the secret manager; never in chat, and never as a literal in a file
  you write or a record you append.
- After rotation the other client starts failing authentication and stops on its own; verify by
  re-reading the conflict count and the receipt file, not by assuming.
- Rotation cuts *this* deployment off too, because the running process still holds the revoked value.
  State that plainly instead of leaving the owner to discover silence: the confirmations are `getMe`
  returning `Unauthorized` for the old value, a fresh `telegram.error.InvalidToken` in
  `logs/errors.log`, and no new `polling conflict` line. Service returns only after the new value is
  installed where the process actually reads it (the secret manager overrides `.env` at startup) and
  the process restarts.
- While the shared project is open, report the blast radius by secret *name* so the owner can decide
  what else to rotate: a project holding a platform token usually holds model-provider keys, the
  dashboard basic-auth password, and any peer/bearer tokens in the same list.

## Attribution discipline

Timing coincidence is evidence, not identity. Say which moment the second consumer appeared and
which restart of which host coincides with it, then ask the user which host that maps to — they
know their inventory and you cannot see it. Asserting a named agent as the culprit when the user
knows that agent is not involved costs the diagnosis and the credibility of everything after it.

## Log location trap

`logs/gateways/<profile>/` contains files named `current`, `lock`, `state` — no `.log` suffix — and
mostly holds startup banners. Adapter, message, and conflict lines are in `logs/gateway.log`,
`logs/errors.log`, and `logs/agent.log`. A `*.log` glob over the gateway directory returns nothing
and reads as "there are no logs", which sends you hunting a logging bug that does not exist.
