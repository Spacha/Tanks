import os
import pygame as pg
from pygame.math import Vector2 as Vector
from math import sqrt, sin, cos, tan

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

FPS = 60

pg.init()
scr = pg.display.set_mode((640, 480))
clock = pg.time.Clock()

class GameObject:
    def __init__(self, position):
        self.position = Vector(position)
        self.velocity = Vector(0,0)
        self.rotation = 0.0
        self.sprite = pg.image.load(os.path.join('img', 'tank1_blue_base.png'))
        self.surface = pg.Surface(self.sprite.get_size(), flags=pg.SRCALPHA)
        self.collides = False

    def draw(self, scr):
        self.surface.fill(0)
        self.surface.blit(self.sprite, (0,0))
        # bounding box
        rect = self.sprite.get_rect()
        rect_color = pg.Color('red') if self.collides else pg.Color('green')
        pg.draw.rect(self.surface, rect_color, rect, 1)
        # center point
        pg.draw.circle(self.surface, pg.Color('white'), rect.center, 2)
        self.surface_transformed = pg.transform.rotate(self.surface, self.rotation)
        scr.blit(self.surface_transformed, self.bounding_box())

    def bounding_box(self):
        #return self.sprite.get_rect(center=self.position)
        return self.sprite.get_rect(center=self.position)

class Rect:
    def __init__(self, color, position, w, h):
        self.color = color
        self.position = Vector(position)        # center
        self.w = w
        self.h = h

        self.x_axis = Vector(self.w / 2, 0)   # local x-axis, defines 'width'
        self.y_axis = Vector(0, self.h / 2)   # local y-axis, defines 'height'
        self.rotation = 0.0

        # collision
        self.collides = False

        self.points = [
            Vector(-self.w / 2, -self.h / 2),   # top-left
            Vector( self.w / 2, -self.h / 2),   # top-right
            Vector( self.w / 2,  self.h / 2),   # bottom-left
            Vector(-self.w / 2,  self.h / 2),   # bottom-right
        ]

    def point_collision(self, point):
        '''return (rect.x <= point.x <= rect.right and
                rect.y <= point.y <= rect.bottom)'''
        def to_local_coords(point):
            point -= self.position
            x = point.project(self.x_axis)
            y = point.project(self.y_axis)
            dot_x = point.dot(self.x_axis)
            dot_y = point.dot(self.y_axis)
            #print(x, dot_x, "\t", y, dot_y)
            #sign_x = -1 if x.x < 0 else 1
            #sign_y = -1 if y.x < 0 else 1
            #print(Vector(sign_x * x.length(), sign_y * y.length(), ))
            sign_x = -1 if dot_x < 0 else 1
            sign_y = -1 if dot_y < 0 else 1
            print(sign_x * x.length(), "\t", sign_y * y.length())
            #print(sign_x * x.length(), "\t", sign_x * x.length())
            #print(point.project(self.y_axis).angle_to(Vector(1,0)))
            '''
            return Vector(
                point.project(self.x_axis).length(),
                point.project(self.y_axis).length())
            '''

        local_point = to_local_coords(point.copy())
        #print(local_point)


    def rotate(self, angle):
        self.rotation += angle
        for point in self.points:
            point.rotate_ip(-angle)

        self.x_axis.rotate_ip(-angle)
        self.y_axis.rotate_ip(-angle)

    def draw(self, scr):
        color = pg.Color('red') if self.collides else pg.Color('green')
        pg.draw.polygon(scr, color, [point + self.position for point in self.points], 1)
        pg.draw.circle(scr, pg.Color('white'), self.position, 2)

    def bounding_box(self):
        #return self.sprite.get_rect(center=self.position)
        return self.sprite.get_rect(center=self.position)

obj = GameObject((320,240))
poly_rect = Rect(pg.Color('black'), (320,240), 40, 20)
point_pos = Vector(200,240)

delta = 0
running = True
while running:

    # 1. Check events
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.MOUSEMOTION:
            obj.position = Vector(event.pos)

    keys = pg.key.get_pressed()
    if keys[pg.K_q]:
        running = False
    if keys[pg.K_UP]:
        #obj.position.y -= delta * 75
        poly_rect.position.y -= delta * 75
    elif keys[pg.K_DOWN]:
        #obj.position.y += delta * 75
        poly_rect.position.y += delta * 75
    if keys[pg.K_RIGHT]:
        #obj.position.x += delta * 75
        poly_rect.position.x += delta * 75
    elif keys[pg.K_LEFT]:
        #obj.position.x -= delta * 75
        poly_rect.position.x -= delta * 75
    if keys[pg.K_z]:
        #obj.rotation += delta * 45
        poly_rect.rotate(delta * 45)
    elif keys[pg.K_x]:
        #obj.rotation -= delta * 45
        poly_rect.rotate(-delta * 45)

    # 2. Update
    def point_collision(rect, point):
        return (rect.x <= point.x <= rect.right and
                rect.y <= point.y <= rect.bottom)

    obj.collides = point_collision(obj.bounding_box(), point_pos)
    poly_rect.point_collision(point_pos)

    # 3. Draw
    pg.display.set_caption(f"Collision study - FPS: {round(clock.get_fps(), 2)}")
    scr.fill((150,150,150))

    pg.draw.circle(scr, pg.Color('white'), point_pos, 2)
    obj.draw(scr)

    poly_rect.draw(scr)

    pg.display.update()

    # 4. Tick
    delta = clock.tick(FPS) / 1000
pg.quit()
