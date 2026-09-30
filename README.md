# Bitwarden Secrets Manager skill — 0.1

One focused skill: [`SKILL.md`](SKILL.md), named `bitwarden-secrets-manager`. The previous Docker/VPS skill bundle and unrelated A2A probes, identity and platform-forensics documents have been removed from the current tree. History remains available for rollback.

## Install

Copy `SKILL.md` into a `bitwarden-secrets-manager/` folder under the intended Hermes profile's skills directory. Start a new session and load `bitwarden-secrets-manager`. Keep repository tests outside the installed folder.

## Scope

BWS project/account scope, masked bootstrap setup/token rotation, dry-run sync, cache/source limitations, and activation checks. Uses Hermes' native BWS integration: no custom SDK or helper client. Container creation and A2A configuration are outside this skill.

## Checks

Run `python3 -m unittest discover -s tests -v` (standard library only). Tests cover the manifest/package contract—not live vault writes, gateway restarts, or performance benchmarks. Guidance was checked against [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/secrets/bitwarden) and the inspected CLI implementation. No `.env`, credential values, caches, or vault exports belong in this repository, even though it is private.

## Attribution

Consolidated from MIT-licensed Hermes Agent BWS setup/incident guidance. Martin and Hermes Agent maintain this standalone adaptation; not an official Hermes or Bitwarden publication. Original license attribution is retained in [`LICENSE`](LICENSE).
