"""DeepAgents adaptor — uses the generic rule+skill installer.

DeepAgents loads skills from /configs/skills/ via the shared skill_loader,
which is runtime-agnostic. The AgentskillsAdaptor wires rules, skills,
hooks, and commands for Claude Code-style harness environments. For DeepAgents,
the same adaptor handles rules and skills; hooks/commands are no-ops
that DeepAgents ignores gracefully.
"""
from plugins_registry.builtins import AgentskillsAdaptor as Adaptor  # noqa: F401

