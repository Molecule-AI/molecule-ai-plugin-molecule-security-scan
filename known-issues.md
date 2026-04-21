# Known Issues

Documented bugs, limitations, and unexpected behaviors in `molecule-security-scan`. Each entry includes severity, first-seen version, and workarounds where available.

---

## Issue 1: Snyk API Rate Limits Cause False Blocks

| Field | Value |
|---|---|
| **Severity** | High |
| **Component** | `molecule_security_scan/scanners/snyk.py` |
| **First seen** | 0.1.0 |
| **Status** | Known — rate-limit backoff implemented in 0.2.0 but not yet fully tested |

### Description

Snyk's free tier limits the plugin to 100 API requests per minute. Under high load (multiple workspaces, concurrent skill loads), the plugin may exceed this limit, causing Snyk to return HTTP 429 `Too Many Requests`. When the rate limit is hit, `scan()` raises a `ScannerRateLimitError`. If `fail_open_on_scan_error: true` (the default), the skill is allowed to load despite the scan not completing — which is the safe behavior, but it silently bypasses the CVE gate.

If `fail_open_on_scan_error: false`, the scan failure blocks the skill load, which may be too strict given that the failure is due to rate limits rather than a detected CVE.

### Error message

```
molecule_security_scan.scanners.snyk.ScannerRateLimitError:
Snyk API rate limit exceeded (100/min). Retry after 2026-04-21T09:16:00Z.
If this persists, set `scanner: pip-audit` or reduce scan frequency.
```

### Reproduction

```bash
# Run >100 scans in one minute (simulate multiple concurrent workspaces)
for i in $(seq 1 110); do
  SNYK_TOKEN=<token> python3 -m molecule_security_scan.scan --scanner snyk /tmp/test_req.txt &
done
wait
```

### Workaround

**Short term:** Set `scanner: pip-audit` as the default for all workspaces, or use the Snyk Team plan (1000/min).

**Medium term:** Enable the rate-limit backoff by setting `snyk_rate_limit_backoff_sec: 60` in config. The plugin will retry once after the indicated backoff window:

```yaml
plugins:
  molecule-security-scan:
    enabled: true
    scanner: "snyk"
    snyk_api_key: "${SNYK_TOKEN}"
    snyk_rate_limit_backoff_sec: 60
    fail_open_on_scan_error: false   # set to false only after verifying backoff works
```

**Long term:** Implement a scan result cache keyed by `requirements.txt` content SHA-256, so repeated scans of the same dependency set use a cached result within `cache_ttl_sec`. This is tracked in issue `#29`.

---

## Issue 2: pip-audit False Positives on Dev-Only Dependencies

| Field | Value |
|---|---|
| **Severity** | Medium |
| **Component** | `molecule_security_scan/scanners/pip_audit.py` |
| **First seen** | 0.1.0 |
| **Status** | Known — partial mitigation in 0.2.1 |

### Description

`pip-audit` scans all dependencies declared in `requirements.txt`, including those used only in development (`[dev]` extra) or testing (`[test]` extra). In many skills, dev-only dependencies contain known CVEs that are not reachable in production (e.g., `pytest` vulnerabilities are only exploitable in test runs, not production agent invocations). However, `pip-audit` flags them with the same severity as production dependencies, causing false positive blocks.

Example false positive:

```
pip-audit output:
[
  {
    "name": "pytest",
    "version": "7.1.0",
    "vulns": [
      {
        "id": "PYSEC-2022-XXXXX",
        "fix_versions": ["7.2.0"],
        "severity": "high"
      }
    ]
  }
]
```

`pytest` is declared as `pytest>=7.0.0; extra == "test"` but `pip-audit` reports the CVE regardless of the extra marker.

### Workaround

Exclude dev/test extras from the scanned requirements by preprocessing the file before scanning:

```python
# scripts/filter_prod_only.py
import re

def filter_prod_requirements(req_path: str) -> list[str]:
    """Remove lines with dev/test extras from requirements.txt for scanning."""
    lines = []
    with open(req_path) as f:
        for raw in f:
            raw = raw.rstrip()
            if any(re.search(extra, raw) for extra in [r'; extra == ["\']dev["\']', r'; extra == ["\']test["\']']):
                continue  # skip dev/test lines
            lines.append(raw)
    return lines
```

Call this in `CVEGate.run()` before passing the path to `pip-audit`:

```python
def run(self, skill_path: str) -> ScanResult:
    req_path = os.path.join(skill_path, "requirements.txt")
    prod_req_path = req_path + ".prod"
    with open(prod_req_path, "w") as f:
        f.write("\n".join(filter_prod_requirements(req_path)))
    # ... scan prod_req_path
```

A first-class `exclude_extras` config option is tracked in issue `#33`.

---

## Issue 3: Skill Manifest Cache Staleness Masks Newly Disclosed CVEs

| Field | Value |
|---|---|
| **Severity** | Medium |
| **Component** | `molecule_security_scan/cache.py` |
| **First seen** | 0.2.0 |
| **Status** | Known — documented |

### Description

`skill_manifest_cache_ttl_sec: 300` (default: 5 minutes) caches the skill manifest and scan result to avoid re-scanning the same skill's `requirements.txt` on every load. However, if a CVE is disclosed between scans, the cached result will not reflect the new CVE until the cache expires.

This creates a window of vulnerability where a skill with a newly disclosed critical CVE may load successfully because its previous "no-CVE" scan is still cached.

**Example scenario:**

```
09:00 — skill-calculator v1.0.0 scanned, cached result: no CVEs
09:30 — NVD discloses CVE-2026-9999 affecting a dependency of skill-calculator
09:32 — user loads skill-calculator → cache hit → CVE-2026-9999 NOT checked
09:35 — cache expires (5-min TTL) → next scan catches CVE-2026-9999
```

**Workaround:**

Set `skill_manifest_cache_ttl_sec: 60` for high-security workspaces to limit the stale-cache window:

```yaml
plugins:
  molecule-security-scan:
    skill_manifest_cache_ttl_sec: 60  # minimum 60 seconds
```

For highest-security environments, disable caching entirely by setting `skill_manifest_cache_ttl_sec: 0` — but expect higher latency on repeated skill loads.

A push-invalidation mechanism (Snyk webhook on CVE disclosure) is tracked in issue `#41`.

---

## Issue 4: CVE Database Update Delay — NVD vs. Snyk Gap

| Field | Value |
|---|---|
| **Severity** | Low |
| **Component** | `molecule_security_scan/scanners/snyk.py`, `scanners/pip_audit.py` |
| **First seen** | 0.1.0 |
| **Status** | Known — inherent to CVE disclosure pipelines |

### Description

When a new CVE is published on NVD (National Vulnerability Database), there is a delay before it appears in:
- Snyk's vulnerability database (typically 1–6 hours after NVD publication)
- PyPA Advisory Database (typically 2–24 hours after NVD publication)

During this delay window, `molecule-security-scan` will not detect the CVE even if it is actively being exploited. This is a known limitation of any CVE-scanning system that depends on aggregated advisory databases rather than direct NVD polling.

Typical delay by scanner:

| Scanner | Typical delay after NVD publish |
|---|---|
| Snyk | 1–6 hours |
| pip-audit (PyPA) | 2–24 hours |
| Direct NVD API | 0–30 minutes (not currently used) |

### Workaround

For organizations that need near-real-time CVE detection, supplement `molecule-security-scan` with a host-based IDS (e.g., osquery + YARA rules) that monitors process behavior rather than static dependency scanning.

Combine with a `cron` job that re-scans production skills every 30 minutes, independent of cache:

```bash
# /etc/cron.d/molecule-cve-re-scan
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
*/30 * * * * root python3 -m molecule_security_scan.rescan --workspace /opt/molecule/workspaces/prod >> /var/log/molecule/cve_rescan.log 2>&1
```

The `rescan` command forces a cache-bypass scan of all loaded skills and logs any newly discovered CVEs even if the workspace cache is still fresh.

A direct NVD API integration is tracked in issue `#55`.
