# Tanks

* Idea:
	* 2 teams, 2-4 players. Players take turns and try to destroy the tanks of the other team.
	* 2d, view from the side
	* the environment is (partially) destructable
	* each turn, the player has a certain amount of action points available:
		* can be used for movement (left/right) or shooting
* Concept
	* A match could consist of, e.g. 10 games. Each game would yield each player
	  a certain amount of gold based on if the team won, how many kills did
	  the player get, some special challenges (e.g. double kill)
		* Can the tanks be upgraded mid-game? Maybe.
	* Environment
		* Various materials:
			* Hardness: how easily it is destroyed
			* Texture: what it looks like
			* Extra: flowing material like sand or water (would probably require Box2D or something)
		* There can be random items in the map that give some effects (health, action, special ammo)
	* Tanks
		* can be upgraded, different ammunition
			* cluster shells, large explosion radius, ...
		* ballistic ammunition - gravity affects heavily
	* Playing
		* Left/right to move
		* Numbers 1-6 to select ammunition
		* Up/down to adjust barrel angle
		* Spacebar to shoot

* Architecture
	* Client-server
	* Client: Render UI, communicate with the server
	* Server: Give turns to clients (players), keep track of everything
* Communication
	* Full-duplex, websockets
	* Data
		* Change barrel ANGLE
		* Change tank POSITION
		* SHOOT (which AMMUNITION)
		* 
* Graphics
	* Pygame 2
* Map:
	* Stored as an array of "pixels". Could be drawn using paint, for example and exported as a bmp, which is then converted to a map.
	* Players' starting positions are put on the map

* Shooting:
	1. Player A shoots (angle (-45..+90), heading (left/right), ammunition (id), power (0-100))
	2. Each client calculates the trajectory independently
		* the server could also calculate who take damage and how much, which can then be sued to confirm the shots


* In a game:
	* Server:
		* Listen inputs from all players all the time. Even if a player is not playing at the moment, they can move their barrel etc.
		  Distribute the changes to all players.
		* Give a turn for player A - this unlocks the player's ability to move and shoot
		* As the player damages other players, update the game state
