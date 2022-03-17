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

class GameEvent:
    def __init__(self):
        self.events = []

    def add(self, type, value=None):
        self.events.append((type, value))

    def empty(self):
        return len(self.events) == 0

    def count(self):
        return len(self.events)

    def as_dict(self):
        events = []
        for type, value in self.events:
            events.append({'type': type, 'value': value})
        return events

class Game:
    def __init__(self, room_key, player_name, rx_queue, send_message_cb):

        # Client stuff...
        self.room_key = room_key
        self.player_name = player_name
        self.rx_queue = rx_queue
        self.send_message = lambda m: send_message_cb(self.room_key, m)

        self.server_ticks = 0

        # Game stuff...
        pg.init()
        pg.fastevent.init()
        self.clock = pg.time.Clock()
        self.scr = pg.display.set_mode((WIDTH, HEIGHT))
        self.font = pg.font.SysFont('segoeui', 18)
        self.delta = 0
        self.current_tick = 0
        self.start_time = 0

        self.running = False

    def start(self):
        self.running = True
        self.start_time = time.monotonic()

        # this is some temp stuff
        self.last_update_time = self.start_time
        self.last_update_ticks = 0
        self.tick_text = None

    def run_loop(self):
        self.check_server_events()
        self.check_events()
        self.update()
        self.draw()
        self.tick()

        if not self.running:
            self.cleanup()

    def check_server_events(self):
        # poll messages from the socket (receive buffer)
        if not self.rx_queue.sync_q.empty():
            message = self.rx_queue.sync_q.get()
            if message['type'] == 'game_update':
                print("Game update received:", message['game_update'])

            elif message['type'] == 'tick':
                self.server_ticks += 1
                self.server_tick = message['tick']

    def check_events(self):
        # check events (quit etc...)
        # check mouse input
        # check key input
        # send all new events as an update package to the server
        # type: game_event, event: ...
        game_event = GameEvent()
        for event in pg.fastevent.get():
            if event.type == pg.QUIT:
                self.stop()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    self.stop()
                elif event.key == pg.K_LEFT:
                    game_event.add('move', 'left')
                elif event.key == pg.K_RIGHT:
                    game_event.add('move', 'right')
            elif event.type == pg.KEYUP:
                if event.key in [pg.K_LEFT, pg.K_RIGHT]:
                    game_event.add('stop')

        if not game_event.empty():
            self.send_event(game_event)

    def update(self):
        pass

    def draw(self):
        self.scr.fill((10, 10, 10))

        pg.draw.rect(self.scr, (255,255,255), pg.Rect(30, 30, 50, 50))

        #for element in self.gui_elements:
        #    element.draw()
        if time.monotonic() - self.last_update_time > 1.0:
            tick_rate = (self.server_ticks - self.last_update_ticks) / (time.monotonic() - self.last_update_time)
            self.last_update_time = time.monotonic()
            self.last_update_ticks = self.server_ticks
            self.tick_text = self.font.render(f"Tick rate: {round(tick_rate)} ticks/s", True, (255, 255, 255))
        if self.tick_text:
            self.scr.blit(self.tick_text, self.tick_text.get_rect())

        pg.display.update()

    def send_event(self, event):
        self.send_message({
            'type': 'game_event',
            'event': event.as_dict()
        })

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

    def set_connection_info(self, room_key, player_name):
        self.room_key = room_key
        self.player_name = player_name

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

    def create_game(self):
        #print(f"Joining room '{room_key}' as '{player_name}'.")
        # create receive queue for the game
        rx_queue = janus.Queue()
        self.game_future = self.async_loop.run_in_executor(None, self.game_thread, rx_queue)
        #rx_queue.close()
        #print("Joined.")

    def send_message(self, room_key, message):
        self.tx_queue.sync_q.put((room_key, message))

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

                self.create_game()
                await socket.send(encode_msg((None, {
                    'type': 'join', 'room': self.room_key, 'player_name': self.player_name
                })))

                with suppress(asyncio.CancelledError):
                    done, pending = await asyncio.wait(
                        [send_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                    )

                if self.game:
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
        self.game = Game(self.room_key, self.player_name, rx_queue, self.send_message)

        try:
            self.game.start()
            while self.running and self.game.running:
                self.game.run_loop()

        except BaseException as e:
            if e is not KeyboardInterrupt:
                print(traceback.format_exc())

        if self.running:
            self.stop()

    async def recv_thread(self, socket):
        try:
            async for message_raw in socket:
                message = decode_msg(message_raw)

                if self.game:  # room is already up...
                    await self.game.rx_queue.async_q.put(message)

        except websockets.exceptions.ConnectionClosedError:
            print("Server closed connection during receive.")
            if self.running:
                self.stop()
        except BaseException as e:
            print("Recv thread exited on exception:", e)

        self.game.rx_queue.close()

    async def send_thread(self, socket):
        while self.running:
            message = await self.tx_queue.async_q.get()

            # 'None' message is used to wake up the thread to stop
            # (given that self.running == False)
            if message == None:
                continue

            try:
                await socket.send( encode_msg(message) )
            except websockets.ConnectionClosed:
                print("Server closed connection during send.")
                if self.running:
                    self.stop()
            except BaseException as e:
                print("Send thread exited on exception:", e)


if __name__ == "__main__":
    room_key = "test-room"
    player_name = "Spacha"

    client = GameClient('localhost', 8765)
    client.set_connection_info(room_key, player_name)
    client.run()
