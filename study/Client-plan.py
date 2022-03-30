import pygame as pg

class ConnectionManager:
	def __init__(self):
		pass

	def connect(self, ip, port):
		pass

	def disconnect(self):
		pass

class EventHandler:
	def __init__(self):
		pass

	def handle(self):
		pass

class Renderer:
	def __init__(self):
		pass

	def render(self):
		pass

class GameClient:
	def __init__(self):
		self.scr_size = scr_size
        self.fps = fps
        self.gravity = 80.0

        # Init pygame
        pg.init()
        self.scr = pg.display.set_mode(self.scr_size)
        pg.display.set_caption("Tanks")
        self.clock = pg.time.Clock()
        self.actions = EventActions()
        self.key_actions = KeyboardActions()
        
        # Graphics stuff
        self.background_clr = (0, 0, 0)
        self.font_main = pg.font.SysFont('segoeui', 26)

        # Client stuff
		self.event_handler = EventHandler()
		self.world = World()
		self.renderer = Renderer()

	def loop(self):
		self.event_handler.handle()
		self.world.update()
		self.renderer.render()
