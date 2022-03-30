import pygame as pg
from pygame.math import Vector2 as Vector

SCR_WIDTH, SCR_HEIGHT = (900,700)
FPS = 60

pg.init()
scr = pg.display.set_mode((SCR_WIDTH, SCR_HEIGHT))
#font = pg.font.Font(None, 18)
font = pg.font.SysFont('helvetica', 18)
clock = pg.time.Clock()

# Init game
circle_pos = Vector(SCR_WIDTH / 2, SCR_HEIGHT / 2)
circle_vel = Vector(0,0)

delta = 0.0
running = True
while running:

    # Get events
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.KEYUP:
            if event.key == pg.K_q:
                running = False

    # Update game

    circle_pos += circle_vel * delta

    # Draw screen
    scr.fill(( 0, 0, 0 ))

    pg.draw.circle(scr, pg.Color('red'), circle_pos, 100, 1)

    pg.display.update()
    delta = clock.tick(FPS)