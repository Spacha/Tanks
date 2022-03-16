#!/usr/bin/env python

import asyncio
import websockets
from random import randint
from time import sleep

def consumer(message):
    print("Consumer message:", message)

def producer():
    res = str(randint(1, 20))
    print("Producer message:", res)
    sleep(1)
    return res

async def consumer_handler(websocket):
    async for message in websocket:
        # await consumer(message)
        consumer(message)

async def producer_handler(websocket):
    while True:
        # message = await producer()
        message = producer()
        await websocket.send(message)

connected = set()
async def handler(websocket):

    # Register.
    connected.add(websocket)
    print("Connected clients:", connected)
    try:
        ## Broadcast a message to all connected clients.
        #websockets.broadcast(connected, "Hello!")
        #await asyncio.sleep(10)

        consumer_task = asyncio.create_task(consumer_handler(websocket))
        producer_task = asyncio.create_task(producer_handler(websocket))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    finally:
        # Unregister.
        connected.remove(websocket)


################################################################################

counter = 0
'''
async def server(websocket):
    global counter

    async for message in websocket:
        print("Client said:", message)
        await websocket.send("Hello client! Counter is {}.".format(counter))
        counter += 1
'''

async def main():
    print("Running server...")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever

asyncio.run(main())
