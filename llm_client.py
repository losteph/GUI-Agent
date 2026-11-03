from openai import OpenAI
from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
    validate_config
)

validate_config()

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    timeout=LLM_TIMEOUT,
    max_retries=LLM_MAX_RETRIES
)


def ask_llm(
    model: str,
    messages: list,
    temperature: float = 0.1,
    max_tokens: int = 1000
):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )

    choice = response.choices[0]
    message = choice.message

    result = {
        "content": message.content,
        "model": response.model,
        "finish_reason": choice.finish_reason,
        "refusal": getattr(message, "refusal", None),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        } if response.usage else None
    }

    return result
