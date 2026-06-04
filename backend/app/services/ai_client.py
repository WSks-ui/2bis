import httpx

from app.config import AI_API_KEY, AI_API_URL, AI_TIMEOUT


class AIClient:
    @staticmethod
    async def generate(prompt: str, quality: str) -> str:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            response = await client.post(
                AI_API_URL,
                json={"prompt": prompt, "quality": quality},
                headers={"Authorization": f"Bearer {AI_API_KEY}"},
            )
            if response.status_code != 200:
                raise Exception(f"AI API error: {response.status_code} {response.text}")
            data = response.json()
            return data["image_url"]
