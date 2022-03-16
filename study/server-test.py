#!/usr/bin/env python

import asyncio
import websockets

class Player:
    def __init__(self, player_id, health, pos):
        self.player_id  = player_id
        self.health     = health
        self.pos        = pos

class GameState:
    def __init__(self):
        self.players = [
            Player(1, 100, (10,0)),
            Player(2, 100, (90,0))
        ]

        self.current_turn = 0

    def next_player(self):
        self.current_turn += 1

        if self.current_turn >= len(self.players):
            self.current_turn = 0

class GameServer:
    def __init__(self):
        self.counter = 0
        self.game_state = GameState()

    def start(self, port):
        asyncio.run(self.server_main(port))

    async def server_main(self, port):
        async with websockets.serve(self.handle_message, "localhost", port):
            await asyncio.Future()  # run forever

    async def handle_message(self, websocket):
        async for message in websocket:
            print("Client said:", message)
            await websocket.send("Hello client! Counter is {}.".format(self.counter))
            self.counter += 1

server = GameServer()
server.start(8765)
'''
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
'''
