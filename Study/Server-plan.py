#!/usr/bin/env python

import asyncio
import websockets

class GameStateManager:
	def __init__(self):
		pass

class DatabaseManager:
	def __init__(self):
		pass

class ConnectionManager:
	def __init__(self):
		pass

	def start(self, port):
		print("Starting server at {}...".format(port))
		pass


class Server:
	def __init__(self):
		self.state = GameStateManager()
		self.database = DatabaseManager()
		self.connection = ConnectionManager()

		self.connection.start(8765)

server = Server()
