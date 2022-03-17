'''
Server:
    Three threads:
        1. The main thread. Runs the game loop.
        2. Receive thread (consumer). Listens for incoming messages and puts
           them into the receive buffer.
        3. Send thread (producer). Waits messages to appear to the send buffer
           and sends them to the client(s).
'''
import asyncio, websockets, json, time
from contextlib import suppress
import sys, traceback
import pygame as pg
import janus

def encode_msg(msg):
    return json.dumps(msg, ensure_ascii=False)
def decode_msg(text):
    return json.loads(text)

TICK_RATE = 32

class Client:
    def __init__(self, id, socket, player_name):
        self.id = id
        self.socket = socket
        self.player_name = player_name
        self.disconnected = False

class Game:
    def __init__(self, room_key, send_message_cb):

        # Server stuff...
        self.room_key = room_key
        self.future = None
        self.rx_queue = janus.Queue()
        self.send_message = lambda m: send_message_cb(self.room_key, m)
        self.clients = {}
        self.new_clients = []
        self.last_client_id = 0

        # Game stuff...
        pg.init()
        self.clock = pg.time.Clock()
        self.delta = 0
        self.current_tick = 0

        self.running = True

    def join(self, socket, name):
        #self.clients.append(Client(self.last_client_id, socket, name))
        self.new_clients.append(Client(self.last_client_id, socket, name))
        print(f"Client '{name}' (ID = {self.last_client_id}) joined")
        self.last_client_id += 1

        return self.new_clients[-1]

    def client_count(self):
        return len([c.id for c in self.clients.values() if not c.disconnected])

    def get_messages(self):
        return []

    def run_loop(self):
        self.check_events()
        self.update()
        self.send_update()
        self.tick()

    def check_events(self):
        messages = self.get_messages()
        if messages:
            for message in messages:
                print("Received:", message)

    def update(self):
        pass

    def send_update(self):
        #self.tx_queue.sync_q.put({'type': 'test', 'tick': self.tick})
        message = {'type': 'test', 'tick': self.current_tick}
        self.send_message(message)

    def tick(self):
        self.delta = self.clock.tick(TICK_RATE)
        self.current_tick += 1

    def stop(self):
        print("Stopping game.")
        self.running = False
        self.rx_queue.close()
        #await self.rx_queue.wait_closed()
        pg.quit()

class GameServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.async_loop = None
        self.tx_queue = None

        self.running = False
        self.rooms = {}

    def run(self):
        self.running = True
        try:
            asyncio.run( self.thread_manager() )
        except BaseException as e:
            pass

    def stop(self, e=None):
        self.running = False

        #self.game.stop()
        for room_key, room in self.rooms.items():
            room.stop()

        if e not in [None, KeyboardInterrupt]:
            print(traceback.format_exc())

    def create_room(self, room_key):
        return Game(room_key, self.send_message)

    async def destroy_room(self, room):
        await room.rx_queue.async_q.put(None)
        room.stop()
        del self.rooms[room.room_key]
        await room.future

    '''
    def get_messages(self, room_key):
        messages = []
        # read all messages from the buffer
        while not self.rx_queue.sync_q.empty():
            messages.append( self.rx_queue.sync_q.get() )
        return messages
    '''
    def send_message(self, room_key, message):
        self.tx_queue.sync_q.put((room_key, encode_msg(message)))

    async def thread_manager(self):
        self.async_loop = asyncio.get_event_loop()
        self.tx_queue = janus.Queue()

        try:
            print("Starting server...")
            async with websockets.serve(self.recv_thread, self.host, self.port) as socket:
                print(f"Started at ws://{self.host}:{self.port}.")
                send_task = asyncio.create_task( self.send_thread(socket) )

                with suppress(asyncio.CancelledError):
                    done, pending = await asyncio.wait(
                        [send_task], return_when=asyncio.FIRST_COMPLETED
                    )

        except BaseException as e:
            self.stop(e)
        
        print("Stopping server...")
        if self.running:
            self.stop()

        #self.rx_queue.close()
        #await self.rx_queue.wait_closed()
        self.tx_queue.close()
        await self.tx_queue.wait_closed()
        print("Server stopped.")

    def game_thread(self, room_key):
        room = self.rooms[room_key]
        try:
            while self.running and room.running:
                self.rooms[room_key].run_loop()

        except BaseException as e:
            if e is not KeyboardInterrupt:
                print(traceback.format_exc())

    async def recv_thread(self, socket):
        client = None
        room = None
        try:
            async for message_raw in socket:
                message = decode_msg(message_raw)
                if message['type'] == 'join':
                    room_key = message['room']

                    # TODO: check client & server version compatibility
                    # return: client_id, tick_rate
                    
                    # If such room doesn't exist, create a new one.
                    if not room_key in self.rooms:
                        room = self.create_room(room_key)
                        self.rooms[room_key] = room

                        room.future = self.async_loop.run_in_executor(None, self.game_thread, room_key)
                    else:
                        room = self.rooms[room_key]

                    client = room.join(socket, message['player_name'])

                elif room:  # room is already up...
                    #await self.room.rx_queue.async_q.put( decode_msg(message_raw) )
                    await room.rx_queue.async_q.put(message)

        except websockets.exceptions.ConnectionClosedError:
            pass

        # Client disconncted. If the room becomes empty, destroy it.
        if client:
            client.disconnected = True
            print(f"Client '{client.player_name}' disconnected from room '{room.room_key}'.")

        if room:
            if room.client_count() == 0:
                await self.destroy_room(room)
                print(f"Cleaned room '{room.room_key}'.")

    async def send_thread(self, socket):
        while self.running:
            room_key, message = await self.tx_queue.async_q.get()
            room = self.rooms[room_key]

            # Add any new clients that have shown up, this handler must control this
            # to avoid it happening inside the loop
            if len(room.new_clients) > 0:
                for client in room.new_clients:
                    room.clients[client.id] = client
                room.new_clients = []

            disconnected = []
            # who to send? put it in the queue (None = all)
            for client_id, client in room.clients.items():
                if client.disconnected:
                    disconnected.append(client.id)
                    continue

                try:
                    await client.socket.send(message)
                except websockets.ConnectionClosed:
                    print("Lost client in send")
                    client.disconnected = True

            for d in disconnected:
                # Check again since they may have reconnected in other loop
                if room.clients[d]:
                    print(f"Disconnected client '{room.clients[d].player_name}'.")
                    del room.clients[d]


if __name__ == "__main__":
    server = GameServer('localhost', 8765)
    server.run()
