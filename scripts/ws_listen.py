"""Listen to live updates from the API.

Usage:
    python scripts/ws_listen.py matches/1     # one match
    python scripts/ws_listen.py leaderboard   # standings changes
"""
import asyncio
import sys

import websockets


async def main(path):
    async with websockets.connect("ws://127.0.0.1:8000/ws/" + path) as ws:
        print("Connected. Waiting for messages (Ctrl+C to stop)...", flush=True)
        async for message in ws:
            print(message, flush=True)


try:
    asyncio.run(main(sys.argv[1]))
except KeyboardInterrupt:
    pass
