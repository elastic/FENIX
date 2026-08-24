# Security policy

## Reporting a vulnerability

If you believe you have found a security issue **in FENIX itself** (the CLI,
helpers, or packaging — not a detection gap in a third-party product), report
it through Elastic's vulnerability process:

https://www.elastic.co/community/security

Do not open a public GitHub issue for vulnerabilities.

## What this repository is

FENIX is a **lab-only snapshot** (not an officially supported Elastic product)
for reproducing Linux fileless-execution patterns with **benign** sample
payloads (they print `hello from fenix` or sleep). It is intended for
authorized detection engineering on systems you own and control.

It is **not** malware, a C2 framework, or an exploit kit. Compiled helpers
and interpreter memfd loaders may still be flagged by antivirus or GitHub
automated scanners because they call `memfd_create`, `execveat`, and related
APIs. Those matches are expected false positives for this project.

## Scope

Please report:

- Accidental inclusion of credentials, private URLs, or non-lab payloads
- Bugs that would execute untrusted input without an explicit lab command

Do **not** request persistence, privilege escalation, stealth, or
weaponized payloads. Those are out of scope
(see [CONTRIBUTING.md](CONTRIBUTING.md)). This repository does not
accept GitHub issues or pull requests.
