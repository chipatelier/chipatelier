"""AI service module — scaffolded in Phase 1, implemented in Phase 3.

This module provides the interface for AI-powered features:
  - Log explanation (explain ORFS errors in plain language)
  - Timing path explanation
  - DRC violation explanation
  - Config advisor (suggest config parameter improvements)
  - Context-aware chat

All actual LLM calls are implemented in Phase 3 (Ollama wiring).
Phase 1 provides the scaffold: interfaces, context builder, and route stubs.

Privacy constraint (CLAUDE.md): NEVER send GDS/DEF file contents, PDK files,
or student PII to any LLM backend (cloud or local).
"""
