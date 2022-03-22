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
import sys, os, traceback
import random
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame as pg
from pygame.math import Vector2 as Vector
import janus

from random import randint

def encode_msg(msg):
    return json.dumps(msg, ensure_ascii=False)
def decode_msg(text):
    return json.loads(text)

TICK_RATE = 30

TANK_MODELS = [
    "tank1_blue",
    "tank1_red",
    "tank1_green",
    #"tank2_green",
    #"tank2_black",
]

class GameObject:
    DIR_LEFT  = -Vector(1,0)
    DIR_RIGHT = Vector(1,0)

    def __init__(self, position):
        self.position = Vector(position)
        self.velocity = Vector(0, 0)
        self.direction = self.DIR_RIGHT
        self.controllable = False
        
        # status tracking
        self.prev_position = self.position
        self.prev_direction = self.direction
        self.position_changed = True
        self.direction_changed = True
        self.position_change = Vector(0, 0)

    def initialize(self):
        pass

    def update(self, delta):
        self.position += delta * self.velocity

        # for directional game objects
        if self.position.x < self.prev_position.x:
            self.direction = self.DIR_LEFT
        elif self.position.x > self.prev_position.x:
            self.direction = self.DIR_RIGHT

    def draw(self, scr):
        pass

    def tick(self):
        self.position_changed = self.position != self.prev_position
        self.position_change = self.position - self.prev_position
        self.direction_changed = self.direction != self.prev_direction

        # update previous...
        self.prev_position = self.position.copy()
        self.prev_direction = self.direction

    def bounding_box(self):
        pass

    # Controls

    def set_as_player(self):
        self.controllable = True
    def key_down(self, keys):
        pass
    def key_up(self, keys):
        pass

    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def serialize(self):
        pass


class TankSprite:  # TODO: use pg.Sprite as a base!
    DIR_LEFT = GameObject.DIR_LEFT
    DIR_RIGHT = GameObject.DIR_RIGHT

    def __init__(self, model=None):
        self.model = model
        # BARREL: coordinates defined by the sprite image (in pixels)
        self.barrel_pos             = Vector(25, 24)    # sprite top-left position in the tank sprite
        self.barrel_pivot_pos       = Vector(2, 2)      # pivot position from top-left of the sprite
        self.barrel_pivot_offset    = Vector(11, 0)     # pivot offset from the sprite center (of rotation)

        if self.model is None:
            self.model = random.choice(TANK_MODELS)
        self._initialize()

    def _initialize(self):
        base_path = os.path.join('img', f"{self.model}_base.png")
        barrel_path = os.path.join('img', f"{self.model}_barrel.png")
        # preserve the originals for re-blit
        self.sprite_right_original = pg.image.load(base_path)
        self.barrel_sprite_original = pg.image.load(barrel_path)
        # BODY
        self.sprite_right = self.sprite_right_original.copy()
        self.sprite_left = pg.transform.flip(self.sprite_right_original, True, False)
        self.rect = self.sprite_right.get_rect()
        # BARREL
        self.barrel_sprite = self.barrel_sprite_original.copy()
        self.barrel_rect = self.barrel_sprite.get_rect()

        self.set_direction(self.DIR_RIGHT)

    def set_direction(self, direction):
        self.direction = direction
        self.update_surface()

    def update_surface(self):
        self.surface = self.sprite_left if (self.direction == self.DIR_LEFT) else self.sprite_right

    def rotate_barrel(self, new_angle):
        def rotated_barrel_sprite(angle):
            return rotate(self.barrel_sprite_original, -angle, self.barrel_pos + self.barrel_pivot_pos, self.barrel_pivot_offset)

        self.barrel_sprite, self.barrel_rect = rotated_barrel_sprite(new_angle)
        # repaint tank (both directions) with rotated barrel
        self.sprite_right = self.sprite_right_original.copy()
        self.sprite_right.blit(self.barrel_sprite, self.barrel_rect)  # with barrel already in place
        self.sprite_left = pg.transform.flip(self.sprite_right, True, False)
        self.update_surface()


class Tank(GameObject):
    def __init__(self, name, position, model=None):
        super().__init__(position)
        self.name = name
        self.barrel_angle = 0                       # how it is currently positioned
        self.barrel_angle_rate = 0                  # how fast is currently changing
        self.barrel_angle_min = -10.0
        self.barrel_angle_max = 70.0

        self.prev_barrel_angle = self.barrel_angle  # what was the previous value
        self.barrel_angle_changed = True            # was the value just changed

        self.sprite = TankSprite(model)

        # MULTIPLAYER: which client this object belongs to
        self.owner_id = None

    def initialize(self):
        super().initialize()

        # not in multiplayer...
        #font = pg.font.SysFont("couriernew", 16)  # TODO: don't re-load every time...
        #self.name_text = font.render(self.name, True, pg.Color('white'))

    def update(self, delta):
        super().update(delta)
        self.barrel_angle_change = delta * self.barrel_angle_rate
        self.barrel_angle += self.barrel_angle_change

        if self.barrel_angle < self.barrel_angle_min:
            self.barrel_angle = self.barrel_angle_min
        elif self.barrel_angle > self.barrel_angle_max:
            self.barrel_angle = self.barrel_angle_max

    def draw(self, scr):
        super().draw(scr)

        if self.barrel_angle_changed:
            self.sprite.rotate_barrel(self.barrel_angle)
        if self.direction_changed:
            self.sprite.set_direction(self.direction)

        scr.blit(self.sprite.surface, self.sprite.rect.move(self.position))
        text_center = self.position + (self.sprite.rect.w / 2, self.sprite.rect.h + 10)
        scr.blit(self.name_text, self.name_text.get_rect(center=text_center))  # TODO: should be in top layer (UI)

    def tick(self):
        super().tick()
        self.barrel_angle_changed = self.barrel_angle != self.prev_barrel_angle
        # update previous...
        self.prev_barrel_angle = self.barrel_angle

    def bounding_box(self):
        return self.sprite.surface.get_bounding_rect().move(self.position)

    def key_down(self, pressed):
        if pg.K_LEFT in pressed:
            self.velocity.x = -50
        if pg.K_RIGHT in pressed:
            self.velocity.x = 50

        if pg.K_UP in pressed:
            self.barrel_angle_rate = 30
        if pg.K_DOWN in pressed:
            self.barrel_angle_rate = -30

    def key_up(self, released):
        print("Released:", released)
        if pg.K_UP in released or pg.K_DOWN in released:
            self.barrel_angle_rate = 0
        if pg.K_LEFT in released or pg.K_RIGHT in released:
            self.velocity.x = 0

    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def get_state(self):
        return {
            # mostly static
            'class':                'Tank',
            'id':                   self.id,
            'owner_id':             self.owner_id,
            'model':                self.sprite.model,
            'name':                 self.name,
            # often changed
            'position':             tuple(self.position),
            'direction':            tuple(self.direction),
            'barrel_angle':         self.barrel_angle,
            #'velocity':             tuple(self.velocity),
            #'barrel_angle_rate':    self.barrel_angle_rate
        }
        

# ------------------------------------------------------------------------------
#
#
#
#
#
#
#
#
# ------------------------------------------------------------------------------

class ObjectContainer:
    def __init__(self):
        self._objs = {}
        self.last_id = 0

        self._pending_addition = set()
        self._pending_delete = set()

    def all(self):
        return self._objs.items()
    def as_list(self):
        return self._objs.values()
    def exists(self, obj_id):
        return obj_id in self._objs and obj_id not in self._pending_addition

    def get(self, obj_id):
        try:
            return self._objs[obj_id]
        except KeyError:
            raise Exception(f"Error: object ID '{obj_id}' not found!")

    def add(self, obj):
        # add object to queue and update ID
        obj_id = self.last_id
        self._pending_addition.add((obj_id, obj))
        self.last_id += 1
        return obj_id

    def delete(self, id):
        if type(id) is int or id.isdigit():  # numeric string is allowed
            self._pending_delete.add(id)
        elif type(id) is list:
            self._pending_delete.update(id)
        else:
            raise ValueError('Object ID must be numeric!')

    def count(self):
        # TODO: ignore pending deletes?
        return len(self._objs)

    def apply_pending_changes(self):
        self._delete_pending()
        self._add_pending()

    def _add_pending(self):
        for obj_id, obj in self._pending_addition:
            self._objs[obj_id] = obj
        self._pending_addition.clear()

    def _delete_pending(self):
        for obj_id in self._pending_delete:
            try:
                del self._objs[obj_id]
            except KeyError:
                print("Warning: trying to delete non-existing object.")
        self._pending_delete.clear()

class Client:
    def __init__(self, socket, player_name):
        self.socket = socket
        self.player_name = player_name

        self.id = None
        self.obj_id = None  # object controlled by the client
        self.disconnected = False

class Game:
    def __init__(self, room_key, send_message_cb):

        # Server stuff...
        self.room_key = room_key
        self.rx_queue = janus.Queue()
        self.send_message = lambda m, c: send_message_cb(self.room_key, m, c)
        self.future = None

        # Game stuff...
        pg.init()
        self.clock = pg.time.Clock()

        self.running = False
        self.current_tick = 0
        self.delta = 0.0

        self.clients = ObjectContainer()
        self.objects = ObjectContainer()

    def initialize(self):
        self.objects.apply_pending_changes()
        self.running = True
        for obj_id, obj in self.objects.all():
            obj.initialize()

    def get_messages(self):
        messages = []
        while not self.rx_queue.sync_q.empty():
            messages.append(self.rx_queue.sync_q.get())
        return messages

    def run_loop(self):
        self.check_events()
        self.update()
        self.send_update()
        self.tick()

    def check_events(self):
        messages = self.get_messages()
        if not messages:
            return

        for message in messages:
            print("Received:", message)
            if message['type'] == 'game_event':

                for event in message['events']:
                    client_id = message['client_id']
                    print(f"Received event from client {client_id}:", event['type'])
                    event_type = event['type']

                    client = self.clients.get(client_id)
                    player = self.objects.get(client.obj_id)

                    # type: KEYDOWN, value: key
                    if event_type == 'KEYDOWN':
                        key = event['value']
                        player.key_down([key])

                    # type: KEYUP, value: key
                    elif event_type == 'KEYUP':
                        key = event['value']
                        player.key_up([key])


    def update(self):
        # apply pending deletes and additions
        self.objects.apply_pending_changes()

        for obj_id, obj in self.objects.all():
            obj.update(self.delta)

    def send_update(self, client=None):
        #self.tx_queue.sync_q.put({'type': 'test', 'tick': self.tick})
        #message = {'type': 'tick', 'tick': self.current_tick}
        #self.send_message(message, client)

        # TODO: send incremental update here!
        self.send_absolute_update()

    def tick(self):
        self.delta = self.clock.tick(TICK_RATE) / 1000
        self.current_tick += 1

        for obj_id, obj in self.objects.all():
            obj.tick()

    def add_obj(self, obj):
        obj_id = self.objects.add(obj)
        obj.id = obj_id
        # if already running, initialize immediately
        if self.running:
            obj.initialize()

    def delete_obj(self, obj_id):
        self.objects.delete(obj_id)

    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def join(self, socket, name):
        def next_tank_model(client_id):
            return TANK_MODELS[client_id % len(TANK_MODELS)]
        # add a client and tank (object) for the new player
        client = Client(socket, name)
        client_id = self.clients.add(client)
        client.id = client_id
        # create tank for the client
        obj = Tank(name, (50, 50), next_tank_model(client_id))
        obj.owner_id = client_id    # the object belongs to the client
        self.add_obj(obj)
        client.obj_id = obj.id
        return client

    def leave(self, client_id):
        client = self.clients.get(client_id)
        client.disconnected = True
        obj_id = client.obj_id
        self.objects.delete(obj_id)
        self.clients.delete(client_id)

    def stop(self):
        print("Stopping game.")
        self.running = False
        self.rx_queue.close()
        #await self.rx_queue.wait_closed()
        pg.quit()

    def send_absolute_update(self, client=None):
        #self.tx_queue.sync_q.put({'type': 'test', 'tick': self.tick})
        message = {'type': 'game_state', 'state': self.get_game_state()}
        self.send_message(message, client)

    def get_game_state(self):
        game_state = {}
        objects = {}

        for obj_id, obj in self.objects.all():
            objects[obj_id] = obj.get_state()  # serialize object
        game_state['objects'] = objects
        '''
        for client_id, player in self.players.items():
            players[client_id] = {
                'color': player.color,
                'position': (player.x, player.y),
                'status': player.status
            }

        game_state['tick'] = self.current_tick
        game_state['players'] = players
        '''
        return game_state

    def client_count(self):
        return len([c.id for c in self.clients.as_list() if not c.disconnected])

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
        #await room.rx_queue.async_q.put(None)
        room.stop()
        del self.rooms[room.room_key]
        await room.future

    def send_message(self, room_key, message, client):
        self.tx_queue.sync_q.put((room_key, client, encode_msg(message)))

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
        room.initialize()  # initialize the game...
        print(f"Game initialized (tick rate {TICK_RATE})")
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
                    print(f"Player '{message['player_name']}' (client ID '{client.id}') joined to room '{room.room_key}'.")
                    await client.socket.send(encode_msg({'type': 'joined', 'client_id': client.id}))

                elif room:  # room is already up...
                    #await self.room.rx_queue.async_q.put( decode_msg(message_raw) )
                    message['client_id'] = client.id
                    await room.rx_queue.async_q.put(message)

        except json.decoder.JSONDecodeError as e:
            print("JSON decode error:", e)
        except websockets.exceptions.ConnectionClosedError:
            pass

        # Client disconncted. If the room becomes empty, destroy it.
        if client:
            client_name = client.player_name
            room.leave(client.id)
            print(f"Client '{client_name}' left room '{room.room_key}'.")

        if room:
            if room.client_count() == 0:
                await self.destroy_room(room)
                print(f"Cleaned room '{room.room_key}'.")

    async def send_thread(self, socket):
        while self.running:
            room_key, receiver, message = await self.tx_queue.async_q.get()

            # if the room was already destroyed
            if not room_key in self.rooms:
                continue

            room = self.rooms[room_key]

            # Add and delete any clients that have joined or left.
            room.clients.apply_pending_changes()

            disconnected = []
            # who to send? put it in the queue (None = all)
            for client_id, client in room.clients.all():
                if receiver is not None and client_id != receiver:
                    continue

                try:
                    await client.socket.send(message)
                except websockets.ConnectionClosed:
                    print("Lost client in send")
                    room.leave(client_id)


if __name__ == "__main__":
    server = GameServer('localhost', 8765)
    server.run()
