import asyncio
import json
import logging
from src.agent.graph import get_agent_graph
from src.schemas import AgentChatRequest

async def run():
    logging.basicConfig(level=logging.DEBUG)
    graph = get_agent_graph()
    
    from src.config import get_settings
    settings = get_settings()
    
    # We will use a mock provider instead of real API key just to see the graph trace, 
    # OR we can inject a mock response into LLM
    pass
    

if __name__ == "__main__":
    # asyncio.run(run())
    pass
