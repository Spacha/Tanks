from typing import *
from dataclasses import dataclass, field
import asyncio, websockets, json, time
from collections import defaultdict

# Source: https://mortoray.com/2020/12/06/high-throughput-game-message-server-with-python-websockets/

#sys.path.append('../server')
#from escape.live_game_state import LiveGameState

def encode_msg(msg: Dict) -> str:
    return json.dumps(msg, ensure_ascii=False)
    
def decode_msg(text: str) -> Dict:
    return json.loads(text)


@dataclass
class Client:
    socket:       Any # What type?
    id:           int
    disconnected: bool = False
    
@dataclass
class Room:
    key:         str
    clients:     Dict[int, Client] = field(default_factory=dict)
    new_clients: List[Client] = field(default_factory=list)
    msg_id:      int = 0
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    listening:   bool = False
    future:      Any = None # What Type?

    def client_count(self) -> int:
        return len([c.id for c in self.clients.values() if not c.disconnected])

client_id_count = 0

rooms: Dict[str, Room] = {}
    

# Used to get a basic idea of throughput
class Stats:
    def __init__(self, name):
        self._name = name
        self._count = 0
        self._time = time.monotonic()

    def incr(self, amount = 1):
        self._count += amount
        if self._count > 5000:
            end_time = time.monotonic()
            print( f'{self._name} {self._count / (end_time-self._time)}/s' )
            self._count = 0
            self._time = end_time

async def listen_room(room):
    if room.listening:
        raise Exception(f'Already listening to {room.key}')
        
    room.listening = True
    print(f'Listen Room {room.key}')
    stats = Stats(f'Outgoing {room.key}')

    while True:
        qevent = await room.event_queue.get()
        if qevent == None:
            break
            
        # Add any new clients that have shown up, this handler must control this
        # to avoid it happening inside the loop below
        if len(room.new_clients) > 0:
            for client in room.new_clients:
                room.clients[client.id] = client
            room.new_clients = []
        
        # In my game I'll track IDs in Redis, to survive unexpected failures.
        # The messages will also be pushed there, to be picked up by another
        # process for DB storage.
        room.msg_id += 1
        qevent['msg_id'] = room.msg_id
        
        count = 0
        disconnected: List[int] = []
        for client in room.clients.values():
            if client.disconnected:
                disconnected.append(client.id)
                continue
            count += 1
            
            # There's likely some asyncio technique to do this in parallel
            try:
                await client.socket.send(encode_msg(qevent))
            except websockets.ConnectionClosed:
                print("Lost client in send")
                client.disconnected = True
                # Hoping incoming will detect disconnected as well
            
        stats.incr(count)
        
        # Remove clients that aren't there anymore. I don't really need this in
        # my game, but it's good to not let long-lived rooms build-up cruft.
        for d in disconnected:
            # Check again since they may have reconnected in other loop
            if room.clients[d]:
                del room.clients[d]
            
    print(f'Unlisten Room {room.key}')
    room.listening = False


async def listen_socket(websocket, path):
    global rooms, client_id_count
    print("connect", path)
    client_id_count += 1
    room: Optional[Room] = None
    client = Client(id=client_id_count, socket=websocket)
    
    stats = Stats('Incoming')
    try:
        async for message_raw in websocket:
            message = decode_msg(message_raw)
            if message['type'] == 'join':
                # Get/create room
                room_key = message['room']
                if not room_key in rooms:
                    room = Room(key=room_key)
                    rooms[room_key] = room
                    
                    room.future = asyncio.ensure_future(listen_room(room))
                else:
                    room = rooms[room_key]
                    
                # Add client to the room
                room.new_clients.append(client)
                
                # Tell the client which id they are.
                await websocket.send(encode_msg({
                    'type': 'joined',
                    'client_id': client.id
                }))
                
            elif room:
                # Identify message and pass it off to the room queue
                message['client_id'] = client.id
                await room.event_queue.put(message)
            else:
                # Behave as trivial echo server if not in room (will be removed
                # in my final version)
                #await websocket.send(encode_msg(message))
                await websocket.send(encode_msg({"kikkeli": "kokkeli"}))
            stats.incr()
    except websockets.ConnectionClosed:
        pass
    except Exception as e:
        # In case something else happens we want to ditch this client. This
        # won't come from websockets, but likely the code above, like
        # having a broken JSON message.
        print(e)
        pass
    
    # Only mark disconnected for queue loop on clients isn't broken
    client.disconnected = True
    if room is not None:
        # Though if zero we can kill the listener and clean up fully
        if room.client_count() == 0:
            await room.event_queue.put(None)
            del rooms[room.key]
            await room.future
            print(f"Cleaned Room {room.key}")
            
    print("disconnect", rooms)


def main() -> None:
    start_server = websockets.serve(listen_socket, "localhost", 8765, ping_interval=5, ping_timeout=5)

    asyncio.get_event_loop().run_until_complete(start_server)

    asyncio.get_event_loop().run_forever()

    
main()