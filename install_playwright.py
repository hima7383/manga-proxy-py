import os
from playwright import async_playwright

async def install_browsers():
    async with async_playwright() as p:
        await p.chromium.download()

if __name__ == "__main__":
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    import asyncio
    asyncio.get_event_loop().run_until_complete(install_browsers())