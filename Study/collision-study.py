import os, time
import pygame as pg
from pygame.math import Vector2 as Vector
from math import sqrt, sin, cos, tan
from random import randint

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

SCR_WIDTH, SCR_HEIGHT = (640,480)
FPS = 60

pg.init()
scr = pg.display.set_mode((SCR_WIDTH, SCR_HEIGHT))
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

        # for collision...
        self.collides = False

        # NOTE: must be re-calculated when size changes!
        self.containing_radius = (self.x_axis + self.y_axis).length()

        self.points = [
            Vector(-self.w / 2, -self.h / 2),   # top-left
            Vector( self.w / 2, -self.h / 2),   # top-right
            Vector( self.w / 2,  self.h / 2),   # bottom-left
            Vector(-self.w / 2,  self.h / 2),   # bottom-right
        ]

    @property
    def left(self):
        return self.position - self.w / 2
    @property
    def right(self):
        return self.position + self.w / 2
    @property
    def top(self):
        return self.position - self.h / 2
    @property
    def bottom(self):
        return self.position + self.h / 2
    @property
    def local_left(self):
        return - self.w / 2
    @property
    def local_right(self):
        return self.w / 2
    @property
    def local_top(self):
        return - self.h / 2
    @property
    def local_bottom(self):
        return self.h / 2

    def circle_contains(self, point):
        return point.distance_to(self.position) <= self.containing_radius

    def point_collides(self, point):  # Benchmark: ~3 us
        def to_local_coords(point):
            point -= self.position
            x = point.dot(self.x_axis) / (self.w / 2)
            y = point.dot(self.y_axis) / (self.h / 2)
            return Vector(x, y)

        local_point = to_local_coords(point.copy())
        return (self.local_left <= local_point.x <= self.local_right and
                self.local_top <= local_point.y <= self.local_bottom)

    def rotate(self, angle):
        self.rotation += angle
        for point in self.points:
            point.rotate_ip(-angle)

        self.x_axis.rotate_ip(-angle)
        self.y_axis.rotate_ip(-angle)

    def draw(self, scr):
        color = pg.Color('red') if self.collides else pg.Color('green')
        pg.draw.polygon(scr, color, [point + self.position for point in self.points], 1)
        pg.draw.circle(scr, pg.Color('grey'), self.position, self.containing_radius, 1)
        pg.draw.circle(scr, pg.Color('black'), self.position, 2)

    def containing_box(self):
        #return self.sprite.get_rect(center=self.position)
        pass

obj = GameObject((0,0))
poly_rect = Rect(pg.Color('black'), (320,240), 60, 30)
point_pos = Vector(200,240)

N = 500
points = []
for i in range(N):
    # 0: position vector, 1: collides, 2: circle contains
    points.append([Vector(randint(10,SCR_WIDTH-10), randint(10,SCR_HEIGHT-10)), False, False])

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

    poly_rect.collides = False  # reset collision state
    #poly_rect.collides = poly_rect.point_collides(point_pos)
    #start_t = time.time()
    for i, point in enumerate(points):
        # reset collision state
        points[i][1] = False
        points[i][2] = False

        # does the circle contain it?
        if not poly_rect.circle_contains(point[0]):
            continue

        point[2] = True
        # does the rect contain it?
        points[i][1] = poly_rect.point_collides(point[0])
        if points[i][1]:
            poly_rect.collides = True
    #total_t = time.time() - start_t

    #print(f"=> Avg: {total_t / N * 1E6} us per collision.")
    #print(f"=> Total: {total_t * 1E6} us per {N} collisions.")

    # 3. Draw
    pg.display.set_caption(f"Collision study - FPS: {round(clock.get_fps(), 2)}")
    scr.fill((150,150,150))

    pg.draw.circle(scr, pg.Color('white'), point_pos, 2)
    for point in points:
        if point[1]:  # collision
            color = pg.Color('red')
        elif point[2]:  # circle contains
            color = pg.Color('yellow')
        else:
            color = pg.Color('white')

        pg.draw.circle(scr, color, point[0], 2)

    obj.draw(scr)
    poly_rect.draw(scr)

    pg.display.update()

    # 4. Tick
    delta = clock.tick(FPS) / 1000
pg.quit()
