"""
Prompt templates for AI features.

Phase 3 populates these with actual templates.
Each template is a function that receives a context dict and returns a formatted string.

Registration pattern:
    @register_prompt("explain_log")
    def explain_log_prompt(ctx: dict) -> str:
        return f"Explain this ORFS error: {ctx['log_tail'][-10:]}"
"""
from typing import Callable

PROMPT_REGISTRY: dict[str, Callable[[dict], str]] = {}


def register_prompt(name: str):
    """Decorator to register a prompt template function."""
    def decorator(fn: Callable[[dict], str]):
        PROMPT_REGISTRY[name] = fn
        return fn
    return decorator
