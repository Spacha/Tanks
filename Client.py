import asyncio, websockets, json, time, sys, os, traceback
from contextlib import suppress
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame as pg
from pygame.math import Vector2 as Vector
import janus
import random

from math import degrees, radians

import pymunk as pm
import pymunk.autogeometry
import pymunk.pygame_util
from pymunk.vec2d import Vec2d
from pymunk import BB

def encode_msg(msg):
    return json.dumps(msg, ensure_ascii=False)
def decode_msg(text):
    return json.loads(text)

#TICK_RATE = 1  # must match with the server
WORLD_WIDTH, WORLD_HEIGHT = (1200, 900)
WIDTH, HEIGHT = (1200, 900)
FPS = 60

PLAYER_SINK = 6

TOTAL_AP            = 100
MOVEMENT_AP_COST    = 20
SHOOT_AP_COST       = 25

TANK_MODELS = [
    "tank1_blue",
    "tank1_red",
    "tank1_green",
    #"tank2_green",
    #"tank2_black",
]

def generate_geometry(surface, space):
    """
    Used by the game engine to generate a terrain based on an image (surface).
    """
    for s in space.shapes:
        if hasattr(s, "generated") and s.generated:
            space.remove(s)

    def sample_func(point):
        try:
            p = int(point[0]), int(point[1])
            color = surface.get_at(p)
            #return color.hsla[2]  # use lightness
            return color[3]  # use alpha
        except Exception as e:
            print(e)
            return 0

    line_set = pm.autogeometry.march_soft(
        BB(0, 0, WORLD_WIDTH - 1, WORLD_HEIGHT - 1), 180, 180, 90, sample_func
    )

    for polyline in line_set:
        line = pm.autogeometry.simplify_curves(polyline, 1.0)

        for i in range(len(line) - 1):
            p1 = line[i]
            p2 = line[i + 1]
            shape = pm.Segment(space.static_body, p1, p2, 1)
            shape.collision_type = 2
            shape.friction = 0.5
            shape.color = pg.Color("red")
            shape.generated = True
            shape.is_ground = True
            space.add(shape)

def pre_solve_static(arb, space, data):
    s = arb.shapes[0]
    space.remove(s.body, s)
    print("Body removed.")
    return False

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


def rotate(surface, angle, pivot, offset):
    """Rotate the surface around the pivot point.
    Args:
        surface (pygame.Surface): The surface that is to be rotated.
        angle (float): Rotate by this angle.
        pivot (tuple, list, pygame.math.Vector2): The pivot point.
        offset (pygame.math.Vector2): This vector is added to the pivot.
    """
    #rotated_image = pg.transform.rotate(surface, -angle)  # Rotate the image.
    rotated_image = pg.transform.rotozoom(surface, -angle, 1)  # Rotate the image.
    rotated_offset = offset.rotate(angle)  # Rotate the offset vector.
    # Add the offset vector to the center/pivot point to shift the rect.
    rect = rotated_image.get_rect(center=pivot+rotated_offset)
    return rotated_image, rect  # Return the rotated image and shifted rect.

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

    def replace(self, obj_id, obj):
        # add object to queue and update ID
        self._pending_addition.add((obj_id, obj))

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

"""
    Lifecycle:
        Initialize:
            Run as soon as the game is initialized. Screen and other resources are available.
        Update:
            Update physics etc.
        Draw:
            Draw 
"""
class Game:
    #Game(self.room_key, self.player_name, rx_queue, self.send_message)
    def __init__(self, room_key, player_name, rx_queue, send_message_cb):

        # Client stuff...
        self.room_key = room_key
        self.player_name = player_name
        self.client_id = None
        self.rx_queue = rx_queue
        self.send_message = lambda m: send_message_cb(m)
        self.joined = False
        self.server_tick = 0

        self.scr_size = Vector(WIDTH, HEIGHT)
        self.fps = FPS

        # World
        self.world_scale = 1
        self.world_size = self.scr_size * self.world_scale

        # Init pygame
        pg.init()
        self.clock = pg.time.Clock()

        # display-related...
        self.scr = pg.display.set_mode(self.scr_size)
        self.main_layer = pg.Surface(self.world_scale * self.scr_size)                          # the main (world) layer (scaled)
        #self.world_hud_layer = pg.Surface(self.world_scale * self.scr_size, flags=pg.SRCALPHA)  # scaled HUD layer
        self.hud_layer = pg.Surface(self.scr_size, flags=pg.SRCALPHA)                           # unscaled HUD layer
        self.screen_rect = self.main_layer.get_rect()
        
        self.WINDOW_CAPTION = "Tanks!"
        pg.display.set_caption(self.WINDOW_CAPTION)
        self.scr_update_rects = [self.scr.get_rect()]

        # Main HUD font(s)
        self.hud_font = pg.font.SysFont("segoeui", 18)
        self.hud_font_big = pg.font.SysFont("segoeui", 28)

        self.running = False
        self.mpos = None
        self.delta = 0.0

        self.objects = ObjectContainer()        # replicated server objects
        self.local_objects = ObjectContainer()  # local, non-public objects


    def initialize(self):
        self.terrain_surface = pg.Surface((WORLD_WIDTH, WORLD_HEIGHT), flags=pg.SRCALPHA)

        self.map_sprite = pg.image.load("Study/img/map-cave.png")
        map_rect = self.map_sprite.get_rect(bottomleft=(0, WORLD_HEIGHT))
        self.terrain_surface.blit(self.map_sprite, map_rect)

        self.objects.apply_pending_changes()
        for obj_id, obj in self.objects.all():
            obj.initialize()

        # render static HUD elements
        self.room_name_text = self.hud_font.render(f"Room: {self.room_key}", True, pg.Color('white'))
        self.room_name_text_rect = self.room_name_text.get_rect().move(5,0)

        self.wait_for_join()
        self.running = True

    def run_loop(self):
        # apply pending deletes and additions
        self.objects.apply_pending_changes()

        self.check_events()
        self.update()  # for prediction, animations etc.
        self.send_update()
        self.draw()
        self.tick()

    def check_events(self):
        # MULTIPLAYER-SPECIFIC
        self.check_server_events()
        self.update_event = GameEvent()  # will contain updates to be sent to the server

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            # UPDATE: keys = pg.key.get_pressed()
            # if keys[pg.K_q]...
            elif event.type == pg.KEYDOWN:
                keys = pg.key.get_pressed()
                # emergency exit
                if keys[pg.K_q]:
                    self.running = False

                self.update_event.add('KEYDOWN', event.key)

            elif event.type == pg.KEYUP:
                keys = pg.key.get_pressed()

                self.update_event.add('KEYUP', event.key)

            elif event.type == pg.MOUSEMOTION:
                self.mpos = Vector(event.pos)
                self.mpos_world = self.mpos * self.world_scale
                #self.tank.position = self.mpos_world

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # add a random player to the mouse position
                    #self.add_obj(Tank(f"Dummy {self.objects.last_id + 2}", self.mpos_world))
                    pass
                if event.button == 3:
                    # delete non-controllable player if mouse hits it (them)
                    #for obj_id, obj in self.objects.all():
                    #    if obj.bounding_box().collidepoint(self.mpos_world) and not obj.controllable:
                    #        self.delete_obj(obj_id)
                    pass

    def update(self):
        for obj_id, obj in self.objects.all():
            obj.update(self.delta)

    def send_update(self):
        if self.update_event.empty():
            return

        self.send_event(self.update_event)

    def draw(self):
        self.main_layer.fill((112, 197, 255))
        #self.world_hud_layer.fill(0)
        self.hud_layer.fill(0)

        # TODO: pass update-rect and convert to screen coordinates!
        for obj_id, obj in self.objects.all():
            obj.draw(self.main_layer, self.hud_layer)

        # terrain
        self.main_layer.blit(self.terrain_surface, (0, 0))

        self.draw_hud(self.hud_layer)

        self.scr.blit(pg.transform.smoothscale(self.main_layer, self.scr_size), self.screen_rect)       # draw world
        #self.scr.blit(pg.transform.smoothscale(self.world_hud_layer, self.scr_size), self.screen_rect)  # draw world HUD
        self.scr.blit(self.hud_layer, self.screen_rect)                                                 # draw HUD

        pg.display.update(self.scr_update_rects)

        #self.scr_update_rects = []  # empty update list?

    def draw_hud(self, scr):
        scr.blit(self.room_name_text, self.room_name_text_rect)
        #update_rects.append(self.room_name_text_rect)

    def tick(self):
        self.delta = self.clock.tick(self.fps) / 1000
        pg.display.set_caption(f"{self.WINDOW_CAPTION} - FPS: {round(self.clock.get_fps(), 2)}")

        for obj_id, obj in self.objects.all():
            obj.tick()

    def add_obj(self, obj):
        obj_id = self.objects.add(obj)
        obj.id = obj_id
        # if already running, initialize immediately
        if self.running:
            obj.initialize()

    def add_obj_with_id(self, obj_id, obj):
        self.objects.replace(obj_id, obj)
        # if already running, initialize immediately
        if self.running:
            obj.initialize()

    def delete_obj(self, obj_id):
        self.objects.delete(obj_id)

    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def wait_for_join(self):
        while not self.joined:
            time.sleep(0.25)

        if self.client_id is not None:
            print(f"Joined. Client ID: {self.client_id}")

    def join(self, client_id):
        self.client_id = client_id  # get current player's client id
        self.joined = True

    def get_messages(self):
        messages = []
        while not self.rx_queue.sync_q.empty():
            messages.append(self.rx_queue.sync_q.get())
        return messages

    def check_server_events(self):
        messages = self.get_messages()
        if not messages:
            return

        for message in messages:
            #print("Received:", message)
            if message['type'] == 'game_state':
                state = message['state']

                # Object state update
                if 'objects' in state:
                    # first, delete objects that were not in the update (left, probably)...
                    for obj_id, obj in self.objects.all():
                        if obj_id not in state['objects']:
                            self.objects.delete(obj_id)

                    # ...then update existing and add new ones
                    for obj_id, obj_state in state['objects'].items():
                        if not self.objects.exists(obj_id):
                            # create new object of type
                            obj = None
                            if obj_state['class'] == 'Tank':
                                obj = Tank(obj_state['name'], obj_state['position'], obj_state['model'])
                                obj.owner_id = obj_state['owner_id']
                                obj.owned_by_player = obj_state['owner_id'] == self.client_id
                                obj.update_state(obj_state)
                            else:
                                raise Exception("Unknown class received!")

                            self.add_obj_with_id(obj_id, obj)
                        else:
                            # update existing object
                            obj = self.objects.get(obj_id)
                            obj.update_state(obj_state)



    def send_event(self, event):
        self.send_message({
            'type': 'game_event',
            'events': event.as_dict()})

    def stop(self):
        self.running = False

    def cleanup(self):
        pg.quit()


class GameObject(pm.Body):
    DIR_LEFT  = -Vector(1,0)
    DIR_RIGHT = Vector(1,0)

    def __init__(self, mass=1, size=(1,1), moment=None):
        if moment is None:
            moment = pm.moment_for_box(mass, size)
        super().__init__(mass, moment)

        self.direction = self.DIR_RIGHT
        self.prev_direction = self.direction
        self.direction_changed = True

    def initialize(self):
        pass

    def update(self, delta):
        pass

    def draw(self, scr, hud=None):
        pass

    def tick(self):
        self.direction_changed = self.direction != self.prev_direction
        self.prev_direction = self.direction

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

    def update_state(self, state):
        # static: class, id, model, name
        self.position       = Vec2d(*state['position'])
        self.angle          = float(state['angle'])
        self.direction      = Vector(state['direction'])
        self.barrel_angle   = float(state['barrel_angle'])
        #print(f"Updated object's ({self.name}) state.")


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
        base_path = os.path.join('Study', 'img', f"{self.model}_base.png")
        barrel_path = os.path.join('Study', 'img', f"{self.model}_barrel.png")
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
        mass = 2000
        size = (54, 28 - PLAYER_SINK)
        w, h = size
        super().__init__(mass, size)

        self.name = name
        self.barrel_angle = 0                           # how it is currently positioned
        self.barrel_angle_rate = 0                      # how fast is currently changing
        self.barrel_angle_min = -10.0
        self.barrel_angle_max = 70.0

        self.prev_barrel_angle = self.barrel_angle      # what was the previous value
        self.barrel_angle_changed = True                # was the value just changed

        self.position = Vec2d(*position)
        self.center_of_gravity = Vec2d(0, size[1] / 2)  # very low center of mass

        # create a rectangular polygon ('box')
        poly_points = [
            (-w / 2, -h / 2), ( w / 2, -h / 2), ( w / 2,  h / 2), (-w / 2,  h / 2)
        ]
        self.shape = pm.Poly(self, poly_points)
        self.shape.friction = 10.0

        self.sprite = TankSprite(model)

        self.owned_by_player = False                    # MULTIPLAYER: whether this belongs to the current player
        self.owner_id = None                            # MULTIPLAYER: which client this object belongs to

    def initialize(self):
        super().initialize()

        color = pg.Color('blue') if self.owned_by_player else pg.Color('red')
        font = pg.font.SysFont("segoeui", 14, bold=self.owned_by_player)  # TODO: don't re-load every time...
        self.name_text = font.render(f" {self.name} ", True, color, pg.Color('white'))

    def update(self, delta):
        super().update(delta)

        self.barrel_angle_change = delta * self.barrel_angle_rate
        self.barrel_angle += self.barrel_angle_change

        if self.barrel_angle < self.barrel_angle_min:
            self.barrel_angle = self.barrel_angle_min
        elif self.barrel_angle > self.barrel_angle_max:
            self.barrel_angle = self.barrel_angle_max

    def draw(self, scr, hud):
        super().draw(scr, hud)

        if self.barrel_angle_changed:
            self.sprite.rotate_barrel(self.barrel_angle)
        if self.direction_changed:
            self.sprite.set_direction(self.direction)

        rotated_sprite, sprite_rect = rotate(self.sprite.surface, degrees(self.angle), (0, 0), Vector(0, PLAYER_SINK - 14))
        text_center = self.position + (0, self.sprite.rect.h / 2 + 10)
        #sprite_rect = self.sprite.rect.move(self.position)
        name_text_rect = self.name_text.get_rect(center=text_center)

        scr.blit(rotated_sprite, sprite_rect.move(self.position))
        #scr.blit(self.sprite.surface, sprite_rect)
        hud.blit(self.name_text, name_text_rect)

        #update_rects += [self.sprite.rect.move(self.prev_position), sprite_rect, name_text_rect]

    def tick(self):
        super().tick()
        self.barrel_angle_changed = self.barrel_angle != self.prev_barrel_angle
        # update previous...
        self.prev_barrel_angle = self.barrel_angle

    def key_down(self, keys):
        # MULTIPLAYER - CLIENT.
        pass

    def key_up(self, keys):
        # MULTIPLAYER - CLIENT.
        pass


class GameClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.async_loop = None
        self.tx_queue = None

        # client info
        self.player_name = None
        self.client_id = None
        
        self.game = None
        self.running = False
        self.recv_ready = False

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

        # Wake up the send thread to stop it
        self.tx_queue.sync_q.put(None)

        if e not in [None, KeyboardInterrupt]:
            print(traceback.format_exc())

    def create_game(self):
        # create receive queue for the game
        rx_queue = janus.Queue()
        self.game_future = self.async_loop.run_in_executor(None, self.game_thread, rx_queue)

    def send_message(self, message):
        self.tx_queue.sync_q.put((message))

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
                '''
                await socket.send(encode_msg((None, {
                    'type': 'join', 'room': self.room_key, 'player_name': self.player_name
                })))
                '''

                with suppress(asyncio.CancelledError):
                    done, pending = await asyncio.wait(
                        [send_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                    )

                if self.game:
                    self.game.stop()
                await self.game_future

        except ConnectionRefusedError:
            print("> Could not reach server. Is it up?")
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

        # wait for the reveive thread to start
        while not self.recv_ready:
            pass

        # join request will be sent as soon as the threads are ready
        self.send_message({'type': 'join', 'room': self.room_key, 'player_name': self.player_name})
        self.game.initialize()
        try:
            while self.running and self.game.running:
                self.game.run_loop()

        except BaseException as e:
            if e is not KeyboardInterrupt:
                print(traceback.format_exc())

        if self.running:
            self.stop()

    async def recv_thread(self, socket):
        try:
            self.recv_ready = True
            async for message_raw in socket:
                message = decode_msg(message_raw)

                if self.game:  # room is already up...
                    if self.game.joined:  # client is ready to receive
                        await self.game.rx_queue.async_q.put(message)
                    else:  # wait for join
                        if message['type'] == 'joined':
                            self.game.join(message['client_id'])


        except websockets.exceptions.ConnectionClosedError:
            print("Server closed connection during receive.")
            if self.running:
                self.stop()
        except BaseException as e:
            if e is not KeyboardInterrupt:
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
            except websockets.exceptions.ConnectionClosed:
                print("Server closed connection during send.")
                if self.running:
                    self.stop()
            except BaseException as e:
                print("Send thread exited on exception:", e)


if __name__ == "__main__":
    print("-----------------")
    print("Welcome to Tanks!")
    print("-----------------")
    room_key = input("Room: ")
    player_name = input("Nickname: ")

    if len(room_key) == 0 or len(room_key) == 0:
        print("Invalid nickname or room!")
    else:
        #room_key = "test-room"
        #player_name = "Spacha"

        client = GameClient('localhost', 8765)
        client.set_connection_info(room_key, player_name)
        client.run()

'''
if __name__ == '__main__':
    game = Game((640, 320), 200)
    player_tank = Tank("Me", (50,50))
    player_tank.set_as_player()
    game.add_obj(player_tank)

    game.run()
'''
