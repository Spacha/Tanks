import asyncio, websockets, json, time
from contextlib import suppress
import sys, traceback
import pygame as pg
import janus

def encode_msg(msg):
    return json.dumps(msg, ensure_ascii=False)
def decode_msg(text):
    return json.loads(text)

WIDTH, HEIGHT = 300, 150
FPS = 60

class Game:
    def __init__(self, room_key, player_name, rx_queue, send_message_cb):

        # Client stuff...
        self.room_key = room_key
        self.player_name = player_name
        #self.rx_queue = janus.Queue()
        self.rx_queue = rx_queue
        self.send_message = lambda m: send_message_cb(self.room_key, m)

        # Game stuff...
        pg.init()
        pg.fastevent.init()
        self.clock = pg.time.Clock()
        self.scr = pg.display.set_mode((WIDTH, HEIGHT))
        self.font = pg.font.SysFont('segoeui', 26)
        self.delta = 0
        self.current_tick = 0

        self.running = True

    def run_loop(self):
        self.check_events()
        self.update()
        self.draw()
        self.send_update()
        self.tick()

        if not self.running:
            self.cleanup()

    def check_events(self):
        for event in pg.fastevent.get():
            if event.type == pg.QUIT:
                self.stop()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    self.stop()
        # check events (quit etc...)
        # check mouse input
        # check key input
        # send all new events as an update package to the server
        # type: game_event, event: ...
        pass

    def update(self):
        pass

    def draw(self):
        self.scr.fill(( 255 , 0 , 0 ))
        pg.display.update()

    def send_update(self):
        pass

    def tick(self):
        self.delta = self.clock.tick(FPS)
        self.current_tick += 1

    def stop(self):
        self.running = False

    def cleanup(self):
        pg.quit()


class GameClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.async_loop = None
        self.tx_queue = None

        # client info
        self.player_name = None
        self.client_id = None

        self.running = False
        self.game = None

    def run(self):
        self.running = True
        try:
            asyncio.run( self.thread_manager() )
        except BaseException as e:
            print(e)

    def stop(self, e=None):
        self.running = False
        #self.game.stop()

        # Wake up the send thread to stop it
        self.tx_queue.sync_q.put(None)

        if e not in [None, KeyboardInterrupt]:
            print(traceback.format_exc())

    def join(self, room_key, player_name):
        print(f"Joining room '{room_key}' as '{player_name}'.")
        self.room_key = room_key
        self.player_name = player_name
        # create receive queue for the game
        rx_queue = janus.Queue()
        self.game_future = self.async_loop.run_in_executor(None, self.game_thread, rx_queue)
        rx_queue.close()
        print("Joined.")

    def send_message(self, room_key, message):
        self.tx_queue.sync_q.put((room_key, encode_msg(message)))

    async def thread_manager(self):
        self.async_loop = asyncio.get_event_loop()
        self.tx_queue = janus.Queue()

        try:
            print("Starting client...")
            print("Connecting to server...")
            server_uri = f"ws://{self.host}:{self.port}"
            async with websockets.connect(server_uri) as socket:
                print(f"Connected to {server_uri}.")

                send_task = asyncio.create_task( self.send_thread(socket) )
                recv_task = asyncio.create_task( self.recv_thread(socket) )

                room_key = "test-room"
                player_name = "Spacha"
                self.join(room_key, player_name)

                with suppress(asyncio.CancelledError):
                    done, pending = await asyncio.wait(
                        [send_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                    )
                self.game.stop()
                await self.game_future

        except BaseException as e:
            self.stop(e)

        print("Stopping client...")
        if self.running:
            self.stop()

        self.tx_queue.close()
        await self.tx_queue.wait_closed()
        print("Client stopped.")

    def game_thread(self, rx_queue):
        # Create game. NOTE: The game (pygame) must be initialized in
        # the game thread for the events to work! Also, the rx_queue
        # must have been initialized in the main thread for it to work.
        print("Initializing game")
        # room_key, rx_queue, send_message_cb
        self.game = Game(self.room_key, self.player_name, self.send_message, rx_queue)

        try:
            while self.running and self.game.running:
                self.game.run_loop()

        except BaseException as e:
            if e is not KeyboardInterrupt:
                print(traceback.format_exc())

        self.stop()

    async def recv_thread(self, socket):
        try:
            async for message_raw in socket:
                message = decode_msg(message_raw)
                print("Received:", message)

                if self.game:  # room is already up...
                    #await self.room.rx_queue.async_q.put( decode_msg(message_raw) )
                    await room.rx_queue.async_q.put(message)

        except websockets.exceptions.ConnectionClosedError:
            pass

        #self.destroy_game()

    async def send_thread(self, socket):
        while self.running:
            message = await self.tx_queue.async_q.get()

            # 'None' message is used to wake up the thread to stop
            # (given that self.running == False)
            if message == None:
                continue

            try:
                await socket.send(message)
            except websockets.ConnectionClosed:
                print("Lost connection in send.")


if __name__ == "__main__":
    client = GameClient('localhost', 8765)
    client.run()
