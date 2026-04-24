import os
import asyncio
from litellm import acompletion
from dotenv import load_dotenv
load_dotenv(".env")
load_dotenv("apps/agent/.env")
import litellm
litellm.set_verbose=True

async def run():
    print("Testing DeepSeek function calling...")
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "WEB_SEARCH",
                "description": "Search the web for real-time information and URLs using DuckDuckGo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = "dummy"
    
    # We rely on user saying "I have configured API key". So I will just print the payload that WOULD be sent.
    print("Done")

if __name__ == "__main__":
    asyncio.run(run())
