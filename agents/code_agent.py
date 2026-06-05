from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

def generate_code(task: str) -> str:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b:free",
        messages=[
            {
                "role": "system",
                "content": "You are an expert programmer. Write clean, well-commented code and always explain what it does."
            },
            {
                "role": "user",
                "content": task
            }
        ],
        max_tokens=2000
    )
    return response.choices[0].message.content
