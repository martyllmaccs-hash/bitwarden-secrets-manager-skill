# Bitwarden Secrets Manager skills for Hermes

Reusable Hermes operational skills for configuring and safely operating Bitwarden Secrets Manager (BWS) in Hermes deployments.

## Included

- `skills/dockerized-agent-operations/` — complete Dockerized Hermes operations skill, including the BWS setup/verification reference, source-precedence guidance, and topology guidance.
- `skills/hermes-vps-operations/` — complete Hermes VPS incident/peer operations skill, including secret-source and credential-isolation procedures relevant to BWS-backed deployments.

Both skills retain their upstream Hermes metadata and supporting references/scripts. The repository contains instructions and code only—no `.env`, BWS access token, vault export, project data, or machine-specific credentials. Treat these files as reusable operational guidance and verify commands against the installed Hermes/BWS versions before use.

## Provenance and license

The included skill sources declare MIT licensing in their frontmatter. This repository preserves those skill files and attributes them to Hermes Agent; it does not claim to be an official Hermes publication. See `LICENSE`.
