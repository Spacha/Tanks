from enum import Enum, auto
from math import sin, cos, radians
from PIL import Image
import pygame as pg
import numpy as np
import time
import sys

from GameEngine.Core import Game, GameObject, Color as CLR

class GameStates(Enum):
    MAIN_MENU = auto()
    SETTINGS  = auto()
    PLAYING   = auto()
    PAUSED    = auto()

class Tanks(Game):
    def __init__(self, scr_size, fps):
        super().__init__(scr_size, fps)
        # self.state = GameStates.MAIN_MENU


"""
    This is a game object that is meant to be controlled by the user.
"""
class Player(GameObject):
    def __init__(self, x, y, width, height, clr):
        # construct the parent
        GameObject.__init__(self, 'Player')

        # barrel
        self.barrel_length       = 10
        self.min_barrel_angle    = radians(0)
        self.max_barrel_angle    = radians(85)
        self.barrel_angle        = radians(0)
        self.barrel_movement     = 0
        self.max_barrel_movement = radians(90) # 1 deg per frame

        self.max_velocity = 100.0
        self.jump_strength = 150.0

        self.height = height
        self.width = width
        self.color = clr

        self.direction = 1  # 1 = right, -1 = left
        self.position.x = x
        self.position.y = y

        # Instructions
        self._move_left = False
        self._move_right = False

    def draw(self, scr):
        """
            Draw the object. This is different for each
            game object (rectangle, sprite, ball...).
        """

        # draw the barrel
        startpos = (int(self.position.x + self.width / 2), self.position.y)
        endpos   = (int(startpos[0] + self.direction * self.barrel_length * cos(self.barrel_angle)),
                    int(startpos[1] - self.barrel_length * sin(self.barrel_angle)))
        
        pg.draw.line(scr, CLR.WHITE, startpos, endpos, 2)
        pg.draw.rect(scr, self.color, self.rect())

    def rect(self):
        """
            Return the pgame Rect object for the object.
        """
        return pg.Rect(self.position.x, self.position.y, self.width, self.height)

    def update(self, delta):
        super().update(delta)
        self.barrel_angle += self.barrel_movement * delta

        # limit movement
        if self.barrel_angle < self.min_barrel_angle:
            self.barrel_angle = self.min_barrel_angle
        elif self.barrel_angle > self.max_barrel_angle:
            self.barrel_angle = self.max_barrel_angle


    # Controls
    # TODO: use setters
    def move_left(self, move = True):
        if move: self.direction = -1
        self.velocity.x += (-1 if move else 1) * self.max_velocity

    def move_right(self, move = True):
        if move: self.direction = 1
        self.velocity.x += (1 if move else -1) * self.max_velocity

    def aim_up(self, aim = True):
        self.barrel_movement -= (-1 if aim else 1) * self.max_barrel_movement

    def aim_down(self, aim = True):
        self.barrel_movement += (-1 if aim else 1) * self.max_barrel_movement

    def jump(self):
        # player can only jump if it's on the ground
        if self.on_ground:
            self.velocity.y = -self.jump_strength


"""
    This is a game object that is meant to be the ground. It's static so
    gravity doesn't affect it. The ground is formed from an image that
    has R, B, G, and alpha channels. Transparent pixels are ignored
    in collision detection.
"""
class Ground(GameObject):
    def __init__(self, x=0, y=0):
        # construct the parent
        GameObject.__init__(self, 'Slope', static=True)

        self.position.x = x
        self.position.y = y

        # the image that represents the ground
        IMG_FILENAME = "GameEngine/img/hills2.png"
        self.sprite = pg.image.load(IMG_FILENAME)
        self.bitmap = Image.open(IMG_FILENAME)
        self.img_to_map()

        self.sink = 5       # how much the ground should give up

    def draw(self, scr):
        """
            Draw the original image.
        """
        scr.blit(self.sprite, self.position.as_tuple())

    def height_at(self, x):
        """
            Returns the ground height at given x coordinate.
            Principle:
                1. Check that the given coordinate lays somewhere within the ground.
                2. The corresponding height value is available in the height map
                   that is generated during startup.
        """
        x_idx = round(x - self.position.x)

        # object is outside the slope, cannot collide
        if x_idx < 0 or x_idx > (len(self.height_map) - 1):
            return 0

        # get the height value from the height map and add the ground offset value
        return self.position.y + self.height_map[x_idx]

    def img_to_map(self):
        """
            This is the whole point of this game. This converts the given image
            (should be loaded to self.bitmap as array).
            Principle:
                1. Convert the array to numpy array. This allows advanced but lightweight operations.
                   The image is a 3d array: (rows, columns, pixel channels)
                2. Convert the pixel channels to truth values (T/F):
                      True:  the pixel is solid ground
                      False: the pixel is 'air'
                3. The height map will contain only the surface pixels. A surface pixel is
                   the first pixel on each columns when going from top to bottom. For this,
                   we transpose the image (turn rows into columns and vice versa) and go
                   through the rows (that are now columns) taking the first 'True' element
                   from each. That is the surface pixel and these form the height map.
        """

        bitmap = np.array(self.bitmap)

        # For each pixel: [0,0,0,0] => False, otherwise True
        #bitmap = np.any(bitmap[::-1], axis=2)

        # Ok, this is different:
        # last element of each pixel value (= alpha) > 20 => True
        bitmap = bitmap[:,:,-1] > 20

        # initialize an empty array for the final height map
        self.height_map = np.zeros(bitmap.shape[1], dtype=int)
        for x, col in enumerate(bitmap.T):
            for y, is_ground in enumerate(col): # 

                # First ground pixel found (=surface)! Save the location
                # to the 'height map' and move to the next column.
                if is_ground:
                    self.height_map[x] = int(y)
                    break


# -------------------------------
#         INIT THE GAME
# -------------------------------
FPS = 100.0
SCR_SIZE = (900, 750)

game = Tanks(SCR_SIZE, FPS)

# make the player
player = Player(100, 200, 10, 10, (238,59,59))
game.add_obj(player)

# make the ground
ground = Ground(0, 300)
game.set_ground(ground)

# Register keys

# meta
game.key_actions.down( pg.K_q,     game.exit )
# player movement
game.key_actions.down( pg.K_LEFT,  lambda: player.move_left(True) )
game.key_actions.up( pg.K_LEFT,    lambda: player.move_left(False) )
game.key_actions.down( pg.K_RIGHT, lambda: player.move_right(True) )
game.key_actions.up( pg.K_RIGHT,   lambda: player.move_right(False) )
# player activity
game.key_actions.down( pg.K_UP,    lambda: player.aim_up(True) )
game.key_actions.up( pg.K_UP,      lambda: player.aim_up(False) )
game.key_actions.down( pg.K_DOWN,  lambda: player.aim_down(True) )
game.key_actions.up( pg.K_DOWN,    lambda: player.aim_down(False) )

game.key_actions.down( pg.K_SPACE, lambda: player.jump() )

while game.running:
    loop_start_time = time.time()

    # -------------------------------
    #         Handle Events
    # -------------------------------
    
    game.handle_events()

    # -------------------------------
    #         Update Game
    # -------------------------------
    
    game.update()

    # -------------------------------
    #         Draw Graphics
    # -------------------------------

    game.draw()
    pg.display.update()

    game.tick()
    game.last_loop_time = time.time() - loop_start_time

pg.quit()
sys.exit()
