import requests

from prompt_optimizer_app.config import AppConfig


SYSTEM_PROMPT = """You rewrite rough user text into a strong, structured AI prompt.

Return only the improved prompt in Markdown. Do not wrap it in code fences.

Keep the user's intent, constraints, and important details. Make ambiguous parts explicit as assumptions or placeholders. Prefer clear sections, concise bullets, and direct instructions.
"""


class DeepSeekClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def optimize_prompt(self, text: str) -> str:
        if not self.config.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is missing. Add it to your .env file.")

        response = requests.post(
            f"{self.config.deepseek_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.deepseek_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.2,
            },
            timeout=self.config.deepseek_timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        try:
            optimized = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected DeepSeek response shape: {data}") from exc

        if not optimized:
            raise RuntimeError("DeepSeek returned an empty prompt.")

        return optimized

