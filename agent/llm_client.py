"""
Unified LLM client wrapper for OpenAI, Google Gemini, and Anthropic Claude.

Provides a single chat() interface that normalizes differences between providers.
Only the selected provider's package is imported (lazy loading).
"""

from typing import List, Dict, Optional
import json

# Provider registry: models and defaults
PROVIDERS = {
    "openai": {
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
        "default": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "gemini": {
        "models": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
        "default": "gemini-2.0-flash",
        "env_key": "GOOGLE_API_KEY",
    },
    "claude": {
        "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "default": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
    },
}


class LLMClient:
    """Thin wrapper normalizing chat completions across LLM providers.

    Usage:
        client = LLMClient(provider="openai", api_key="sk-...", model="gpt-4o-mini")
        text = client.chat(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
            ],
            temperature=0.3,
            json_mode=False,
        )
    """

    def __init__(self, provider: str, api_key: str, model: Optional[str] = None):
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS.keys())}")
        self.provider = provider
        self.api_key = api_key
        self.model = model or PROVIDERS[provider]["default"]
        self._client = None
        self._init_client()

    def _init_client(self):
        if self.provider == "openai":
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
            self._client = OpenAI(api_key=self.api_key)

        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
            except ImportError:
                raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
            genai.configure(api_key=self.api_key)
            self._client = genai  # store module ref; model created per-call for system instruction support

        elif self.provider == "claude":
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
            self._client = Anthropic(api_key=self.api_key)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             json_mode: bool = False) -> str:
        """Send chat messages and return the response text.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            temperature: Sampling temperature (0.0 - 1.0)
            json_mode: If True, request JSON-formatted output

        Returns:
            Response text string
        """
        if self.provider == "openai":
            return self._chat_openai(messages, temperature, json_mode)
        elif self.provider == "gemini":
            return self._chat_gemini(messages, temperature, json_mode)
        elif self.provider == "claude":
            return self._chat_claude(messages, temperature, json_mode)

    def _chat_openai(self, messages, temperature, json_mode):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _chat_gemini(self, messages, temperature, json_mode):
        # Separate system message from conversation
        system_msg = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [msg["content"]]})

        # Create model with system instruction (Gemini requires this at model level)
        model = self._client.GenerativeModel(
            self.model,
            system_instruction=system_msg,
        )

        generation_config = {"temperature": temperature}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        response = model.generate_content(contents, generation_config=generation_config)
        return response.text

    def _chat_claude(self, messages, temperature, json_mode):
        # Claude uses a separate system parameter
        system_msg = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        # Claude has no native JSON mode; enforce via system prompt
        if json_mode:
            json_instruction = "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no explanation, no extra text."
            if system_msg:
                system_msg += json_instruction
            else:
                system_msg = "You are a helpful assistant." + json_instruction

        kwargs = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = self._client.messages.create(**kwargs)
        return response.content[0].text
