import os, time
import pygame as pg
from pygame.math import Vector2 as Vector
from math import sqrt, sin, cos, tan, pi as PI
from random import randint

NUM_RIGID_BODIES = 1
rigid_bodies = []

# Pygame ----------------------------------------------#
SCR_WIDTH, SCR_HEIGHT = (900,700)
FPS = 60
# Pygame ----------------------------------------------#

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

        # physics (not here!)
        self.velocity = Vector(0,0)

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
        #pg.draw.circle(scr, pg.Color('grey'), self.position, self.containing_radius, 1)
        pg.draw.circle(scr, pg.Color('black'), self.position, 2)

    def containing_box(self):
        #return self.sprite.get_rect(center=self.position)
        pass

# 2D box shape. Physics engines usually have a couple different classes of shapes
# such as circles, spheres (3D), cylinders, capsules, polygons, polyhedrons (3D)...
class BoxShape:
    def __init__(self, w, h, m):
        self.width = w
        self.height = h
        self.mass = m
        self.calculate_box_inertia()

    # Calculates the inertia of a box shape and stores it.
    def calculate_box_inertia(self):
        self.moment_of_inertia = self.mass * (self.width**2 + self.height**2) / 12

# Two dimensional rigid body
class RigidBody:
    def __init__(self, pos, linear_vel, angle, angular_vel):
        self.position           = pos
        self.linear_velocity    = linear_vel
        self.angle              = angle
        self.angular_velocity   = angular_vel

        self.force = Vector(0,0)
        self.torque = 0.0
        self.shape = None

    def draw(self, scr):
        rect = Rect(pg.Color('white'), self.position, self.shape.width, self.shape.height)
        rect.rotate(self.angle / PI * 180)
        rect.draw(scr)

        r = Vector(self.shape.width / 2, self.shape.height / 2)
        pg.draw.line(scr, pg.Color('red'), r, r + self.force)

def initialize_rigid_bodies():
    for i in range(NUM_RIGID_BODIES):
        rigid_body = RigidBody(
            pos         = Vector( randint(50,SCR_WIDTH-50), randint(50,SCR_HEIGHT/2) ),
            linear_vel  = Vector(0,0),
            angle       = randint(0,360) / 360 * PI * 2,
            angular_vel = 0.0)

        rigid_body.shape = BoxShape(
            w = 1 + 20*randint(1,4),
            h = 1 + 20*randint(1,4),
            m = 10)
        rigid_bodies.append(rigid_body)

# Applies a force at a point in the body, inducing some torque.
def compute_force_and_torque(rigid_body):
    f = Vector(10, 10)
    rigid_body.force = f

    # r is the 'arm vector' that goes from the center of mass to the point of force application
    r = Vector(rigid_body.shape.width / 2, rigid_body.shape.height / 2)
    rigid_body.torque = r.x * f.y - r.y * f.x

def print_rigid_bodies():
    for i, rigid_body in enumerate(rigid_bodies):
        print(f"body[{i}]: pos = {rigid_body.position}, angle: = {rigid_body.angle}")

# Pygame ----------------------------------------------#
def draw_rigid_bodies(scr):
    scr.fill((150,150,150))
    for i, rigid_body in enumerate(rigid_bodies):
        rigid_body.draw(scr)
        #pg.draw.rect(scr, pg.Color('white'), rigid_body.get_rect(), 1)

    pg.display.update()

# Pygame ----------------------------------------------#

# https://toptal.com/game/video-game-physics-part-i-an-introduction-to-rigid-body-dynamics
def run_rigid_body_simulation():
    total_simulation_time = 10.0    # The simulation will run for 10 seconds.
    current_time = 0.0            # This accumulates the time that has passed.
    dt = 0.05                      # Each step will take one second.

    # Pygame ----------------------------------------------#
    pg.init()
    scr = pg.display.set_mode((SCR_WIDTH, SCR_HEIGHT))
    clock = pg.time.Clock()
    running = True
    # Pygame ----------------------------------------------#
    
    initialize_rigid_bodies()
    print_rigid_bodies()
    
    while current_time < total_simulation_time and running:
        # Pygame ----------------------------------------------#
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    running = False
        # Pygame ----------------------------------------------#

        for rigid_body in rigid_bodies:
            compute_force_and_torque(rigid_body)
            linear_acceleration = Vector(rigid_body.force.x / rigid_body.shape.mass, rigid_body.force.y / rigid_body.shape.mass)
            rigid_body.linear_velocity.x += linear_acceleration.x * dt
            rigid_body.linear_velocity.y += linear_acceleration.y * dt

            rigid_body.position.x += rigid_body.linear_velocity.x * dt
            rigid_body.position.y += rigid_body.linear_velocity.y * dt

            angular_acceleration = rigid_body.torque / rigid_body.shape.moment_of_inertia
            rigid_body.angular_velocity += angular_acceleration * dt
            rigid_body.angle += rigid_body.angular_velocity * dt
        
        print_rigid_bodies()
        draw_rigid_bodies(scr)  # Pygame

        current_time += clock.tick(1 / dt) / 1000  # Pygame
        #current_time += dt

if __name__ == '__main__':
    run_rigid_body_simulation()
