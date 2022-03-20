from PIL import Image
import pygame as pg
from pygame.math import Vector2 as Vector
import numpy as np
import time
import sys

CLR_WHITE     = (255,255,255)
CLR_BLACK     = ( 0 , 0 , 0 )
CLR_BLUE      = ( 0 , 0 ,255)
CLR_SKY_BLUE  = (112,197,255)

"""
	This class takes care of game mechanics including the physics.
"""
class Game():
	def __init__(self, scr_size, fps):
		self.scr_size = Vector(scr_size)
		self.fps = fps
		self.scale = 20  # pixels / meter

		# Init pygame
		pg.init()
		self.scr = pg.display.set_mode(self.scr_size)
		pg.display.set_caption("Worms!")
		self.clock = pg.time.Clock()
		self.start_time = 0
		self.current_tick = 0
		self.current_frame = 0
		
		# Graphics stuff
		self.background_clr = CLR_SKY_BLUE
		#self.font_main = pg.font.SysFont('segoeui', 26)
		self.font_main = pg.font.SysFont('couriernew', 16)

		# World settings
		self.world_size = self.to_world(self.scr_size)
		self.gravity = 10 * Vector(0, 9.81)
		self.ground = None
		self.objects = []

		self.delta = 0.0

	def to_screen(self, world_coord):  # [m] -> [px]
		return world_coord * self.scale

	def to_world(self, screen_coord):  # [px] -> [m]
		return screen_coord / self.scale

	def initialize(self):
		"""
			Should be called when everything is set up, right before running.
		"""
		for obj in self.objects:
			obj.initialize()

		self.start_time = time.monotonic()

	def update(self):
		"""
			This is called once per frame. Takes care of updating the simple "physics".
		"""
		for obj in self.objects:
			obj.update(self.delta)  # start by calculating the new position

			# check ground collisions (you could check other collisions here, too)
			if not obj.static:
				# limit horizontal movement
				if obj.left() <= 0:
					obj.position.x = -obj.l_left
				elif obj.right() >= self.world_size[0]:
					obj.position.x = self.world_size[0] - obj.l_right

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
			obj.position.y = ground_h - obj.l_bottom + self.ground.sink
			obj.set_velocity( y = 0 )

			if not obj.on_ground:
				obj.on_ground = True
		else:
			#obj.velocity.y += self.delta * self.gravity # gravity pulls the object down
			obj.apply_impulse( self.gravity )

			# little treshold, objects 1 pixel above ground
			# are still considered to be on the ground
			if (ground_h - obj.bottom() > self.to_world(1)):
				if obj.on_ground:
					obj.on_ground = False

	def draw(self):
		# clear the screen
		self.scr.fill(self.background_clr)

		# draw game objects
		for obj in self.objects:
			obj.draw(self.scr)


		# draw the top layer (e.g. UI elements)
		x,y,m = 0,0,6
		x,y = self.ui_write(" Worms! ", 8, y+m)

		player = self.get_object('Player')
		if player is not None:
			x,y = self.ui_write(" On ground: {} ".format("Yes" if player.on_ground else "No"), 8, y+m)
			x,y = self.ui_write(" Position: ({:.1f},{:.1f}), velocity: ({:.1f},{:.1f}) ".format(
				round(player.position.x, 2), round(player.position.y, 2), round(player.velocity.x, 2), round(player.velocity.y, 2)), 8, y+m)

		self.ui_write(" FPS: {} ".format(self.actual_fps()), 8, y+m)

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

			TODO: Static text should be stored once and only blitted each frame.
		"""
		text = self.font_main.render(text_str, True, CLR_BLACK, CLR_WHITE) 
		text_rect = text.get_rect()
		text_rect.left = x
		text_rect.top  = y

		self.scr.blit(text, text_rect)

		return (text_rect.right, text_rect.bottom)

	def tick(self):
		self.delta = self.clock.tick(self.fps) / 1000  # seconds
		self.current_tick += 1

	def next_frame(self):
		self.current_frame += 1

	def elapsed_time(self):
		return time.monotonic() - self.start_time

	def set_ground(self, ground):
		"""
			Sets given object as ground. Only one
			ground can exist (old one is overwrited).
		"""
		self.add_obj(ground)
		self.ground = ground

	def add_obj(self, obj):
		"""
			Add a new game object to the game (player, ground, npc's...).
		"""
		obj.add_to_game(game)
		self.objects.append(obj)

	def actual_fps(self):
		return round(self.clock.get_fps(), 2)


class InteractsWithPhysics:
	def __init__(self, static=False):
		self.position = Vector(0, 0)
		self.velocity = Vector(0, 0)
		self.static = static

		self._game = None

	def update(self, delta):
		"""
			The game calls this method. This takes care of updating
			all the game-object-specific physics.
		"""
		if not self.static:
			self.position += delta * self.velocity

	def _scale(self, x=0, y=0):
		if type(x) is Vector and y is None:  	# just one vector
			return self._game.delta * x
		else: 									# x, y pair
			return self._game.delta * Vector(x, y)

	def apply_impulse(self, x=0, y=0):
		"""
			Use 1:
				jump = Vector(0, -10)
				self.apply_impulse(jump)
			Use 2:
				jump = -10
				self.apply_impulse(0, jump)
			Use 3:
				jump = -10
				self.impulse(y = jump)
		"""
		#print("Impulse:", impulse(x, y), "delta:", self._game.delta)
		self.velocity += self._scale(x, y)

	def set_velocity(self, x=None, y=None):
		if x is not None:
			self.velocity.x = x
		if y is not None:
			self.velocity.y = y

"""
	This is a class that is the basis of a game object. Use
	this as a parent when creating new types of game objects.
"""
class GameObject(InteractsWithPhysics):
	def __init__(self, label, static=False):
		super().__init__(static)
		self.label = label
		self.sprite = None
		
		self.width = 0
		self.height = 0

		self.on_ground = False
		self._game = None

	def add_to_game(self, game):
		self._game = game

	def initialize(self):
		pass

	def set_bounding_box(self, bounding_box):
		self.bounding_box = bounding_box

		#if type(bounding_box) is Point:
		# 	Pointy 'bounding box', such as one used with small projectiles,
		# 	doesn't need complex geometry. Collision is based on point overlap.
		#else:
		# add shortcuts to edge positions for convenience
		self.l_left 			= bounding_box.left
		self.l_right 			= bounding_box.right
		self.l_top 				= bounding_box.top
		self.l_bottom 			= bounding_box.bottom

		self.l_top_left 		= Vector(self.l_left, self.l_top)
		self.l_top_right 		= Vector(self.l_right, self.l_top)
		self.l_bottom_left 		= Vector(self.l_left, self.l_bottom)
		self.l_bottom_right 	= Vector(self.l_right, self.l_bottom)

		self.size = Vector(self.width, self.height)

	def left(self):  		# left edge position in world coordinates
		return self.position.x + self.l_left
	def right(self):  		# right edge position in world coordinates
		return self.position.x + self.l_right
	def top(self):  		# top edge position in world coordinates
		return self.position.y + self.l_top
	def bottom(self):  		# bottom edge position in world coordinates
		return self.position.y + self.l_bottom
	def top_left(self): 	# top-left corner position in world coordinates
		return self.position + self.l_top_left
	def top_right(self): 	# top-right corner position in world coordinates
		return self.position + self.l_top_right
	def bottom_left(self): 	# bottom-left corner position in world coordinates
		return self.position + self.l_bottom_left
	def bottom_right(self):	# bottom-right corner position in world coordinates
		return self.position + self.l_bottom_right


"""
	This is a game object that is meant to be controlled by the user.
"""
class Player(GameObject):
	def __init__(self, x, y, width, height, clr):
		# construct the parent
		GameObject.__init__(self, 'Player')

		self.movement_speed = 2.5
		self.jump_strength = 750

		self.width = width
		self.height = height
		self.color = clr

		self.position.x = x
		self.position.y = y

		bounding_box = pg.Rect(-width / 2, -height / 2, width, height)
		self.set_bounding_box( bounding_box )

		# Instructions
		self._move_left = False
		self._move_right = False

		# debug
		self._default_color = self.color
		self._last_on_ground = self.on_ground

	def update(self, delta):
		super().update(delta)
		# if collision status changed...
		if self.on_ground != self._last_on_ground:
			self.color = ( 90, 90,255) if self.on_ground else self._default_color
			self._last_on_ground = self.on_ground
			self.repaint()

	def repaint(self):
		size = self._game.to_screen(self.size)
		self.sprite = pg.Surface(size)
		pg.draw.rect(self.sprite, self.color, pg.Rect((0,0), size))

	def initialize(self):
		# graphics
		self.repaint()

	def draw(self, scr):
		"""
			Draw the object. This is different for each
			game object (rectangle, sprite, ball...).
		"""
		scr.blit(self.sprite, self.rect(to_screen=True))

	def rect(self, to_screen=False):
		"""
			Return the pgame Rect object for the object.
		"""
		#return pg.Rect(self.left(), self.top(), self.width, self.height)
		# Converted in screen coordinates:
		pos, size = None, None
		if to_screen:
			pos = self._game.to_screen(self.top_left())
			size = self._game.to_screen(self.size)
		else:
			pos = self.top_left()
			size = self.size

		return pg.Rect(pos, size)

	# Controls
	# TODO: use setters
	def move_left(self, move=True):
		self.velocity.x += (-1 if move else 1) * self.movement_speed
		#self.set_velocity( x = (-1 if move else 1)*self.movement_speed )

	def move_right(self, move=True):
		self.velocity.x += (1 if move else -1) * self.movement_speed
		#self.set_velocity( x = (1 if move else -1)*self.movement_speed )

	def jump(self):
		# player can only jump if it's on the ground
		if self.on_ground:
			self.apply_impulse( y = -self.jump_strength )


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
		IMG_FILENAME = "map2.png"
		self.sprite = pg.image.load(IMG_FILENAME)
		self.bitmap = Image.open(IMG_FILENAME)

		self.sink = 0.15  # how much the ground should give up

	def initialize(self):
		self.img_to_map()

	def draw(self, scr):
		"""
			Draw the original image.
		"""
		scr.blit(self.sprite, ( self._game.to_screen(self.position) ))

	def height_at(self, x):
		"""
			Returns the ground height at given x coordinate.
			Principle:
				1. Check that the given coordinate lays somewhere within the ground.
				2. The corresponding height value is available in the height map
				   that is generated during startup.
		"""
		x_idx = self._game.to_screen( x - self.position.x )

		# object is outside the slope, cannot collide
		if x_idx < 0 or x_idx > (len(self.height_map) - 1):
			return 0

		# get the height value from the height map and add the ground offset value
		return self.position.y + self.height_map[int(x_idx)]

	def img_to_map(self):
		"""
			This is the whole point of this game. This converts the given image
			(should be loaded to self.bitmap as array).
		"""

		bitmap = np.array(self.bitmap)
		
		# last element of each pixel value (= alpha) > 0 => True
		bitmap = bitmap[:,:,-1] > 20

		# initialize an empty array for the final height map
		self.height_map = np.zeros(bitmap.shape[1], dtype=float)
		for x, col in enumerate(bitmap.T):
			for y, is_ground in enumerate(col): # 

				# First ground pixel found (=surface)! Save the location
				# to the 'height map' and move to the next column.
				if is_ground:
					self.height_map[x] = self._game.to_world(y)
					break


# -------------------------------
#         INIT THE GAME
# -------------------------------
FPS = 90
SCR_SIZE = (800, 600)

game = Game(SCR_SIZE, FPS)

# make the player
player = Player(5, 10, 2, 1, CLR_BLUE)
game.add_obj(player)

# make the ground
ground = Ground(0, (600-200) / 20)
game.set_ground(ground)

game.initialize()

exit = False
while not exit:
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
			elif event.key == pg.K_SPACE:
				player.jump()
			elif event.key == pg.K_SPACE:
				player.jump()
			elif event.key == pg.K_LEFT:
				player.move_left(True)
			elif event.key == pg.K_RIGHT:
				player.move_right(True)

		if event.type == pg.KEYUP:
			if event.key == pg.K_LEFT:
				player.move_left(False)
			if event.key == pg.K_RIGHT:
				player.move_right(False)

	# -------------------------------
	#         Update Game
	# -------------------------------
	
	# update physics every other frame
	update_physics = game.current_frame % 2 == 0
	
	if update_physics:
		game.update()

	# -------------------------------
	#         Draw Graphics
	# -------------------------------

	game.draw()
	pg.display.update()

	if update_physics:
		game.tick()
	game.next_frame()

pg.quit()
sys.exit()
