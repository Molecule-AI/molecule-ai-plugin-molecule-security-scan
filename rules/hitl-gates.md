# HITL Gates — molecule-security-scan

## Status: Not Applicable

This plugin does not implement Human-in-the-Loop (HITL) gates. `molecule-security-scan` is a deterministic, automated CVE gate — it evaluates a skill's dependency manifest against a known CVE database and makes a binary allow/block decision without human review.

The design intentionally omits HITL gates for the following reasons:

1. **Speed of disclosure.** CVE disclosures can happen at any time. A human-review step in the skill load path would introduce latency and create a backlog of unreviewed skills during a mass CVE event.

2. **Deterministic policy.** CVE severity thresholds (`block_on_critical`, `warn_on_high`) are policy decisions encoded in config, not judgment calls that require human input. The allowlist is the intended escape hatch for cases where human review is needed.

3. **SIEM alerting.** Scan results (including `cve_scan_blocked`) are written to the audit log and forwarded to the SIEM. Security operators receive automated alerts on blocked skills and can re-enable a blocked skill manually after patching.

If you need to add HITL gates to this plugin (e.g., "block on critical CVEs unless a security officer approves in writing"), the design would follow the pattern in `molecule-compliance`:

1. Define the gate condition in `rules/gates/cve-human-approval.md`.
2. Implement the gate as a subclass of `HITLGate` in `molecule_security_scan/gates/`.
3. Add a human-approval callback (webhook / email / ticket creation) that pauses the skill load until approved.
4. Register the gate in `plugin.yaml` under `gates:`.
5. Document the approval SLA and escalation path in this file.
