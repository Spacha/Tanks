import pygame as pg
from pygame.math import Vector2 as Vector

from math import degrees, radians

import pymunk as pm
import pymunk.autogeometry
import pymunk.pygame_util
from pymunk.vec2d import Vec2d
from pymunk import BB

SCR_WIDTH, SCR_HEIGHT = (1200, 900)
FPS = 60

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

#ground_segments = []

def generate_geometry(surface, space):
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
        BB(0, 0, SCR_WIDTH - 1, SCR_HEIGHT - 1), 180, 180, 90, sample_func
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

#--------------------------------------
# Init Pygame
#--------------------------------------

pg.init()
scr = pg.display.set_mode((SCR_WIDTH, SCR_HEIGHT))
#font = pg.font.Font(None, 18)
font = pg.font.SysFont('segoeui', 18)
bigfont = pg.font.SysFont('segoeui', 28)
clock = pg.time.Clock()

#--------------------------------------
# Init Pymunk
#--------------------------------------

space = pm.Space()
space.gravity = 0, 980
# static walls of the world
static = [
    pm.Segment(space.static_body, (-50, -50), (-50, SCR_HEIGHT + 50), 5),
    pm.Segment(space.static_body, (-50, SCR_HEIGHT + 50), (SCR_WIDTH + 50, SCR_HEIGHT + 50), 5),
    pm.Segment(space.static_body, (SCR_WIDTH + 50, SCR_HEIGHT + 50), (SCR_WIDTH + 50, -50), 5),
    pm.Segment(space.static_body, (-50, -50), (SCR_WIDTH + 50, -50), 5),
]
for s in static:
    s.collision_type = 1
space.add(*static)

def pre_solve_static(arb, space, data):
    s = arb.shapes[0]
    space.remove(s.body, s)
    print("Body removed.")
    return False

space.add_collision_handler(0, 1).pre_solve = pre_solve_static

terrain_surface = pg.Surface((SCR_WIDTH, SCR_HEIGHT), flags=pg.SRCALPHA)
#terrain_surface.fill(pg.Color('white'))

#color = pg.color.THECOLORS['pink']
#pg.draw.circle(terrain_surface, color, (SCR_WIDTH / 2, SCR_HEIGHT / 2), 150)
IMG_FILENAME = "img/map-cave.png"
map_sprite = pg.image.load(IMG_FILENAME)
map_rect = map_sprite.get_rect(bottomleft=(0, SCR_HEIGHT))
terrain_surface.blit(map_sprite, map_rect)
generate_geometry(terrain_surface, space)

player_sprite_right = pg.image.load("img/tank1_base_.png")
player_sprite_left = pg.transform.flip(player_sprite_right, True, False)

#--------------------------------------
# Init game
#--------------------------------------
player_sink = 6
mass = 2000
poly_w, poly_h = (54, 28 - player_sink) #(40, 20)
moment = pm.moment_for_box(mass, (poly_w, poly_h))
player = pm.Body(mass, moment)
player.position = (90, 540)
player.center_of_gravity = Vec2d(0, 12) # VERY low-center of gravity
# Create poly-rect:
poly_points = [
    (-poly_w / 2, -poly_h / 2),   # top-left
    ( poly_w / 2, -poly_h / 2),   # top-right
    ( poly_w / 2,  poly_h / 2),   # bottom-left
    (-poly_w / 2,  poly_h / 2),   # bottom-right
]
player_shape = pm.Poly(player, poly_points)
player_shape.friction = 10.0
space.add(player, player_shape)

draw_options = pm.pygame_util.DrawOptions(scr)
pm.pygame_util.positive_y_is_up = False

TOTAL_AP            = 100
MOVEMENT_AP_COST    = 20
SHOOT_AP_COST       = 25
direction = 0
player_last_pos = player.position

#--------------------------------------
# Start game loop
#--------------------------------------

action_points = TOTAL_AP

debug_mode = False

delta = 0.0
running = True
while running:

    #--------------------------------------
    # Get events
    #--------------------------------------

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.KEYUP:
            if event.key == pg.K_q:
                running = False
            elif event.key == pg.K_F1:
                debug_mode = not debug_mode
            elif event.key in [pg.K_LEFT, pg.K_RIGHT]:
                direction = 0
            elif event.key == pg.K_TAB:
                action_points = TOTAL_AP
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_LEFT:
                direction = -1
            elif event.key == pg.K_RIGHT:
                direction = +1

    #--------------------------------------
    # Update game
    #--------------------------------------

    if action_points <= 0:
        action_points = 0
        direction = 0

    on_ground = False
    #for s in ground_segments:
    #    if player_shape.shapes_collide(s):
    for s in space.shapes:
        if hasattr(s, "is_ground") and s.is_ground:
            if player_shape.shapes_collide(s).points:
                on_ground = True
                break

    if direction:
        #player_shape.surface_velocity = -direction * 20, 0
        #print(player.surface_velocity)
        #print(degrees(player.rotation_vector.angle))
        #player.velocity = Vec2d(direction * 20.0, player.velocity.y)
        #player.velocity += direction * player.rotation_vector * 20
        #player.apply_impulse_at_local_point(direction * player.rotation_vector * 20000)
        #if player_shape.shapes_collide(space.static_body): # on ground
        if on_ground:
            #player_shape.friction = 0.0
            player.apply_impulse_at_local_point(direction * player.rotation_vector * 50000, (0, 14))
        #player.apply_force_at_local_point(-direction * player.rotation_vector * 2E6)
        #player.friction = -4000 / space.gravity.y
    else:
        #player_shape.friction = 10.0
        pass


    space.step(1.0 / FPS)

    # post-update

    if on_ground:
        player_movement = (player.position - player_last_pos).length
        if direction and player_movement > 0.1:
            #print(player.position - player_last_pos, player_movement)
            action_points -= player_movement * delta * MOVEMENT_AP_COST

    #--------------------------------------
    # Draw screen
    #--------------------------------------

    scr.fill( pg.Color('deepskyblue1') )

    # rotate(surface, angle, pivot, offset):
    rotated_sprite, sprite_rect = rotate(player_sprite_right, degrees(player.angle), (0, 0), Vector(0, player_sink - 14))
    #scr.blit(pg.transform.rotate(player_sprite_right, -degrees(player.angle)), player.position - rotation_offset)

    scr.blit(rotated_sprite, sprite_rect.move(player.position))
    scr.blit(terrain_surface, (0, 0))
    if debug_mode:
        space.debug_draw(draw_options)

        if direction:
            direction_text = font.render(f"Player movement: {'left' if direction < 0 else 'right'}", True, pg.Color('black'))
            scr.blit(direction_text, direction_text.get_rect(topleft=(10,10)))

        if on_ground:
            t = font.render(f"On ground", True, pg.Color('black'))
            scr.blit(t, t.get_rect(topleft=(10,30)))


    # draw "no action points" notification
    if action_points <= 0:
        t1 = bigfont.render(f"End of action points!", True, pg.Color('white'))
        t2 = font.render(f"Press [TAB] to end turn.", True, pg.Color('black'))
        pg.draw.rect(scr, (175,28,0), pg.Rect( 0, 40, SCR_WIDTH, 90 ))
        pg.draw.line(scr, (120,18,0), (0, 40), (SCR_WIDTH, 40))
        pg.draw.line(scr, (120,18,0), (0, 40 + 90), (SCR_WIDTH, 40 + 90))
        scr.blit(t1, t1.get_rect(center=(SCR_WIDTH / 2, 63)))
        scr.blit(t2, t2.get_rect(center=(SCR_WIDTH / 2, 63 + 44)))


    # draw 'action bar indicator'
    color = pg.Color('green')
    if action_points <= SHOOT_AP_COST:
        color = pg.Color('red')
    elif action_points <= SHOOT_AP_COST + 10:
        color = pg.Color('orange')
    pg.draw.rect(scr, color, pg.Rect(12, SCR_HEIGHT - 38, action_points * 2 - 4, 20 - 4))
    # action bar frame
    pg.draw.rect(scr, pg.Color('white'), pg.Rect(10, SCR_HEIGHT - 40, TOTAL_AP * 2, 20), 1)
    # shoot indicator
    pg.draw.line(scr, pg.Color('white'), (9 + SHOOT_AP_COST * 2, SCR_HEIGHT - 39), (9 + SHOOT_AP_COST * 2, SCR_HEIGHT - 22))
    player_last_pos = player.position

    pg.display.update()

    #--------------------------------------
    # Tick the clock
    #--------------------------------------

    delta = clock.tick(FPS) / 1000.0
    pg.display.set_caption(f"Demo - FPS: {round(clock.get_fps(), 2)}")
