# molecule-security-scan — CVE Gate for Skill Dependencies

`molecule-security-scan` is a **supply-chain CVE gate** plugin. It wraps
`builtin_tools/security_scan.py` and runs Snyk or pip-audit against a
skill's `requirements.txt` before the skill loads, blocking or warning on
critical/high CVEs.

**Version:** 1.0.0
**Runtime:** `langgraph`, `claude_code`, `deepagents`
**Related:** `molecule-audit` (event retention), `molecule-compliance` (runtime
OWASP policy)

---

## Repository Layout

```
molecule-security-scan/
├── plugin.yaml              — Plugin manifest
├── skills/
│   └── skill-cve-gate/
│       └── SKILL.md         — Full skill documentation
└── builtin_tools/           — (harness-provided, not in this repo)
    └── security_scan.py     — CVE gate implementation
```

---

## How It Works

When a skill is about to load, the gate runs a CVE scanner against its
`requirements.txt`. Selection is automatic:

| Scanner | Requires | When selected |
|---|---|---|
| **Snyk CLI** | `snyk` binary in PATH + `SNYK_TOKEN` env | Available — preferred |
| **pip-audit** | `pip-audit` binary in PATH | Fallback when Snyk absent |
| **skip** | — | Neither available → skip silently |

---

## Modes

Configure in workspace `config.yaml`:

```yaml
security_scan:
  mode: warn      # off | warn | block
```

| Mode | Behaviour |
|---|---|
| `off` | Skip entirely. Useful in air-gapped CI. |
| `warn` | Log WARNING + audit event on critical/high. Load skill anyway. |
| `block` | Raise `SkillSecurityError`. Skill does not load. |

**Rollout order:** `warn` first → measure → then `block` once clean.

---

## When to Install

✅ Install on workspaces that:
- Install skills from third-party sources (marketplace, agentskills.io, uploads)
- Run in a production tenant where agent compromise is meaningful
- Must satisfy a supply-chain audit (SOC 2, ISO 27001 control A.8.28)

❌ Skip on workspaces that only use first-party `molecule-*` plugins —
those are vetted at PR-review time in monorepo CI.

---

## Audit Trail

Every scan writes to the audit log via `audit.log_event`:

```json
{
  "event_type": "supply_chain",
  "action": "cve_scan",
  "resource": "skill-name:version",
  "outcome": "pass",
  "detail": {
    "scanner": "snyk",
    "critical": 0,
    "high": 0,
    "medium": 2,
    "low": 5
  }
}
```

Failures (mode=block) log `outcome: denied` + the blocking CVE ID.
**Pair with `molecule-audit`** to get the full JSONL trail.

---

## SNYK_TOKEN Setup

Set via workspace secret (never in `config.yaml`):

```bash
curl -X POST http://localhost:8080/workspaces/$WS_ID/secrets \
  -H "Content-Type: application/json" \
  -d '{"key":"SNYK_TOKEN","value":"..."}'
```

The token is injected at container start as an env var.

---

## Full Configuration Reference

```yaml
security_scan:
  mode: warn
  # scanner: pip-audit       # force override (default: auto)
  severity_threshold: high   # critical | high | medium | low
  fail_open_if_no_scanner: true
```

- `severity_threshold` — only findings ≥ this level trigger warn/block.
  Medium and low are always INFO-logged only.
- `fail_open_if_no_scanner` — `true` = skip silently if neither tool present;
  `false` = treat as block event.

---

## Anti-Patterns

- **Do not** set `mode: block` during initial rollout — strand risk.
- **Do not** install without `molecule-audit` — scan results disappear.
- **Do not** scan first-party `molecule-*` plugins — vetted at commit time.
- **This is not your only supply-chain defence.** It catches known CVEs only.
  Complement with deterministic lockfiles and registry allowlists.

---

## Development

### Prerequisites

- Node.js >= 18 (for markdownlint, if editing `.md` files)
- Python 3.11+ (for YAML validation)
- `gh` CLI authenticated
- Write access to `Molecule-AI/molecule-ai-plugin-molecule-security-scan`

### Setup

```bash
git clone https://github.com/Molecule-AI/molecule-ai-plugin-molecule-security-scan.git
cd molecule-ai-plugin-molecule-security-scan

# Validate plugin.yaml
python3 -c "import yaml; yaml.safe_load(open('plugin.yaml'))"
echo "plugin.yaml OK"
```

### Pre-Commit Checklist

```bash
# YAML structure
python3 -c "import yaml; yaml.safe_load(open('plugin.yaml'))"

# No credentials in plugin.yaml
python3 -c "
import re, sys
with open('plugin.yaml') as f:
    content = f.read()
patterns = [r'sk.ant', r'ghp.', r'AKIA[A-Z0-9]']
if any(re.search(p, content) for p in patterns):
    print('FAIL: possible credentials found')
    sys.exit(1)
print('No credentials: OK')
"
```

---

## Release Process

1. Review changes: `git log origin/main..HEAD --oneline`
2. Bump `version` in `plugin.yaml` (semver)
3. Update `**Version:**` in this CLAUDE.md if conventions changed
4. Commit: `chore: bump version to X.Y.Z`
5. Tag and push: `git tag vX.Y.Z && git push origin main --tags`
6. Create GitHub Release with changelog

---

## Known Issues

See `known-issues.md` at the repo root.
