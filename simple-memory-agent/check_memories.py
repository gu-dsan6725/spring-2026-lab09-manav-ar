from dotenv import load_dotenv
from memory_manager import MemoryManager
import asyncio, os

load_dotenv()
mm = MemoryManager(api_key=os.getenv("MEM0_API_KEY"))

async def check():
    results = await mm.search(user_id="alice", query="Alice software engineer", limit=5, agent_id="memory-agent", run_id="alice-session-2")
    print("Search results:", results)
    
    all_mem = await mm.get_all(user_id="alice")
    print("All memories:", all_mem)

asyncio.run(check())
