import asyncio
from src.mcp_client import managed_session, _call_mcp
import json

async def run():
    async with managed_session() as session:
        res = await _call_mcp(session, "getEventApiProductVersions", {"eventApiProductIds": ["rf6illetnw5"]})
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(run())
