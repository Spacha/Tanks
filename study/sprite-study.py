import time
import pygame as pg
from pygame.math import Vector2 as Vector

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
        if type(id) is int:
            self._pending_delete.add(id)
        elif type(id) is list:
            self._pending_delete.update(id)
        else:
            raise ValueError('Object ID must be integer!')

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
        self.world_scale = 1
        self.world_size = self.scr_size * self.world_scale

        # Init pygame
        pg.init()
        self.clock = pg.time.Clock()
        # display-related...
        self.scr = pg.display.set_mode(self.scr_size)
        self.main_layer = pg.Surface(self.world_scale * self.scr_size)
        self.screen_rect = self.main_layer.get_rect()
        self.WINDOW_CAPTION = "Sprite study"
        pg.display.set_caption(self.WINDOW_CAPTION)

        self.running = False
        self.mpos = None
        self.delta = 0.0

        self.objects = ObjectContainer()

    def initialize(self):
        self.objects.apply_pending_changes()
        for obj_id, obj in self.objects.all():
            print("initializing")
            obj.initialize()
        self.running = True

    def run(self):
        self.initialize()
        while self.running:
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
                    self.add_obj(Tank(f"Player {self.objects.last_id + 2}", self.mpos_world))
                if event.button == 3:
                    # delete non-controllable player if mouse hits it (them)
                    for obj_id, obj in self.objects.all():
                        if obj.bounding_box().collidepoint(self.mpos_world) and not obj.controllable:
                            self.delete_obj(obj_id)

    def update(self):
        # apply pending deletes and additions
        self.objects.apply_pending_changes()

        for obj_id, obj in self.objects.all():
            obj.update(self.delta)

    def draw(self):
        self.main_layer.fill((112, 197, 255))

        for obj_id, obj in self.objects.all():
            obj.draw(self.main_layer)

        self.scr.blit(pg.transform.scale(self.main_layer, self.scr_size), self.screen_rect)
        pg.display.flip()

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
    DIR_LEFT  = Vector(1,0)
    DIR_RIGHT = -Vector(1,0)

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


class TankSprite:  # TODO: use pg.Sprite as a base!
    DIR_LEFT = GameObject.DIR_LEFT
    DIR_RIGHT = GameObject.DIR_RIGHT

    def __init__(self, text=""):
        self.text = text
        # BARREL: coordinates defined by the sprite image (in pixels)
        self.barrel_pos             = Vector(25, 24)    # sprite top-left position in the tank sprite
        self.barrel_pivot_pos       = Vector(2, 2)      # pivot position from top-left of the sprite
        self.barrel_pivot_offset    = Vector(11, 0)     # pivot offset from the sprite center (of rotation)
        self._initialize()

    def _initialize(self):
        self.sprite_right_original = pg.image.load("tank1_base.png")  # preserve the original for re-blit
        self.barrel_sprite_original = pg.image.load("tank1_barrel.png")
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
    def __init__(self, name, position):
        super().__init__(position)
        self.name = name
        self.barrel_angle = 0                       # how it is currently positioned
        self.barrel_angle_rate = 0                  # how fast is currently changing
        self.barrel_angle_min = -10
        self.barrel_angle_max = 70

        self.prev_barrel_angle = self.barrel_angle  # what was the previous value
        self.barrel_angle_changed = True            # was the value just changed

        self.sprite = TankSprite()

    def initialize(self):
        super().initialize()

        font = pg.font.SysFont("couriernew", 16)  # TODO: don't re-load every time...
        self.name_text = font.render(self.name, True, pg.Color('white'))

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
    game = Game((640, 320), 200)
    player_tank = Tank("Me", (50,50))
    player_tank.set_as_player()
    game.add_obj(player_tank)

    game.run()