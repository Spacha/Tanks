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

class Objects:
    def __init__(self):
        self._objs = {}
        self.last_id = 0

        self._pending_addition = set()
        self._pending_delete = set()

    def all(self):
        return self._objs.items()

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
        if type(id) is list:
            self._pending_delete.add(id)
        elif type(id) is int:
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

class Game:
    def __init__(self, scr_size, fps):
        self.scr_size = Vector(scr_size)
        self.fps = fps

        # World
        self.world_scale = 1
        self.world_size = self.scr_size * self.world_scale

        # Init pygame
        pg.init()
        self.scr = pg.display.set_mode(self.scr_size)
        self.main_layer = pg.Surface(self.world_scale * self.scr_size)
        self.screen_rect = self.main_layer.get_rect()
        self.WINDOW_CAPTION = "Sprite study"
        pg.display.set_caption(self.WINDOW_CAPTION)
        self.clock = pg.time.Clock()

        self.running = False
        self.mpos = None
        self.delta = 0.0

        self.objects = Objects()

    def initialize(self):
        for obj_id, obj in self.objects.all():
            obj.initialize()

    def run(self):
        self.running = True
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

                for obj_id, obj in self.objects.all():
                    obj.key_down(keys)

            elif event.type == pg.KEYUP:
                keys = pg.key.get_pressed()
                for obj_id, obj in self.objects.all():
                    obj.key_up(keys)

            elif event.type == pg.MOUSEMOTION:
                self.mpos = Vector(event.pos)
                self.mpos_world = self.mpos * self.world_scale
                #self.tank.position = self.mpos_world

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.add_obj(Tank(self.mpos_world))

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

    def delete_obj(self, obj_id):
        self.objects.delete(obj_id)

class GameObject:
    DIR_LEFT  = Vector(1,0)
    DIR_RIGHT = -Vector(1,0)

    def __init__(self, position):
        self.position = Vector(position)
        self.velocity = Vector(0, 0)
        self.direction = self.DIR_RIGHT
        
        # status tracking
        self.prev_position = self.position
        self.prev_direction = self.direction
        self.position_changed = True
        self.direction_changed = True
        self.position_change = Vector(0, 0)

    def initialize(self):
        pass

    def update(self, delta):
        # for directional game objects
        if self.position.x < self.prev_position.x:
            self.direction = self.DIR_LEFT
        elif self.position.x > self.prev_position.x:
            self.direction = self.DIR_RIGHT

        self.position += delta * self.velocity

    def draw(self, scr):
        pass

    def tick(self):
        self.position_changed = self.position != self.prev_position
        self.position_change = self.position - self.prev_position
        self.direction_changed = self.direction != self.prev_direction

        # update previous...
        self.prev_position = self.position
        self.prev_direction = self.direction

    def key_down(self, keys):
        pass
    def key_up(self, keys):
        pass


class TankSprite:  # TODO: use pg.Sprite as a base!
    DIR_LEFT = GameObject.DIR_LEFT
    DIR_RIGHT = GameObject.DIR_RIGHT

    def __init__(self):
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

    def move(self, position_change):
        self.rect.move_ip(position_change)

    def set_direction(self, direction):
        self.direction = direction
        self.update_current()

    def update_current(self):
        self._sprite = self.sprite_left if (self.direction == self.DIR_LEFT) else self.sprite_right

    def draw(self, scr):
        #print(self.sprite_rect)
        scr.blit(self._sprite, self.rect)

    def rotate_barrel(self, new_angle):
        def rotated_barrel_sprite(angle):
            return rotate(self.barrel_sprite_original, -angle, self.barrel_pos + self.barrel_pivot_pos, self.barrel_pivot_offset)

        self.barrel_sprite, self.barrel_rect = rotated_barrel_sprite(new_angle)
        # repaint tank (both directions) with rotated barrel
        self.sprite_right = self.sprite_right_original.copy()
        self.sprite_right.blit(self.barrel_sprite, self.barrel_rect)  # with barrel already in place
        self.sprite_left = pg.transform.flip(self.sprite_right, True, False)
        self.update_current()


class Tank(GameObject):
    def __init__(self, position):
        super().__init__(position)
        self.barrel_angle = 0                       # how it is currently positioned
        self.barrel_angle_rate = 0                  # how fast is currently changing

        self.prev_barrel_angle = self.barrel_angle  # what was the previous value
        self.barrel_angle_changed = True            # was the value just changed

        self.sprite = TankSprite()

    def initialize(self):
        super().initialize()

    def update(self, delta):
        super().update(delta)
        self.barrel_angle_change = delta * self.barrel_angle_rate
        self.barrel_angle += self.barrel_angle_change

    def draw(self, scr):
        super().draw(scr)

        #if self.position_changed:
        #    self.sprite.move(self.position_change)
        if self.barrel_angle_changed:
            self.sprite.rotate_barrel(self.barrel_angle)
        if self.direction_changed:
            self.sprite.set_direction(self.direction)

        #self.sprite.draw(scr)
        scr.blit(self.sprite._sprite, self.sprite.rect.move(self.position))

    def tick(self):
        super().tick()
        self.barrel_angle_changed = self.barrel_angle != self.prev_barrel_angle
        # update previous...
        self.prev_barrel_angle = self.barrel_angle

    def key_down(self, keys):
        if keys[pg.K_LEFT]:
            self.velocity.x = -50
        if keys[pg.K_RIGHT]:
            self.velocity.x = 50

        if keys[pg.K_UP]:
            self.barrel_angle_rate = 20
        if keys[pg.K_DOWN]:
            self.barrel_angle_rate = -20

    def key_up(self, keys):
        if not (keys[pg.K_UP] or keys[pg.K_DOWN]):
            self.barrel_angle_rate = 0
        if not (keys[pg.K_LEFT] or keys[pg.K_RIGHT]):
            self.velocity.x = 0



if __name__ == '__main__':
    game = Game((640, 320), 60)
    game.add_obj(Tank((50,50)))

    game.initialize()
    game.run()
