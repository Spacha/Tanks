import pygame as pg

'''
class Rect(pg.Rect):
	def to_screen(self):
		#return self.move(...)
		return self
	def to_world(self):
		#return self.move(...)
		return self

class Vector(pg.math.Vector2):
	def to_screen(self):
		#return self.move(...)
		return Vector(self) * SCR_SCALE
	def to_world(self):
		#return self.move(...)
		return self
'''


class Screen:
	def __init__(self, size, scale):
		self.size = pg.display.set_mode(size)
		self.scale = scale

	def to_screen(self, coord):
		pass

	def to_world(self, coord):
		pass

	'''
	def draw():

		return pg.draw

		# draw.rect
		# draw.polygon
		# draw.circle
		# draw.ellipse
		# draw.arc
		# draw.line
		# draw.lines
		# draw.aaline
		# draw.aalines
	'''


class Game:
	def __init__(self, scr_size, fps):
		# setup the game
		# ...
		scale = 20

		self.scr = Screen(scr_size, scale)
		self.draw = self.scr.draw

class Player:
	def draw(self, scr):
		#scr.draw.rect()
		#scr.draw.blit(self.surface)
		pass

if __name__ == '__main__':
	game = Game((640, 320), 20)
