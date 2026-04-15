"""Built-in model pricing table.

Prices are USD per 1M tokens (input, output).
Sources: provider pricing pages as of 2024-12.
"""

# (input_per_1m, output_per_1m)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o3-mini": (1.10, 4.40),
    # Anthropic
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-3.5": (0.80, 4.00),
    "claude-sonnet-3.5": (3.00, 15.00),
    "claude-haiku-3": (0.25, 1.25),
    "claude-opus-3": (15.00, 75.00),
    # Google
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-2.5-pro": (1.25, 10.00),
    # Meta via Groq / Together / etc.
    "llama-3-70b": (0.59, 0.79),
    "llama-3-8b": (0.05, 0.08),
    "llama-3.1-405b": (3.00, 3.00),
    "llama-3.1-70b": (0.59, 0.79),
    "llama-3.1-8b": (0.05, 0.08),
    # Mistral
    "mistral-large": (2.00, 6.00),
    "mistral-small": (0.20, 0.60),
    "mixtral-8x7b": (0.24, 0.24),
    # Cohere
    "command-r-plus": (2.50, 10.00),
    "command-r": (0.15, 0.60),
    # DeepSeek
    "deepseek-v3": (0.27, 1.10),
    "deepseek-r1": (0.55, 2.19),
}


def calculate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    """Calculate cost in USD for a given model and token counts.

    If model is unknown, returns 0.0 (caller should warn).
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    input_rate, output_rate = pricing
    cost = (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
    return round(cost, 8)


def list_models() -> list[str]:
    """Return sorted list of known model names."""
    return sorted(MODEL_PRICING.keys())
