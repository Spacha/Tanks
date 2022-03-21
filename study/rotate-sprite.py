import pygame as pg
from pygame.math import Vector2 as Vector
from math import sin, cos, tan
import time

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

sprite_right = pg.image.load("tank1_base.png")
barrel_sprite = pg.image.load("tank1_barrel.png")
barrel_pos = Vector(25, 24)

pg.init()
clock = pg.time.Clock()
scr = pg.display.set_mode((400, 200))

sprite = sprite_right.copy()
sprite.blit( barrel_sprite, barrel_sprite.get_rect().move(barrel_pos) )
sprite = pg.transform.scale(sprite, (100, 100))
'''
print("Starting...")
start_t = time.time()
N = 1000
for i in range(N):
    barrel_sprite_rot = barrel_sprite.copy()
    barrel_sprite_rot, barrel_rect_rot = rotate( barrel_sprite_rot, i, barrel_pos + (2,2), Vector(11,0) )
print(f"Time: {(time.time() - start_t) / N * 1000000} us")
'''
angle = 0

running = True
while running:
    for e in pg.event.get():
        if e.type == pg.QUIT:
            running = False


    angle += 0.5
    #angle = 90
    sprite_rot = sprite_right.copy()
    barrel_sprite_rot = barrel_sprite.copy()
    #barrel_center = (barrel_sprite_rot.get_width() / 2, barrel_sprite_rot.get_height() / 2)
    # vector (11,0) is the offset from center to the pivot point
    # we needed to add 2 to the vector so that 
    barrel_sprite_rot, barrel_rect_rot = rotate( barrel_sprite_rot, -angle, barrel_pos + (2,2), Vector(11,0) )
    #barrel_sprite_rot, barrel_rect_rot = rotate( barrel_sprite_rot, -angle, barrel_pos, (2,2) )
    sprite_rot.blit( barrel_sprite_rot, barrel_rect_rot )
    sprite_rot = pg.transform.scale(sprite_rot, (100, 100))

    scr.fill((255,255,255))

    scr.blit( sprite, sprite.get_rect() )
    scr.blit( sprite_rot, sprite_rot.get_rect().move(100,0) )


    pg.display.flip()
    pg.display.set_caption(f"FPS: {round(clock.get_fps(), 2)}")
    clock.tick(60)

pg.quit()
