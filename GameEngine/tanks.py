from PIL import Image
import pygame as pg
import numpy as np
import time
import sys

CLR_WHITE = (255,255,255)
CLR_BLACK = ( 0 , 0 , 0 )
CLR_BLUE  = ( 0 , 0 ,255)

"""
    Simple class representing a 2D vector like position and velocity.
"""
class Vector():
    def __init__(self, x, y):
        self.x = x
        self.y = y


"""
    This class takes care of game mechanics including the physics.
"""
class Game():
    def __init__(self, scr_size, fps):
        self.scr_size = scr_size
        self.fps = fps
        self.gravity = 0.3

        # Init pygame
        pg.init()
        self.scr = pg.display.set_mode(self.scr_size)
        pg.display.set_caption("A Slope Game!")
        self.clock = pg.time.Clock()
        
        # Graphics stuff
        self.background_clr = CLR_BLACK
        self.font_main = pg.font.SysFont('segoeui', 26)

        # World settings
        self.ground = None
        self.objects = []

        self.last_loop_time = self.fps

    def update(self):
        """
            This is called once per frame. Takes care of updating the simple "physics".
        """
        for obj in self.objects:
            obj.update() # start by calculating the new position

            # check ground collisions (you could check other collisions here, too)
            if not obj.static:
                self.check_ground(obj)

    def check_ground(self, obj):
        """
            Checks if given object is on (or below) the ground and keeps it on the surface.
            Since we are not using real time-based physics but simple "frame-based",
            the accelerations and such are not 100% correct.
        """
        ground_h = self.ground.height_at(obj.position.x)

        # if the object is on (or below) the surface
        if obj.bottom() >= (ground_h + self.ground.sink):
            obj.position.y = ground_h - obj.height + self.ground.sink

            if not obj.on_ground:
                obj.on_ground = True
        else:
            obj.velocity.y += self.gravity # gravity pulls the object down

            # little treshold, objects 1 pixel above ground
            # are still considered to be on the ground
            if (ground_h - obj.bottom() > 1):
                if obj.on_ground:
                    obj.on_ground = False

    def draw(self):
        # clear the screen
        self.scr.fill(self.background_clr)

        # draw game objects
        for obj in self.objects:
            obj.draw(self.scr)


        # draw the top layer (e.g. UI elements)
        x,y,m = 0,10,10
        x,y = self.ui_write(" A Slope Game! ", 10, y+m)

        player = self.get_object('Player')
        if player is not None:
            x,y = self.ui_write(" On ground: {} ".format("Yes" if player.on_ground else "No"), 10, y+m)

        self.ui_write(" FPS: {} ".format(self.actual_fps()), 10, y+m)

    def get_object(self, label):
        """
            Get an object by label. If not found, None is returned.
        """
        for obj in self.objects:
            if obj.label == label:
                return obj
        return None
        

    def ui_write(self, text_str, x, y):
        """
            A small helper to write UI text on the screen.
            Returns the x and y coordinates of the bottom right
            corner if the text to help write multiple rows/columns.
        """
        text = self.font_main.render(text_str, True, CLR_BLACK, CLR_WHITE) 
        text_rect = text.get_rect()
        text_rect.left = x
        text_rect.top  = y

        self.scr.blit(text, text_rect)

        return (text_rect.right, text_rect.bottom)

    def tick(self):
        self.clock.tick(self.fps)

    def set_ground(self, ground):
        """
            Sets given object as ground. Only one
            ground can exist (old one is overwritten).
        """
        self.add_obj(ground)
        self.ground = ground

    def add_obj(self, obj):
        """
            Add a new game object to the game (player, ground, npc's...).
        """
        self.objects.append(obj)

    def actual_fps(self):
        return round(1/self.last_loop_time, 2)


"""
    This is a class that is the basis of a game object. Use
    this as a parent when creating new types of game objects.
"""
class GameObject():
    def __init__(self, label, static=False):
        self.position = Vector(0, 0)
        self.velocity = Vector(0, 0)
        self.label = label
        self.static = static

        self.width = 0
        self.height = 0

        self.on_ground = False

    def update(self):
        """
            The game calls this method. This takes care of updating
            all the game-object-specific physics.
        """
        if not self.static:
            self.position.x = int(self.position.x + self.velocity.x)
            self.position.y = int(self.position.y + self.velocity.y)

    def bottom(self):
        """
            Return the position of the bottom of the object
            (used in ground collision detection).
        """
        return int(self.position.y + self.height)


"""
    This is a game object that is meant to be controlled by the user.
"""
class Player(GameObject):
    def __init__(self, x, y, width, height, clr):
        # construct the parent
        GameObject.__init__(self, 'Player')

        self.max_velocity = 2.5
        self.jump_strength = 5.0

        self.height = height
        self.width = width
        self.color = clr

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
        pg.draw.rect(scr, self.color, self.rect())

    def rect(self):
        """
            Return the pgame Rect object for the object.
        """
        return pg.Rect(self.position.x, self.position.y, self.width, self.height)

    # Controls
    # TODO: use setters
    def move_left(self, move=True):
        self.velocity.x += (-1 if move else 1) * self.max_velocity

    def move_right(self, move=True):
        self.velocity.x += (1 if move else -1) * self.max_velocity

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
        IMG_FILENAME = "img/hills2.png"
        self.sprite = pg.image.load(IMG_FILENAME)
        self.bitmap = Image.open(IMG_FILENAME)
        self.img_to_map()

        self.sink = 5       # how much the ground should give up

    def draw(self, scr):
        """
            Draw the original image.
        """
        scr.blit(self.sprite, (self.position.x, self.position.y))

    def height_at(self, x):
        """
            Returns the ground height at given x coordinate.
            Principle:
                1. Check that the given coordinate lays somewhere within the ground.
                2. The corresponding height value is available in the height map
                   that is generated during startup.
        """
        x_idx = x - self.position.x

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
SCR_SIZE = (700, 600)

game = Game(SCR_SIZE, FPS)

# make the player
player = Player(100, 200, 10, 10, CLR_BLUE)
game.add_obj(player)

# make the ground
ground = Ground(0, 300)
game.set_ground(ground)

exit = False
while not exit:
    loop_start_time = time.time()

    # -------------------------------
    #         Handle Events
    # -------------------------------

    for event in pg.event.get():
        if event.type == pg.QUIT:
            exit = True
        if event.type == pg.KEYDOWN:
            # emergency exit
            if event.key == pg.K_q:
                exit = True
            if event.key == pg.K_SPACE:
                player.jump()
            if event.key == pg.K_LEFT:
                player.move_left(True)
            if event.key == pg.K_RIGHT:
                player.move_right(True)

        if event.type == pg.KEYUP:
            if event.key == pg.K_LEFT:
                player.move_left(False)
            if event.key == pg.K_RIGHT:
                player.move_right(False)

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
