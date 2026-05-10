# molecule-security-scan

Supply-chain CVE gate for skill dependencies. Runs Snyk or pip-audit against a skill's `requirements.txt` before the skill loads, blocking or warning on critical/high CVEs.

## How it works

Before a skill is activated, the plugin:
1. Locates the skill's `requirements.txt` (in `skills/<name>/`)
2. Runs `pip-audit` (default) or `snyk test` (if configured)
3. Filters findings by severity threshold
4. Blocks or warns based on config

Critical/High CVEs block by default. Medium/Low warn.

## Install

### In org template (org.yaml)

```yaml
plugins:
  - molecule-security-scan
```

### From URL (community install)

```
github://Molecule-AI/molecule-ai-plugin-molecule-security-scan
```

## Configuration

```yaml
security_scan:
  mode: block       # or: warn
  min_severity: high # block CVEs at or above this level
  scanner: pip-audit # or: snyk
  snyk_token_env: SNYK_TOKEN  # env var name for Snyk token
```

## Runtimes

- `langgraph` — primary
- `claude_code` — supported
- `deepagents` — supported

## Skills

- `skill-cve-gate` — agent guidance on CVE findings

## Architecture

```
skills/
  skill-cve-gate/   # SKILL.md — agent guidance on CVE findings
adapters/
  langgraph.py      # Registers scanner and gate logic
runbooks/
  setup.md          # Snyk token setup, pip-audit installation
```

## Known issues

See [known-issues.md](known-issues.md).

## License

Business Source License 1.1 — © Molecule AI.
