# Local Development Setup

This runbook covers setting up a local development environment for
`molecule-security-scan`.

---

## Prerequisites

- Python 3.11+
- `gh` CLI authenticated
- Write access to `Molecule-AI/molecule-ai-plugin-molecule-security-scan`

---

## Clone & Bootstrap

```bash
git clone https://github.com/Molecule-AI/molecule-ai-plugin-molecule-security-scan.git
cd molecule-ai-plugin-molecule-security-scan
```

---

## Validating Plugin Structure

```bash
# YAML structure validation
python3 -c "import yaml; yaml.safe_load(open('plugin.yaml'))"
echo "plugin.yaml OK"

# Check all referenced skill paths exist
python3 -c "
import yaml, os
with open('plugin.yaml') as f:
    data = yaml.safe_load(f)
for skill in data.get('skills', []):
    path = f'skills/{skill}/SKILL.md'
    exists = os.path.exists(path)
    print(f'[{\"OK\" if exists else \"MISSING\"}] {path}')
"
```

---

## Testing the CVE Gate Locally

The `builtin_tools/security_scan.py` harness wrapper is not in this repo — it
is provided by the Molecule AI platform at runtime. To test locally:

1. **Install a scanner** (Snyk or pip-audit):
   ```bash
   # Option A: pip-audit (simpler)
   pip install pip-audit
   pip-audit --help

   # Option B: Snyk (richer DB)
   npm install -g snyk
   snyk auth
   ```

2. **Create a test skill with a vulnerable requirements.txt**:
   ```bash
   mkdir -p /tmp/test-skill
   echo "flask==0.0.1" > /tmp/test-skill/requirements.txt
   ```

3. **Run the scanner directly** to verify it works:
   ```bash
   # pip-audit
   pip-audit -r /tmp/test-skill/requirements.txt

   # snyk
   SNYK_TOKEN=your_token snyk test --file=/tmp/test-skill/requirements.txt
   ```

4. **Install the plugin in a test workspace**:
   ```bash
   mol workspace plugin install molecule-security-scan --workspace <test-wsid>
   ```

5. **Trigger a skill load** and check the audit log for `supply_chain` events.

---

## Verifying Scanner Auto-Selection

The gate selects the scanner automatically. To test the priority:

```bash
# Snyk only in PATH → should be selected
which snyk && echo "snyk: AVAILABLE" || echo "snyk: NOT FOUND"
which pip-audit && echo "pip-audit: AVAILABLE" || echo "pip-audit: NOT FOUND"

# The gate logs which scanner was selected — check the audit trail
# for: "detail": {"scanner": "snyk", ...}
```

---

## Simulating Block Mode

To test `mode: block`:

```bash
# Set a known-vulnerable package in a test skill
echo "requests=2.18.0" > /tmp/vuln-skill/requirements.txt

# Install in test workspace with mode: block in config.yaml:
# security_scan:
#   mode: block

# Try to load the vulnerable skill
# Expected: SkillSecurityError in workspace logs
# Expected audit event: outcome=denied, detail.cve_id=...
```

---

## Troubleshooting

### Plugin loads but no scan happens

- Check `builtin_tools/security_scan.py` is available in the harness
- Verify `config.yaml` has `security_scan.mode` set (not absent)
- Check the workspace audit log for `supply_chain` events with `outcome: skip`

### Snyk returns no vulnerabilities

- Confirm `SNYK_TOKEN` is set as a workspace secret
- Run `snyk auth` interactively to verify token validity
- Snyk unauthenticated mode has reduced CVE coverage — pip-audit fallback
  may find issues Snyk misses

### pip-audit fails to parse requirements.txt

- pip-audit requires `pip >= 21.0`
- Check the requirements.txt has valid pip-installable package specs
- Run `pip-compile` to generate a locked requirements.txt if needed

### Workspace blocked unexpectedly

- The gate found a critical/high CVE in a transitive dependency
- Check the audit event: `"outcome": "denied"`, `"detail": {"blocked_cve": "CVE-..."}`
- Fix: update the package to a patched version, then re-load the skill

### False positive on known-safe package

- This is expected for first-party `molecule-*` packages
- These should be excluded from scanning (the plugin skips them automatically)
- If a false positive occurs on a third-party skill, open an issue

---

## Related

- `builtin_tools/security_scan.py` — the platform-provided CVE gate implementation
- `skills/skill-cve-gate/SKILL.md` — full skill documentation
- `molecule-audit` — event retention for scan results
- `molecule-compliance` — runtime OWASP policy companion
- Snyk CLI docs: https://docs.snyk.io/snyk-cli
- pip-audit docs: https://pypi.org/project/pip-audit/
