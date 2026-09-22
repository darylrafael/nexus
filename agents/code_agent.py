from llm_client import llm_chat


def generate_code(task: str) -> str:
    response = llm_chat(
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
        max_tokens=2000,
        temperature=0.2,
    )
    return response.choices[0].message.content
