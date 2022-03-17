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

class Game:
    def __init__(self, get_messages, send_message):

        # Server stuff...
        self.get_messages = get_messages    # synchronous
        self.send_message = send_message    # synchronous
        self.clients = []
        self.last_client_id = 0

        # Game stuff...
        pg.init()
        self.clock = pg.time.Clock()
        self.delta = 0
        self.current_tick = 0

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
        print("Sent:    ", message)

    def tick(self):
        self.delta = self.clock.tick(TICK_RATE)
        self.current_tick += 1

    def stop(self):
        print("Stopping game.")

class GameServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.async_loop = None
        self.rx_queue = None
        self.tx_queue = None
        self.game = Game(self.get_messages, self.send_message)
        self.rooms = []

    def run(self):
        self.running = True
        try:
            asyncio.run( self.thread_manager() )
        except BaseException as e:
            pass

    def stop(self, e=None):
        self.running = False
        self.game.stop()
        if e not in [None, KeyboardInterrupt]:
            print(traceback.format_exc())

    def join(self, socket, name):
        self.clients.append((socket, name))
        print(f"Client {name} (ID = {self.last_client_id}) joined")
        self.last_client_id += 1
        #self.game.join(...)

    def get_messages(self):
        messages = []
        # read all messages from the buffer
        while not self.rx_queue.sync_q.empty():
            messages.append( self.rx_queue.sync_q.get() )
        return messages

    def send_message(self, message):
        self.tx_queue.sync_q.put( encode_msg(message) )

    async def thread_manager(self):
        self.async_loop = asyncio.get_event_loop()
        self.rx_queue = janus.Queue()
        self.tx_queue = janus.Queue()

        try:
            print("Starting server...")
            async with websockets.serve(self.thread_socket_recv, self.host, self.port) as socket:
                print(f"Started at ws://{self.host}:{self.port}.")
                send_task = asyncio.create_task( self.thread_socket_send(socket) )

                with suppress(asyncio.CancelledError):
                    done, pending = await asyncio.wait(
                        [send_task], return_when=asyncio.FIRST_COMPLETED
                    )
                    #await game_future
                    pass

        except BaseException as e:
            self.stop(e)
            pass
        
        print("Stopping server...")
        if self.running:
            self.stop()
        self.rx_queue.close()
        await self.rx_queue.wait_closed()
        self.tx_queue.close()
        await self.tx_queue.wait_closed()
        print("Server stopped.")

    def thread_game(self):
        try:
            while self.running:
                print("Game update.")
                self.game.run_loop()
                time.sleep(1)

        except BaseException as e:
            if e is not KeyboardInterrupt:
                print(traceback.format_exc())

    async def thread_socket_recv(self, socket):
        try:
            async for message_raw in socket:
                message = decode_msg(message_raw)
                if message['type'] == 'join':
                    #room_key = message['room']
                    # Do we need to start new game thread here for each game/room? Probably.
                    self.join(socket, message['player_name'])
                    game_future = self.async_loop.run_in_executor(None, self.thread_game)
                    with suppress(asyncio.CancelledError):
                        await game_future
                else:
                    await self.rx_queue.async_q.put( decode_msg(message_raw) )
        except websockets.exceptions.ConnectionClosedError:
            print("Client disconnected.")

    async def thread_socket_send(self, socket):
        while self.running:
            #print("Sender.")
            #await asyncio.sleep(0.5)
            message = await self.tx_queue.async_q.get()

            for client_socket, player_name in self.clients:
                try:
                    await client_socket.send(message)
                except websockets.ConnectionClosed:
                    print("Lost client in send")
                    #client.disconnected = True
                    # Hoping incoming will detect disconnected as well

            '''
            for client in room.clients.values():
                if client.disconnected:
                    disconnected.append(client.id)
                    continue
                count += 1
                
                # There's likely some asyncio technique to do this in parallel
                try:
                    await client.socket.send(message)
                    #await client.socket.send(encode_msg(qevent))

                except websockets.ConnectionClosed:
                    print("Lost client in send")
                    client.disconnected = True
                    # Hoping incoming will detect disconnected as well

                except Exception as e:
                    print("Unexpected error:", sys.exc_info(), traceback.format_exc())
            '''

if __name__ == "__main__":
    server = GameServer('localhost', 8765)
    server.run()
