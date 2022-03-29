'''
Server:
    Three threads:
        1. The main thread. Runs the game loop.
        2. Receive thread (consumer). Listens for incoming messages and puts
           them into the receive buffer.
        3. Send thread (producer). Waits messages to appear to the send buffer
           and sends them to the client(s).
'''
import asyncio, websockets, json, time, sys, os, traceback
from contextlib import suppress
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame as pg
from pygame.math import Vector2 as Vector
from math import pi as PI, sin, cos, degrees, radians
import janus
import random

import pymunk as pm
import pymunk.autogeometry
import pymunk.pygame_util
from pymunk.vec2d import Vec2d
from pymunk import BB

from random import randint

def encode_msg(msg):
    return json.dumps(msg, ensure_ascii=False)
def decode_msg(text):
    return json.loads(text)

MAPS = [{
    "world_size": (1200, 900),
    "terrain_file": "Study/img/map-cave.png",
    "max_players": 2,
    "start_positions": [(90, 540), (1110, 540), (550, 230)],
    "start_directions": [Vector(1, 0), -Vector(1, 0), Vector(1, 0)]
}, {
    "world_size": (1200, 900),
    "terrain_file": "Study/img/map-obstacle-course.png",
    "max_players": 1,
    "start_positions": [(90, 540)],
    "start_directions": [Vector(1, 0)]
}]
MAP = MAPS[0]

# Physics: 120 FPS, updates: 30 FPS
TICK_RATE = 120
FRAMES_PER_UPDATE = 4 # send update every 4th loop = 30 UPS
WORLD_WIDTH, WORLD_HEIGHT = (1200, 900)

if (WORLD_WIDTH, WORLD_HEIGHT) != MAP["world_size"]:
    print("Warning: Terrain size doesn't match with world size!")

PLAYER_SINK = 6
MAX_HP = 100

MAX_AP              = 100
MOVEMENT_AP_COST    = 20
SHOOT_AP_COST       = 25
RESET_AP_COST       = 25

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
            #return color[3]  # use alpha
            magenta = color == pg.Color('magenta')
            if magenta:
                return 0
            return color[3]  # use alpha or magenta
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
    if type(s.body) is Tank:
        s.body.lose()
    space.remove(s.body, s)
    return False

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

        self.paska = 'penismaailma'

        self.game = None  # this is only used in shooting (should avoid using)

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

    def get_state(self):
        return {
            'position':             tuple(self.position),
            'angle':                float(self.angle),
            'direction':            tuple(self.direction),
            #'velocity':             tuple(self.velocity),
            #'angular_velocity':     ...,
        }

    def serialize(self):
        pass

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

        # MULTIPLAYER - SERVER
        self.sprite_model = model
        self.barrel_pos = Vector(25, 24) + (2,2)
        #self.sprite = TankSprite(model)

        # MULTIPLAYER - SERVER
        self.driving_direction = 0      # being driven by user?
        self.owner_id = None            # which client this object belongs to
        self.action_points = 0.0
        self.turn_ended = True
        self.last_position = self.position
        self.fallen_over = False
        self.reset_angle = False
        self.health_points = MAX_HP
        self.has_lost = False

    def initialize(self):
        super().initialize()
        # MULTIPLAYER - SERVER.

    def update(self, delta, space):
        super().update(delta)
        self.barrel_angle_change = delta * self.barrel_angle_rate
        self.barrel_angle += self.barrel_angle_change

        if self.barrel_angle < self.barrel_angle_min:
            self.barrel_angle = self.barrel_angle_min
        elif self.barrel_angle > self.barrel_angle_max:
            self.barrel_angle = self.barrel_angle_max

        self.fallen_over = PI/2 <= self.angle <= 3/2*PI

        self.on_ground = False
        if not self.fallen_over:
            for s in space.shapes:
                if hasattr(s, "is_ground") and s.is_ground:
                    if self.shape.shapes_collide(s).points:
                        self.on_ground = True
                        break

        if self.action_points <= 0:
            self.action_points = 0.0
            self.driving_direction = 0

        if self.driving_direction != 0:
            self.direction = self.DIR_LEFT if self.driving_direction < 0 else self.DIR_RIGHT
            
            if self.on_ground:
                #self.shape.friction = 0.1
                #self.apply_impulse_at_local_point(self.driving_direction * self.rotation_vector * 1000000 * delta, (0, 14))
                self.shape.surface_velocity = -self.direction.x * self.rotation_vector * 5000 * delta
        
        if self.driving_direction == 0:
            #self.shape.friction = 10.0
            self.shape.surface_velocity = 0,0


    def draw(self, scr, hud):
        super().draw(scr, hud)
        # MULTIPLAYER - NOT IN SERVER.

    def tick(self):
        super().tick()
        self.barrel_angle_changed = self.barrel_angle != self.prev_barrel_angle
        # update previous...
        self.prev_barrel_angle = self.barrel_angle

    def key_down(self, pressed):
        
        # MULTIPLAYER - SERVER.

        if self.has_lost:
            return

        if pg.K_LEFT in pressed:
            #self.velocity.x = -50
            self.driving_direction = -1
        if pg.K_RIGHT in pressed:
            #self.velocity.x = 50
            self.driving_direction = +1

        if pg.K_UP in pressed:
            self.barrel_angle_rate = 30
        if pg.K_DOWN in pressed:
            self.barrel_angle_rate = -30

    def key_up(self, released):
        
        # MULTIPLAYER - SERVER.

        if self.has_lost:
            return

        if pg.K_TAB in released:
            if not self.turn_ended:
                self.end_turn()
        if pg.K_r in released:
            if self.fallen_over and self.action_points >= RESET_AP_COST:
                self.reset_angle = True

        if pg.K_SPACE in released:
            self.shoot()
        if pg.K_UP in released or pg.K_DOWN in released:
            self.barrel_angle_rate = 0
        if pg.K_LEFT in released or pg.K_RIGHT in released:
            #self.velocity.x = 0
            self.driving_direction = 0

    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def lose(self):
        self.action_points = 0.0
        self.health_points = 0.0
        self.has_lost = True
        self.end_turn()

    def take_damage(self, damage):
        # TODO: account for armor etc.
        self.health_points -= damage
        
        if self.health_points <= 0:
            self.health_points = 0.0
            self.lose()

    def shoot(self):
        if self.action_points >= SHOOT_AP_COST:
            self.action_points -= SHOOT_AP_COST
            barrel_dir_vect = Vec2d(self.direction.x * cos(radians(self.barrel_angle) - self.direction.x * self.angle), -sin(radians(self.barrel_angle) - self.direction.x * self.angle))
            #projectile = Projectile(self.position + 50 * barrel_dir_vect)
            projectile = Projectile(self.position + 30 * barrel_dir_vect)
            projectile.velocity = 1000 * barrel_dir_vect
            #self.apply_impulse_at_local_point(-20000 * barrel_dir_vect)

            self.game.add_obj(projectile)
            self.game.space.add(projectile, projectile.shape)

    def start_turn(self):
        self.turn_ended = False
        self.action_points = MAX_AP

    def end_turn(self):
        self.turn_ended = True
        self.action_points = 0.0

    def update_action_points(self, delta):
        if self.reset_angle:
            self.angle = 0
            self.position -= Vec2d(0, 10)
            self.action_points -= RESET_AP_COST
            self.reset_angle = False

        if self.on_ground:
            movement = (self.position - self.last_position).length
            if self.driving_direction != 0 and movement > 0.1:
                #print(player.position - player_last_position, movement)
                self.action_points -= movement * delta * MOVEMENT_AP_COST
        self.last_position = self.position

    def get_state(self):
        super_state = super().get_state()
        return {
            # mostly static
            'class':                'Tank',
            'id':                   self.id,
            'has_turn':             bool(not self.turn_ended),
            'has_lost':             bool(self.has_lost),
            'owner_id':             self.owner_id,
            'model':                self.sprite_model,
            'name':                 self.name,
            # often changed
            'health_points':        float(self.health_points),
            'action_points':        float(self.action_points),
            'barrel_angle':         self.barrel_angle
            #'barrel_angle_rate':    self.barrel_angle_rate
        } | super_state

class Projectile(GameObject):
    def __init__(self, position, model=None):
        mass = 25
        moment = pm.moment_for_circle(mass, 0, 5)
        super().__init__(mass, moment=moment)
        self.position = Vec2d(*position)
        self.shape = pm.Circle(self, 5)
        self.owner_id = None
        self.exploded = False

    def initialize(self):
        super().initialize()
        # MULTIPLAYER - SERVER.

    def update(self, delta, space):
        super().update(delta)

        if self.exploded:
            return

        # TODO: Check collisions --> explode
        self.collides = False
        for s in space.shapes:
            if self.shape.shapes_collide(s).points:
                if s is self.shape:
                    continue
                self.collides = True
                break

        if self.collides:
            self.explode(space)

    def draw(self, scr, hud):
        super().draw(scr, hud)
        # MULTIPLAYER - NOT IN SERVER.
        pg.draw.circle(scr, pg.Color('yellow'), self.position, 5)

    def explode(self, space):
        def calc_explosion_effect(dist, max_dist, max_effect):
            return max_effect / max_dist * (max_dist + 1 - dist)
        # TODO: Not always need to update the map (explosion over ground etc)!
        self.game.erase_map_circle(self.position, 30)
        for s in space.shapes:
            if type(s.body) is Tank:
                # this is very naive (assumes point-like shapes)
                dist = self.position.get_distance(s.body.position)
                # dist = 75 -> explosion_effect = 1
                # dist = 0  -> explosion_effect = 100
                if dist <= 120:
                    explosion_effect = calc_explosion_effect(dist, 120, 100)
                    impulse_direction = (s.body.position - self.position).normalized()
                    s.body.apply_impulse_at_local_point(20000 * explosion_effect * impulse_direction)
                    s.body.take_damage(explosion_effect / 3)  # direct hit is about 30 % of HP

        self.game.delete_obj(self.id)
        self.exploded = True
        # TODO: check players and damage them

    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def get_state(self):
        super_state = super().get_state()
        return {
            # mostly static
            'class':                'Projectile',
            'id':                   self.id,
            'owner_id':             self.owner_id,
            #'model':                'CIRCLE-5'
            'exploded':             self.exploded
        } | super_state
        

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

    def count(self, include_pending=False):
        # TODO: ignore pending deletes?
        pending = len(self._pending_addition) if include_pending else 0
        return len(self._objs) + pending

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
        self.full = False
        self.current_player = None

        # Game stuff...
        self.init_game()

        self.running = False
        self.current_tick = 0
        self.delta = 0.0

        self.clients = ObjectContainer()
        self.objects = ObjectContainer()

        self.TEST_map_updates = []

    def init_game(self):
        #--------------------------------------
        # Init Pygame
        #--------------------------------------
        pg.init()
        self.clock = pg.time.Clock()

        #--------------------------------------
        # Init Pymunk
        #--------------------------------------
        self.space = pm.Space()
        self.space.gravity = 0, 980

    def init_world(self):
        # static walls of the world
        static = [
            pm.Segment(self.space.static_body, (-50, -50), (-50, WORLD_HEIGHT + 50), 5),
            pm.Segment(self.space.static_body, (-50, WORLD_HEIGHT + 50), (WORLD_WIDTH + 50, WORLD_HEIGHT + 50), 5),
            pm.Segment(self.space.static_body, (WORLD_WIDTH + 50, WORLD_HEIGHT + 50), (WORLD_WIDTH + 50, -50), 5),
            pm.Segment(self.space.static_body, (-50, -50), (WORLD_WIDTH + 50, -50), 5),
        ]
        for s in static:
            s.collision_type = 1
        self.space.add(*static)

        self.space.add_collision_handler(0, 1).pre_solve = pre_solve_static

        self.terrain_surface = pg.Surface((WORLD_WIDTH, WORLD_HEIGHT), flags=pg.SRCALPHA)

        map_sprite = pg.image.load(MAP["terrain_file"])
        map_rect = map_sprite.get_rect(bottomleft=(0, WORLD_HEIGHT))
        self.terrain_surface.blit(map_sprite, map_rect)
        generate_geometry(self.terrain_surface, self.space)

    def initialize(self):
        self.init_world()
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
        # apply pending deletes and additions
        self.objects.apply_pending_changes()

        self.check_events()
        self.update()
        if self.current_tick % FRAMES_PER_UPDATE == 0:  # time to send an update
            self.send_update()
        self.tick()

    def check_events(self):
        messages = self.get_messages()

        for message in messages:
            if message['type'] == 'game_event':
                for event in message['events']:
                    client_id = message['client_id']
                    event_type = event['type']

                    # check if there are old messages in queue from players that have left...
                    if self.clients.exists(client_id):
                        client = self.clients.get(client_id)
                    if self.objects.exists(client.obj_id):
                        player = self.objects.get(client.obj_id)

                    # type: KEYDOWN, value: key
                    if event_type == 'KEYDOWN':
                        key = event['value']
                        player.key_down([key])

                    # type: KEYUP, value: key
                    elif event_type == 'KEYUP':
                        key = event['value']
                        player.key_up([key])

        if self.clients.count() > 0:
            if self.current_player is None or (self.objects.exists(self.current_player.obj_id) and self.objects.get(self.current_player.obj_id).turn_ended):
                self.next_turn()

    def next_turn(self, client_id=None):
        if client_id is None:
            # find next client in the list (wraps back to the previous current if alone)
            client_id = self.current_player.id + 1
            client = None
            c = 0
            while client is None and c < 10:
                try:
                    client = self.clients.get(client_id)
                    if client is not None:
                        obj = self.objects.get(client.obj_id)
                        if obj.has_lost:  # cannot give turn to player who has lost
                            raise
                except:
                    client = None
                    client_id = (client_id + 1)
                    if client_id > self.clients.last_id:
                        client_id = 0
                c += 1
                
        else:
            # get certain client
            client = self.clients.get(client_id)
        
        if client is None:  # no active players...
            return

        self.current_player = client
        self.objects.get(self.current_player.obj_id).start_turn()

    def update(self):
        for obj_id, obj in self.objects.all():
            obj.update(self.delta, self.space)

        self.space.step(1.0 / TICK_RATE)

        if self.objects.exists(self.current_player.obj_id):
            self.objects.get(self.current_player.obj_id).update_action_points(self.delta)

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
        obj.game = self
        # if already running, initialize immediately
        if self.running:
            obj.initialize()

    def delete_obj(self, obj_id):
        self.objects.delete(obj_id)

    def erase_map_circle(self, pos, radius):
        """
        Erases a circular piece of the map and updates the collision map.
        """
        pg.draw.circle(self.terrain_surface, pg.Color('magenta'), pos, radius)
        generate_geometry(self.terrain_surface, self.space)
        self.TEST_map_updates.append(('CIRCLE', (pos, radius)))


    #----------------------------------
    #   MULTIPLAYER-SPECIFIC
    #----------------------------------

    def join(self, socket, name):
        # TODO: Handle disconnected and rejoined (missed client id)
        # TODO: Respond negatively if cannot join (full lobby or so)
        def next_tank_model(client_id):
            return TANK_MODELS[client_id % len(TANK_MODELS)]
        # add a client and tank (object) for the new player
        client = Client(socket, name)
        client_id = self.clients.add(client)
        client.id = client_id
        # create tank for the client
        obj = Tank(name, MAP["start_positions"][client_id], next_tank_model(client_id))
        obj.direction = MAP["start_directions"][client_id]
        obj.owner_id = client_id    # the object belongs to the client
        self.add_obj(obj)
        self.space.add(obj, obj.shape)
        client.obj_id = obj.id

        if self.clients.count(include_pending=True) >= MAP["max_players"]:
            self.full = True
        if self.clients.count(include_pending=True) == 1:
            self.current_player = client

        return client

    def leave(self, client_id):
        try:
            if self.current_player.id == client_id:
                self.next_turn()  # give turn to next player if current leaves
            client = self.clients.get(client_id)
        except:
            return
        client.disconnected = True
        obj_id = client.obj_id
        self.objects.delete(obj_id)
        self.clients.delete(client_id)

    def stop(self):
        print("Stopping game.")
        self.running = False
        self.rx_queue.close()
        #await self.rx_queue.wait_closed()
        #pg.quit()

    def send_absolute_update(self, client=None):
        #self.tx_queue.sync_q.put({'type': 'test', 'tick': self.tick})
        message = {'type': 'game_state', 'state': self.get_game_state()}
        self.send_message(message, client)

    def get_game_state(self):
        game_state = {}
        game_state['current_player'] = self.current_player.id

        if self.TEST_map_updates:
            game_state['map_update'] = self.TEST_map_updates
            self.TEST_map_updates = []

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

                    # check if room is full
                    if room.full:
                        print(f"Player '{message['player_name']}' could not join room '{room.room_key}' (full).")
                        await socket.send(encode_msg({'type': 'join-rejected', 'reason': 'Room is full'}))
                    else:
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
                    #room.leave(client_id)


if __name__ == "__main__":
    #server = GameServer('localhost', 8765)
    server = GameServer('192.168.1.154', 8765)
    server.run()
