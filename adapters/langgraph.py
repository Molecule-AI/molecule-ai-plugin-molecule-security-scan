"""LangGraph adaptor — uses the generic rule+skill installer.

LangGraph loads skills from /configs/skills/ via the shared skill_loader,
which is runtime-agnostic. The AgentskillsAdaptor wires rules, skills,
hooks, and commands for Claude Code-style harness environments. For LangGraph,
the same adaptor handles rules and skills; hooks/commands are no-ops
that LangGraph ignores gracefully.
"""
from plugins_registry.builtins import AgentskillsAdaptor as Adaptor  # noqa: F401

