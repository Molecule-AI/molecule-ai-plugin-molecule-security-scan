# molecule-ai-plugin-molecule-security-scan

## Purpose

Supply-chain CVE gate for skill dependencies. Wraps `builtin_tools/security_scan.py` and runs either Snyk or `pip-audit` against a skill's `requirements.txt` before the skill loads, blocking the load or issuing a warning when critical or high severity CVEs are found. Opt-in per workspace.

**Skill exposed:** `skill-cve-gate`

**Typical use:** Prevent a vulnerable skill from loading in a production workspace until the CVE is resolved or a human reviews the risk.

---

## Snyk vs pip-audit Comparison

| Dimension | Snyk | pip-audit |
|---|---|---|
| **CVE data source** | Snyk Vulnerability Database (updated continuously) | Python Packaging Advisory Database (cached, PyPA) |
| **API key required** | Yes — `SNYK_TOKEN` env var or `snyk_api_key` config | No |
| **Rate limits** | 100 requests/min on free tier; 1000/min on Team plan | None (local subprocess) |
| **Offline operation** | No — requires API call | Yes — works with local cache |
| **Output format** | JSON / SARIF | JSON / CSV (pip-audit >= 22.5) |
| **Fix suggestions** | Yes — pull-request generation | No — only identification |
| **License scanning** | Yes | No |
| **Supported by this plugin** | Yes (default) | Yes (fallback) |
| **False positive rate** | Low | Moderate (dev-only extras flagged) |
| **Setup complexity** | Higher (token required) | Lower (zero-config fallback) |

**Default behavior:** Snyk is used when `snyk_api_key` is present in config; `pip-audit` is used as fallback when it is not.

---

## Skill Pre-Load Timing

`skill-cve-gate` executes synchronously during the skill load pipeline, before the skill's `__init__` or `invoke` methods are called. The gate cannot add latency to agent responses after the skill has loaded — it only gates the load itself.

```
skill load request
  └── skill-cve-gate.run(path/to/requirements.txt)
        ├── Parse requirements.txt
        ├── Run Snyk or pip-audit
        ├── Filter by severity threshold
        └── PASS → skill loads
             └── FAIL (block mode) → skill_load_error logged; agent blocked
             └── FAIL (warn mode)  → warning logged; skill loads anyway
```

Execution time by scanner:

| Scanner | Typical duration (10 deps) | 95th percentile |
|---|---|---|
| Snyk (cached) | ~2 s | ~5 s |
| Snyk (uncached) | ~5–15 s | ~30 s |
| pip-audit (local) | ~3–10 s | ~20 s |

Set `scan_timeout_sec: 60` in config to give the scan time to complete before the gate times out.

---

## CVE Severity Thresholds

Only `critical` and `high` severity CVEs trigger the gate by default. This is configurable.

| Severity | Snyk level | pip-audit level | Default action |
|---|---|---|---|
| `critical` | `critical` | `critical` | `block` (or `warn` if `warn_on_critical: true` + `block_on_critical: false`) |
| `high` | `high` | `high` | Configurable via `warn_on_high` / `block_on_high` |
| `medium` | `medium` | `medium` | Logged only (never blocks) |
| `low` | `low` | `low` | Logged only |

Configuring the threshold:

```yaml
plugins:
  molecule-security-scan:
    enabled: true
    scanner: "snyk"              # "snyk" or "pip-audit"; default: snyk if token present else pip-audit
    snyk_api_key: "${SNYK_TOKEN}" # read from env var; never hardcode
    scan_timeout_sec: 60
    severity_threshold: "high"   # block/warn on this severity and above; options: critical, high
    block_on_critical: true      # hard block on critical CVEs; default true
    warn_on_high: true           # warn but allow load on high CVEs; default true
    block_on_high: false         # block on high CVEs; default false
    allowlist:                   # CVE IDs to ignore regardless of severity
      - "SNYK-PYTHON-REQUESTS-1234567"
      - "PYSEC-2019-123"
    skill_manifest_cache_ttl_sec: 300  # cache skill manifest to avoid re-scanning; default 300
```

---

## Opt-In Per Workspace

The plugin is disabled by default. Enable it per workspace via `workspace-settings.yaml`:

```yaml
plugins:
  molecule-security-scan:
    enabled: true
    scanner: "snyk"
    snyk_api_key: "${SNYK_TOKEN}"
```

Workspaces without this entry silently skip the CVE gate.

---

## Configuration Reference

### Workspace Settings

```yaml
plugins:
  molecule-security-scan:
    enabled: true                             # required
    scanner: "snyk"                           # "snyk" (default if token) or "pip-audit" (default if no token)
    snyk_api_key: "${SNYK_TOKEN}"             # Snyk API token; read from env var
    scan_timeout_sec: 60                     # seconds; default 30; min 5; max 300
    severity_threshold: "high"                # critical | high; default high
    block_on_critical: true                   # block if true, warn if false; default true
    warn_on_high: true                        # warn if true; default true
    block_on_high: false                      # block if true, warn if false; default false
    allowlist:                                # list of CVE IDs to always pass
      - "SNYK-PYTHON-URLLIB3-1234567"
    skill_manifest_cache_ttl_sec: 300         # cache skill manifest; default 300; 0 disables cache
    log_scan_results: true                    # write results to audit log; default true
    fail_open_on_scan_error: true            # allow skill load if scanner fails; default true
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SNYK_TOKEN` | Only for Snyk scanner | Snyk API token. Must have `api` scope. |
| `SNYK_API_URL` | No | Override Snyk API endpoint (for Snyk API proxy). Default: `https://api.snyk.io`. |
| `PIP_AUDIT_PATH` | No | Path to `pip-audit` binary. Default: find on PATH. |
| `PIP_AUDIT_CACHE_DIR` | No | Directory for pip-audit dependency cache. Default: `~/.cache/pip-audit`. |

---

## Runtimes Supported

| Runtime | Min Version | Notes |
|---|---|---|
| `langgraph` | 0.2.x | `CVEGate.invoke()` called pre-skill-load in graph compile |
| `claude_code` | 0.6.x | `CVEGate.run()` called in skill loader hook |
| `deepagents` | 0.4.x | Works via `CVEGateProxy` shim |

---

## Development Setup

```bash
# 1. Clone
git clone https://github.com/molecule-ai/molecule-ai-plugin-molecule-security-scan.git
cd molecule-ai-plugin-molecule-security-scan

# 2. Create venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Validate plugin.yaml
python3 -c "import yaml; yaml.safe_load(open('plugin.yaml'))" && echo "plugin.yaml OK"

# 4. Run unit tests
pytest tests/unit/ -v

# 5. Smoke test with pip-audit (no token needed)
SNYK_TOKEN= pytest tests/unit/test_scanner_pip_audit.py -v

# 6. Smoke test with Snyk (requires SNYK_TOKEN)
SNYK_TOKEN=<your-token> pytest tests/unit/test_scanner_snyk.py -v

# 7. Full integration test
pytest tests/integration/ -v --require-core
```

For local `pip-audit` testing without a skill's `requirements.txt`:

```bash
# Create a test requirements file
echo "requests==2.26.0" > /tmp/test_requirements.txt
python3 -m molecule_security_scan.scan --scanner pip-audit /tmp/test_requirements.txt
```

---

## Testing

| Test suite | Command | CI |
|---|---|---|
| Unit tests | `pytest tests/unit/` | Required |
| Scanner selection logic | `pytest tests/unit/test_scanner_selection.py -v` | Required |
| pip-audit integration | `pytest tests/unit/test_scanner_pip_audit.py -v` | Required |
| Snyk integration | `pytest tests/unit/test_scanner_snyk.py -v` | Required (guarded by `SNYK_TOKEN`) |
| Allowlist logic | `pytest tests/unit/test_allowlist.py -v` | Required |
| Severity threshold | `pytest tests/unit/test_severity.py -v` | Required |
| Cache TTL | `pytest tests/unit/test_cache.py -v` | Required |
| Integration (requires stub core) | `pytest tests/integration/` | Required |

---

## Release Process

1. Bump the version in `pyproject.toml` and `plugin.yaml`.
2. Update `CHANGELOG.md` with a dated entry.
3. Run full test suite: `pytest tests/ -v`.
4. Publish to PyPI: `python3 -m build && twine upload dist/*`.
5. Tag the release: `git tag vX.Y.Z && git push origin vX.Y.Z`.
6. Update plugin registry entry if applicable.
