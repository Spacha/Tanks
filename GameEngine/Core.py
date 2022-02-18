from math import degrees
import pygame as pg
import numpy as np
import time
import sys

# Custom events
delete_particle_event = pg.USEREVENT + 1

# Colors
class Color:
    WHITE  = (255,255,255)
    BLACK  = ( 0 , 0 , 0 )

    RED    = (255, 0 , 0 )
    GREEN  = ( 0 ,255, 0 )
    BLUE   = ( 0 , 0 ,255)
    YELLOW = (255,255, 0 )

"""
    Simple class representing a 2D vector like position and velocity.
"""
class Vector():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def as_tuple(self):
        return (self.x, self.y)

    def __mul__(self, other):
        if type(other) in [int, float]:
            return Vector(self.x * other, self.y * other)
        else:
            raise Exception("Multiplication with Vector and that not defined.")

    def __add__(self, other):
        if type(other) is Vector:
            return Vector(self.x + other.x, self.y + other.y)
        else:
            raise Exception("Addition with Vector and that not defined.")


class EventActions:
    def __init__(self):
        # a dictionary containing action for each event registered
        self.actions = {}

    def register(self, event, callback):
        """
            Register a new with a callback
        """
        self.actions[event] = callback

    def handle(self, events):
        """
            Handle a list of events.
        """
        for event in events:
            try:
                # call the callback if found
                self.actions[event.type](event)
                print(event)
            except KeyError:
                continue

class KeyboardActions:
    def __init__(self):
        # a dictionary containing action for each event registered
        self.actions_down = {}
        self.actions_up = {}

    def down(self, key, action):
        # does not handle mod keys -> need another method for that (ctrlDown...)
        self.actions_down[key] = action

    def up(self, key, action):
        # dos not handle mod keys -> need another method for that (ctrlDown...)
        self.actions_up[key] = action

    def handle_down(self, code, key, mod):
        # does not (yet) handle mod keys
        try:
            self.actions_down[key]()
        except KeyError:
            return

    def handle_up(self, key, mod):
        # does not (yet) handle mod keys
        try:
            self.actions_up[key]()
        except KeyError:
            return

"""
    This class takes care of game mechanics including the physics.
"""
class Game:
    def __init__(self, scr_size, fps):
        self.scr_size = scr_size
        self.fps = fps
        self.gravity = 4.0

        # Init pygame
        pg.init()
        self.scr = pg.display.set_mode(self.scr_size)
        pg.display.set_caption("A Slope Game!")
        self.clock = pg.time.Clock()
        self.actions = EventActions()
        self.key_actions = KeyboardActions()
        
        # Graphics stuff
        self.background_clr = Color.BLACK
        self.font_main = pg.font.SysFont('segoeui', 26)

        # World settings
        self.ground = None
        self.objects = {}
        self.particle_labels = []
        self._pending_objects = []
        self._pending_particles = []
        self._pending_delete = []

        self.last_delta = self.fps

        # initialize the actual game
        self.register_actions()
        self.running = True

    def register_actions(self):
        """
            Event types:
                QUIT            None
                ACTIVEEVENT     gain, state
                KEYDOWN         unicode, key, mod
                KEYUP           key, mod
                MOUSEMOTION     pos, rel, buttons
                MOUSEBUTTONUP   pos, button
                MOUSEBUTTONDOWN pos, button
                JOYAXISMOTION   joy, axis, value
                JOYBALLMOTION   joy, ball, rel
                JOYHATMOTION    joy, hat, value
                JOYBUTTONUP     joy, button
                JOYBUTTONDOWN   joy, button
                VIDEORESIZE     size, w, h
                VIDEOEXPOSE     None
                USEREVENT       Code
        """
        self.actions.register(pg.QUIT,               self.exit)
        self.actions.register(pg.KEYDOWN,            self.handle_keydown)
        self.actions.register(pg.KEYUP,              self.handle_keyup)
        self.actions.register(pg.MOUSEMOTION,        self.handle_mousemove)
        self.actions.register(pg.MOUSEBUTTONDOWN,    self.handle_mousedown)
        self.actions.register(pg.MOUSEBUTTONUP,      self.handle_mouseup)
        self.actions.register(delete_particle_event, self.delete_old_particles)
        '''
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
        '''

    def handle_events(self):
        """
            Handles the events, such as user input and acts accordingly.
        """
        events = pg.event.get()
        self.actions.handle(events)

    def update(self):
        """
            This is called once per frame. Takes care of updating the simple "physics".
        """
        # first, delete objects that were marked to be deleted last loop
        self.delete_old_particles(None)
        self.delete_pending_objects()
        self.add_pending_particles()
        self.add_pending_objects()

        for label, obj in self.objects.items():
            obj.update(self.last_delta) # start by calculating the new position

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
        for label, obj in self.objects.items():
            obj.draw(self.scr)

        # draw the top layer (e.g. UI elements)
        x,y,m = 0,10,10
        x,y = self.ui_write(" A Slope Game! ", 10, y+m)

        player = self.get_object('Player')
        if player is not None:
            x,y = self.ui_write(" On ground: {} ".format("Yes" if player.on_ground else "No"), 10, y+m)
            x,y = self.ui_write(" Barrel angle: {}°".format(int(degrees(player.barrel_angle))), 10, y+m)

        self.ui_write(" FPS: {} ".format(self.actual_fps()), 10, y+m)

    def get_object(self, label):
        """
            Get an object by label. If not found, None is returned.
        """
        try:
            return self.objects[label]
        except KeyError:
            return None


    def ui_write(self, text_str, x, y):
        """
            A small helper to write UI text on the screen.
            Returns the x and y coordinates of the bottom right
            corner if the text to help write multiple rows/columns.
        """
        text = self.font_main.render(text_str, True, Color.BLACK, Color.WHITE) 
        text_rect = text.get_rect()
        text_rect.left = x
        text_rect.top  = y

        self.scr.blit(text, text_rect)

        return (text_rect.right, text_rect.bottom)

    def tick(self):
        self.clock.tick(self.fps)
        self.last_delta = self.clock.get_time() / 1000.0

    def get_ticks(self):
        """
            Returns seconds since game started (pg.init).
        """
        return pg.time.get_ticks() / 1000.0

    def time(self):
        """
            Returns absolute time in seconds.
        """
        return time.time()

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
            Overwrites the old item if there is one with the same label.
            If the object has no label, generates a unique label for it.
        """
        if obj.label is None:
            obj.label = self.generate_label()
        #self.objects[obj.label] = obj
        self._pending_objects.append(obj)

    def add_particle(self, particle):
        self._pending_particles.append(particle)

    def delete_obj(self, obj):
        """
            Marks a a game object to be deleted from the game.
        """
        self._pending_delete.append(obj.label)

    def add_pending_objects(self):
        for obj in self._pending_objects:
            self.objects[obj.label] = obj
        self._pending_objects = []

    def add_pending_particles(self):
        for particle in self._pending_particles:
            self.add_obj(particle)
            self.particle_labels.append(particle.label)

            # set a timer to destroy the particle after its lifetime
            # pg.time.set_timer(delete_particle_event, int(particle.lifetime * 1000))
        self._pending_particles = []

    def delete_pending_objects(self):
        """
            Deletes the pending objects and clears the list.
        """
        for label in self._pending_delete:
            try:
                del self.objects[label]
            except KeyError:
                print("Unkown object to be deleted: ", label)
        self._pending_delete = []

    def generate_label(self):
        """
            Generates a unique label.
        """
        return "anon-" + str(hash(time.time()))

    def on_screen(self, obj):
        """
            Return true if the object is on the screen.
            NOTE: Only the object position counts! Not width!
        """
        return (0 <= obj.position.x <= self.scr_size[0] and
                0 <= obj.position.y <= self.scr_size[1])

    def actual_fps(self):
        return round(1/self.last_delta, 2)

    # Event handlers

    def delete_old_particles(self, event):
        for label in self.particle_labels:
            try:
                obj = self.objects[label]
            except KeyError:
                continue
            if obj.has_life_ended():
                # Delete label using list comprehension: https://stackoverflow.com/a/5746071
                self.particles = [p for p in self.particle_labels if not label]
                self.delete_obj(obj)

    def handle_keydown(self, event):
        code = event.unicode
        key = event.key
        mod = event.mod
        self.key_actions.handle_down(code, key, mod)

    def handle_keyup(self, event):
        key = event.key
        mod = event.mod
        self.key_actions.handle_up(key, mod)

    def handle_mousemove(self, event):
        pos = event.pos
        rel = event.rel
        buttons = event.buttons
        # self.mouse.actions.moved(pos, rel, buttons)

    def handle_mousedown(self, event):
        pos = event.pos
        buttons = event.button
        # self.mouse.actions.down(pos, button)

    def handle_mouseup(self, event):
        pos = event.pos
        buttons = event.button
        # self.mouse.actions.up(pos, button)

    def exit(self, event = None):
        self.running = False


"""
    This is a class that is the basis of a game object. Use
    this as a parent when creating new types of game objects.
"""
class GameObject():
    def __init__(self, label = None, static = False):
        self.position = Vector(0.0, 0.0)
        self.velocity = Vector(0.0, 0.0)
        self.label = label
        self.static = static

        self.width = 0
        self.height = 0

        self.on_ground = False
        self.debug = False

    def update(self, delta):
        """
            The game calls this method. This takes care of updating
            all the game-object-specific physics.
            Last frame time is given in @delta and must
            be used in physics calculations.
        """
        if not self.static:
            self.position.x = self.position.x + self.velocity.x * delta
            self.position.y = self.position.y + self.velocity.y * delta

    def bottom(self):
        """
            Return the position of the bottom of the object
            (used in ground collision detection).
        """
        return int(self.position.y + self.height)

    def toggle_debug(self):
        self.debug = not self.debug
