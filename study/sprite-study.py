import time, os
import pygame as pg
from pygame.math import Vector2 as Vector
import random

def rotate(surface, angle, pivot, offset):
    """Rotate the surface around the pivot point.
    Args:
        surface (pygame.Surface): The surface that is to be rotated.
        angle (float): Rotate by this angle.
        pivot (tuple, list, pygame.math.Vector2): The pivot point.
        offset (pygame.math.Vector2): This vector is added to the pivot.
    """
    rotated_image = pg.transform.rotate(surface, -angle)  # Rotate the image.
    rotated_offset = offset.rotate(angle)  # Rotate the offset vector.
    # Add the offset vector to the center/pivot point to shift the rect.
    rect = rotated_image.get_rect(center=pivot+rotated_offset)
    return rotated_image, rect  # Return the rotated image and shifted rect.

WIDTH, HEIGHT = (960, 540)
FPS = 60

TANK_MODELS = [
    "tank1_blue",
    "tank1_red",
    "tank1_green",
    #"tank2_green",
    #"tank2_black",
]

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
    def __init__(self, scr_size, fps):
        self.scr_size = Vector(scr_size)
        self.fps = fps

        # World
        self.world_scale = 1.5
        self.world_size = self.scr_size * self.world_scale

        # Init pygame
        pg.init()
        self.clock = pg.time.Clock()
        # display-related...
        self.scr = pg.display.set_mode(self.scr_size)
        self.main_layer = pg.Surface(self.world_scale * self.scr_size)
        self.hud_layer = pg.Surface(self.scr_size, flags=pg.SRCALPHA)
        self.screen_rect = self.main_layer.get_rect()
        
        self.WINDOW_CAPTION = "Tanks!"
        pg.display.set_caption(self.WINDOW_CAPTION)
        self.scr_update_rects = [self.scr.get_rect()]

        # Main HUD font
        self.hud_font = pg.font.SysFont("segoeui", 18)

        self.running = False
        self.mpos = None
        self.delta = 0.0

        self.objects = ObjectContainer()

    def initialize(self):
        self.objects.apply_pending_changes()
        for obj_id, obj in self.objects.all():
            print("initializing")
            obj.initialize()

        # render static HUD elements
        self.room_name_text = self.hud_font.render(f"Room: [local]", True, pg.Color('white'))
        self.room_name_text_rect = self.room_name_text.get_rect().move(5,0)

        self.running = True

    def run(self):
        self.initialize()
        while self.running:
            # apply pending deletes and additions
            self.objects.apply_pending_changes()

            self.check_events()
            self.update()
            self.draw()
            self.tick()

    def check_events(self):
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

                # relay keyboard events to all controllable game objects
                for obj_id, obj in self.objects.all():
                    if obj.controllable:
                        obj.key_down(keys)

            elif event.type == pg.KEYUP:
                keys = pg.key.get_pressed()
                # relay keyboard events to all controllable game objects
                for obj_id, obj in self.objects.all():
                    if obj.controllable:
                        obj.key_up(keys)

            elif event.type == pg.MOUSEMOTION:
                self.mpos = Vector(event.pos)
                self.mpos_world = self.mpos * self.world_scale
                #self.tank.position = self.mpos_world

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # add a random player to the mouse position
                    self.add_obj(Tank(f"Dummy {self.objects.last_id + 2}", self.mpos_world))
                if event.button == 3:
                    # delete non-controllable player if mouse hits it (them)
                    for obj_id, obj in self.objects.all():
                        if obj.bounding_box().collidepoint(self.mpos_world) and not obj.controllable:
                            self.delete_obj(obj_id)

    def update(self):
        for obj_id, obj in self.objects.all():
            obj.update(self.delta)

    def draw(self):
        self.main_layer.fill((112, 197, 255))
        self.hud_layer.fill(0)

        for obj_id, obj in self.objects.all():
            obj.draw(self.main_layer)

        self.draw_hud(self.hud_layer)

        self.scr.blit(pg.transform.smoothscale(self.main_layer, self.scr_size), self.screen_rect)   # draw world
        self.scr.blit(self.hud_layer, self.screen_rect)                                             # draw HUD

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

    def delete_obj(self, obj_id):
        self.objects.delete(obj_id)

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

    def update_state(self, state):
        # static: class, id, model, name
        self.position       = Vector(state['position'])
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

        self.owned_by_player = False                # MULTIPLAYER: whether this belongs to the current player
        self.owner_id = None                        # MULTIPLAYER: which client this object belongs to

    def initialize(self):
        super().initialize()

        color = pg.Color('red') if self.owned_by_player else pg.Color('white')

        #font = pg.font.SysFont("couriernew", 16)  # TODO: don't re-load every time...
        font = pg.font.SysFont("segoeui", 14)  # TODO: don't re-load every time...
        self.name_text = font.render(self.name, True, color)

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


        text_center = self.position + (self.sprite.rect.w / 2, self.sprite.rect.h + 10)
        sprite_rect = self.sprite.rect.move(self.position)
        name_text_rect = self.name_text.get_rect(center=text_center)

        scr.blit(self.sprite.surface, sprite_rect)
        scr.blit(self.name_text, name_text_rect)  # TODO: should be in top layer (UI) -> no scaling issues

        #update_rects += [self.sprite.rect.move(self.prev_position), sprite_rect, name_text_rect]

    def tick(self):
        super().tick()
        self.barrel_angle_changed = self.barrel_angle != self.prev_barrel_angle
        # update previous...
        self.prev_barrel_angle = self.barrel_angle

    def bounding_box(self):
        return self.sprite.surface.get_bounding_rect().move(self.position)

    def key_down(self, keys):
        if keys[pg.K_LEFT]:
            self.velocity.x = -50
        if keys[pg.K_RIGHT]:
            self.velocity.x = 50

        if keys[pg.K_UP]:
            self.barrel_angle_rate = 30
        if keys[pg.K_DOWN]:
            self.barrel_angle_rate = -30

    def key_up(self, keys):
        if not (keys[pg.K_UP] or keys[pg.K_DOWN]):
            self.barrel_angle_rate = 0
        if not (keys[pg.K_LEFT] or keys[pg.K_RIGHT]):
            self.velocity.x = 0


if __name__ == '__main__':
    game = Game((WIDTH, HEIGHT), FPS)
    player_tank = Tank("Me", (50,50))
    player_tank.set_as_player()
    game.add_obj(player_tank)

    game.run()
