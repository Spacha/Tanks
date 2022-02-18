#!/usr/bin/env python

import asyncio
import websockets

counter = 0

async def echo(websocket):
    global counter

    async for message in websocket:
        print("Client said:", message)
        await websocket.send("Hello client! Counter is {}.".format(counter))
        counter += 1

async def main():
    async with websockets.serve(echo, "localhost", 8765):
        await asyncio.Future()  # run forever

asyncio.run(main())