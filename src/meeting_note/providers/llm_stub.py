from __future__ import annotations


class StubLLMProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        del max_tokens
        return "Stub LLM response. Configure a local GGUF provider before production use."
