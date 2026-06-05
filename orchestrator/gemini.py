import json
import time  # <--- TAMBAHAN: Import time
from agents.code_agent import generate_code as _generate_code
from agents.web_agent import search_web as _search_web
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from memory.session import log_session  # <--- TAMBAHAN: Import log_session
from openai import OpenAI

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for research questions, recent news, or factual information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": "Generate, explain, or debug code for any programming task.",
            "parameters": {
                "type": "object",
                "properties": {"task": {"type": "string"}},
                "required": ["task"],
            },
        },
    },
]


def run(query: str, context: str = "") -> str:
    start = time.time()  # <--- TAMBAHAN: Mulai hitung waktu di awal fungsi

    system = """You are Nexus, a multi-agent AI pipeline orchestrator.
IMPORTANT: You MUST always call a tool. Never answer from memory.
- For any research, news, or factual question -> call search_web
- For any coding task -> call generate_code"""

    if context:
        system += f"\n\nContext from past sessions:\n{context}"

    messages = [{"role": "system", "content": system}, {"role": "user", "content": query}]

    response = client.chat.completions.create(
        model=OPENROUTER_MODEL, messages=messages, tools=TOOLS, tool_choice="auto"
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        print(f"  -> Routing to: {fn_name}")

        if fn_name == "search_web":
            result = _search_web(fn_args["query"])
        elif fn_name == "generate_code":
            result = _generate_code(fn_args["task"])
        else:
            result = "Unknown tool."

        messages.append(msg)
        messages.append({"role": "tool", "content": result, "tool_call_id": tool_call.id})

        response = client.chat.completions.create(model=OPENROUTER_MODEL, messages=messages)

    # <--- MODIFIKASI: Simpan output ke variabel dulu sebelum di-log
    final_result = response.choices[0].message.content

    # <--- TAMBAHAN: Kirim log data ke memory session
    log_session(
        query=query,  # Menggunakan query dinamis yang dimasukkan user
        agent="gemini_agent",
        model=OPENROUTER_MODEL,  # Menggunakan model dinamis dari config
        result=final_result,
        duration_ms=int((time.time() - start) * 1000),
    )

    return final_result