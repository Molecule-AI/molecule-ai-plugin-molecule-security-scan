# Local Development Setup — molecule-security-scan

Step-by-step guide for setting up a local development environment for `molecule-ai-plugin-molecule-security-scan`.

---

## Prerequisites

- Python 3.11+
- `git`
- `pip` or `uv`
- (Optional) `docker` for containerized testing
- (Optional) A Snyk account for Snyk scanner testing

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/molecule-ai/molecule-ai-plugin-molecule-security-scan.git
cd molecule-ai-plugin-molecule-security-scan
```

---

## Step 2: Validate plugin.yaml

```bash
python3 -c "import yaml; yaml.safe_load(open('plugin.yaml'))" && echo "plugin.yaml OK"
```

Expected output: `plugin.yaml OK`

---

## Step 3: Install the Package in Development Mode

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the package plus development dependencies (`pytest`, `pyyaml`, `requests`).

Verify the installation:

```bash
python3 -c "from molecule_security_scan import CVEGate; print('import OK')"
```

---

## Step 4: Install pip-audit (Fallback Scanner — No Token Needed)

```bash
pip install pip-audit>=2.5.0
pip-audit --version
```

`pip-audit>=2.5.0` is required for JSON output format support.

---

## Step 5: Set Up SNYK_TOKEN (Optional — for Snyk Scanner Testing)

1. Create a Snyk account at https://snyk.io if you do not have one.
2. Retrieve your API token from https://app.snyk.io/settings/api-tokens.
3. Export it locally (do not commit):

```bash
export SNYK_TOKEN="your-snyk-api-token-here"
echo $SNYK_TOKEN  # confirm it prints the token
```

For persistence across sessions, add to your shell profile:

```bash
# ~/.bashrc or ~/.zshrc
export SNYK_TOKEN="your-snyk-api-token-here"
```

**Security note:** Never commit `SNYK_TOKEN` to version control. The repo's `.gitignore` should include `.env` and any file containing `SNYK_TOKEN`.

---

## Step 6: Create a Test Skill with requirements.txt

```bash
# Create a test skill directory
mkdir -p /tmp/test-skill
cat > /tmp/test-skill/requirements.txt << 'EOF'
requests==2.26.0
urllib3==1.26.0
certifi==2023.07.22
EOF
echo "Skill created at /tmp/test-skill with $(wc -l < /tmp/test-skill/requirements.txt) dependencies"
```

---

## Step 7: Run a CVE Scan with pip-audit (No Token Required)

```bash
python3 -c "
import os, sys
from molecule_security_scan import CVEGate
from molecule_security_scan.config import PluginConfig

config = PluginConfig(
    enabled=True,
    scanner='pip-audit',
    scan_timeout_sec=60,
    severity_threshold='high',
    block_on_critical=True,
    warn_on_high=True,
    block_on_high=False,
    allowlist=[],
)
gate = CVEGate(config=config)
result = gate.run('/tmp/test-skill')
print(f'Scan result: {result.result}')
print(f'CVEs found: {len(result.cves)}')
for cve in result.cves:
    print(f'  {cve[\"id\"]} — {cve[\"package\"]} {cve[\"severity\"]}')
"
```

Expected output (example — depends on current CVE database state):

```
Scan result: cve_scan_warn
CVEs found: 1
  PYSEC-2023-XXXX — requests high
```

If the `requests` version in the test file has no known CVEs, output is `cve_scan_ok` with 0 CVEs.

---

## Step 8: Run a CVE Scan with Snyk (Requires SNYK_TOKEN)

```bash
python3 -c "
import os, sys
from molecule_security_scan import CVEGate
from molecule_security_scan.config import PluginConfig

token = os.environ.get('SNYK_TOKEN')
if not token:
    print('SNYK_TOKEN not set — skipping Snyk test')
    sys.exit(0)

config = PluginConfig(
    enabled=True,
    scanner='snyk',
    snyk_api_key=token,
    scan_timeout_sec=60,
    severity_threshold='high',
    block_on_critical=True,
    warn_on_high=True,
    block_on_high=False,
    allowlist=[],
)
gate = CVEGate(config=config)
result = gate.run('/tmp/test-skill')
print(f'Scanner: Snyk')
print(f'Scan result: {result.result}')
print(f'CVEs found: {len(result.cves)}')
for cve in result.cves:
    print(f'  {cve[\"id\"]} — {cve[\"package\"]} {cve[\"severity\"]}')
"
```

Expected output (example):

```
Scanner: Snyk
Scan result: cve_scan_warn
CVEs found: 2
  SNYK-PYTHON-REQUESTS-1234567 — requests high
  SNYK-PYTHON-URLLIB3-2345678 — urllib3 high
```

---

## Step 9: Test the Block / Warn Modes

### Warn mode (default — skill loads with warning)

```python
from molecule_security_scan import CVEGate, PluginConfig, ScanResult

config = PluginConfig(
    enabled=True, scanner='pip-audit',
    block_on_critical=False,  # don't block on critical
    warn_on_high=True,
    block_on_high=False,      # warn but don't block on high
)
gate = CVEGate(config=config)
result = gate.run('/tmp/test-skill')
print(result.result)   # cve_scan_warn
print(result.skill_loaded)  # True
```

### Block mode (strict — skill blocked on critical/high CVEs)

```python
config = PluginConfig(
    enabled=True, scanner='pip-audit',
    block_on_critical=True,
    warn_on_high=False,
    block_on_high=True,       # block on high CVEs
)
gate = CVEGate(config=config)
result = gate.run('/tmp/test-skill')
print(result.result)         # cve_scan_blocked (if CVEs found)
print(result.skill_loaded)   # False
```

---

## Step 10: Test the Allowlist

```python
config = PluginConfig(
    enabled=True, scanner='pip-audit',
    block_on_critical=True, block_on_high=True,
    # Allowlist the exact CVE that will be found in test skill
    allowlist=['PYSEC-2023-XXXX'],  # replace with actual CVE found above
)
gate = CVEGate(config=config)
result = gate.run('/tmp/test-skill')
print(result.result)    # cve_scan_ok or cve_allowlisted
print(result.skill_loaded)  # True
```

---

## Step 11: Run the Unit Tests

```bash
# All unit tests (pip-audit)
pytest tests/unit/ -v

# Snyk tests (requires SNYK_TOKEN)
SNYK_TOKEN="${SNYK_TOKEN}" pytest tests/unit/test_scanner_snyk.py -v

# Integration tests (requires stub core)
pytest tests/integration/ -v --require-core
```

---

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `ScannerConfigError: requirements.txt not found` | Skill has no `requirements.txt` | Add `requirements.txt` to the skill, or this is expected (skill will be skipped) |
| `pip-audit` returns text instead of JSON | `pip-audit` version < 2.5.0 | `pip install 'pip-audit>=2.5.0'` |
| `pip-audit` exits code 1, no output | Empty `requirements.txt` | Add at least one dependency or expect `cve_scan_skipped` |
| `SNYK_TOKEN` not recognized | Token not exported in current shell | `export SNYK_TOKEN=...` in the same shell session |
| `ScannerRateLimitError` | Snyk API rate limit exceeded (100/min) | Wait 60 s, set `scanner: pip-audit`, or upgrade to Snyk Team plan |
| `ScannerParseError: non-JSON output` | Wrong `pip-audit` version or non-pip dependency | Check `pip-audit --version`; verify `--format json` supported |
| Scan returns no CVEs on known-vulnerable dep | pip-audit cache is stale | `pip-audit --version` and `pip-audit --cache-dir /tmp/pa-cache` with fresh cache |
| Allowlisted CVE still showing as found | CVE ID in allowlist doesn't match scanner's ID format | Use exact scanner ID: `SNYK-PYTHON-REQUESTS-1234567` not `PYSEC-2023-123` |
| `skill_manifest_cache_ttl_sec: 0` not disabling cache | Code bug — minimum TTL enforced | Set to `1` as minimum; tracked in issue `#44` |
| Snyk scan slow (> 15 s) | Uncached dependencies | First scan per dependency set always slower; subsequent scans use cache |
| `ImportError: No module named molecule_security_scan` | Package not installed in venv | `pip install -e ".[dev]"` with venv activated |
| `plugin.yaml` YAML parse error | Indentation error | Re-validate with `python3 -c "import yaml; yaml.safe_load(open('plugin.yaml'))"` |
