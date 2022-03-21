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

class Game:
    def __init__(self, scr_size, fps):
        self.scr_size = Vector(scr_size)
        self.fps = fps
        self.scale = 20  # pixels / meter

        # Init pygame
        pg.init()
        self.scr = pg.display.set_mode(self.scr_size)
        self.WINDOW_CAPTION = "Sprite study"
        pg.display.set_caption(self.WINDOW_CAPTION)
        self.clock = pg.time.Clock()

        self.running = False
        self.mpos = None
        self.delta = 0.0

    def initialize(self):
        self.tank.initialize()

    def run(self):
        self.running = True
        while self.running:
            self.check_events()
            self.update()
            self.draw()
            pg.display.flip()
            self.tick()

    def check_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            # UPDATE: keys = pg.key.get_pressed()
            # if keys[pg.K_q]...
            elif event.type == pg.KEYDOWN:
                # emergency exit
                if event.key == pg.K_q:
                    self.running = False

                if event.key == pg.K_UP:
                    self.tank.barrel_angle_rate = 20
                if event.key == pg.K_DOWN:
                    self.tank.barrel_angle_rate = -20

            elif event.type == pg.KEYUP:
                if event.key == pg.K_UP:
                    self.tank.barrel_angle_rate = 0
                if event.key == pg.K_DOWN:
                    self.tank.barrel_angle_rate = 0

            elif  event.type == pg.MOUSEMOTION:
                self.mpos = event.pos
                self.tank.position = Vector(event.pos)

    def update(self):
        self.tank.update(self.delta)

    def draw(self):
        self.scr.fill((112, 197, 255))
        self.tank.draw(self.scr)

    def tick(self):
        self.delta = self.clock.tick(self.fps) / 1000
        pg.display.set_caption(f"{self.WINDOW_CAPTION} - FPS: {round(self.clock.get_fps(), 2)}")
        self.tank.tick()


class GameObject:
    DIR_LEFT  = Vector(1,0)
    DIR_RIGHT = -Vector(1,0)

    def __init__(self):
        self.position = Vector(0, 0)
        self.direction = self.DIR_RIGHT
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

    def draw(self, scr):
        pass

    def tick(self):
        self.position_changed = self.position != self.prev_position
        self.position_change = self.position - self.prev_position
        self.direction_changed = self.direction != self.prev_direction

        # update previous...
        self.prev_position = self.position
        self.prev_direction = self.direction


class Tank(GameObject):
    def __init__(self):
        super().__init__()

        self.barrel_angle = 0                       # how it is currently positioned
        self.barrel_angle_rate = 0                  # how fast is currently chaning

        self.prev_barrel_angle = self.barrel_angle  # what was the previous value
        self.barrel_angle_changed = True            # was the value just changed

        # Sprite-specific:
        # barrel.position, barrel.pivot_position, barrel_sprite_left, barrel_sprite_left, barrel_sprite
        self.barrel_pos = Vector(25,24)
        self.barrel_pivot_pos = Vector(2,2)
        self.barrel_pivot_offset = Vector(11,0)

    def initialize(self):
        super().initialize()
        self.make_sprite()

    def update(self, delta):
        super().update(delta)
        self.barrel_angle_change = delta * self.barrel_angle_rate
        self.barrel_angle += self.barrel_angle_change

    def _rotated_barrel_sprite(self, angle):
        return rotate(self.barrel_sprite_original, -self.barrel_angle, self.barrel_pos + self.barrel_pivot_pos, self.barrel_pivot_offset)

    def draw(self, scr):
        super().draw(scr)

        if self.position_changed:  # -> move the tank rect
            self.sprite_rect.move_ip(self.position_change)

        
        if self.barrel_angle_changed:  # -> rotate and re-blit the barrel onto the tank
            #self.barrel_sprite = pg.transform.rotate(self.barrel_sprite, self.barrel_angle_change)
            self.barrel_sprite, self.barrel_sprite_rect = self._rotated_barrel_sprite(self.barrel_angle)
            # repaint tank with rotated barrel
            self.sprite_right = self.sprite_right_original.copy()
            self.sprite_right.blit(self.barrel_sprite, self.barrel_sprite_rect)  # with barrel already in place
            self.sprite_left = pg.transform.flip(self.sprite_right, True, False)

        if self.direction_changed or self.barrel_angle_changed:  # -> flip the tank sprite
            if self.direction == self.DIR_LEFT:
                self.sprite = self.sprite_left
            else:
                self.sprite = self.sprite_right


        scr.blit(self.sprite, self.sprite_rect)

    def make_sprite(self):
        # base
        self.sprite_right_original = pg.image.load("tank1_base.png")  # preserve the original for re-blit
        self.sprite_left_original = pg.transform.flip(self.sprite_right_original, True, False)

        self.sprite_right = self.sprite_right_original.copy()
        self.sprite_left = self.sprite_left_original.copy()
        self.sprite_rect = self.sprite_right.get_rect()

        self.barrel_sprite_original = pg.image.load("tank1_barrel.png")

        self.barrel_sprite = self.barrel_sprite_original.copy()
        #self.barrel_sprite_left = pg.transform.flip(self.barrel_sprite_right, True, False)

        #self.barrel_sprite_right = pg.transform.rotate(self.barrel_sprite_right, self.barrel_rot)
        #self.barrel_sprite_left = pg.transform.rotate(self.barrel_sprite_left, -self.barrel_rot)

        # Account for rotation (position based on the bottom of the barrel)
        #print(self.barrel_pos[1], self.barrel_sprite_right.get_height() / 2)
        #self.barrel_pos[1] -= self.barrel_sprite_right.get_height() / 2
        self.barrel_sprite_rect = self.barrel_sprite.get_rect()

    def tick(self):
        super().tick()
        self.barrel_angle_changed = self.barrel_angle != self.prev_barrel_angle
        # update previous...
        self.prev_barrel_angle = self.barrel_angle



if __name__ == '__main__':
    game = Game((640, 320), 60)
    game.tank = Tank()

    game.initialize()
    game.run()
