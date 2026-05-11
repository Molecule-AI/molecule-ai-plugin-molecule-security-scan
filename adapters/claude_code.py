"""Claude Code adaptor — uses the generic rule+skill+hooks installer.

The skill-cve-gate skill is a policy/documentation layer. builtin_tools.security_scan
does not expose @tool-decorated functions — the CVE gate runs as a pre-load hook
inside the skill loader, blocking or warning before the skill code executes.
The AgentskillsAdaptor installs the SKILL.md onto the Claude Code harness so the
agent knows when to activate the gate.
"""
from plugins_registry.builtins import AgentskillsAdaptor as Adaptor  # noqa: F401
