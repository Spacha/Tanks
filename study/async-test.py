import asyncio, websockets, json
from time import sleep
import janus

import pygame as pg
import sys

def encode_msg(msg):
    return json.dumps(msg, ensure_ascii=False)
    
def decode_msg(text):
    return json.loads(text)

WIDTH, HEIGHT = 300, 150
FPS = 60

loop = None
another_players = []
running = True

client_id = None

def quit():
    global running
    running = False
    pg.quit()
    #sys.exit()
    #for task in asyncio.all_tasks():
    #    task.cancel()
    #    with suppress(CancelledError):
    #        loop.run_until_complete(task)

def update(action, data, q):
    print("New data.")
    q.put({'type': 'game_activity', 'activity': {
        'type': action, 'value': data}
    })

def request_start_game(q):
    q.put({'type': 'start_game'})

def threaded(recv_queue: janus.SyncQueue[int], send_queue: janus.SyncQueue[int]) -> None:
    '''for i in range(100):
        send_queue.put(i)
    send_queue.join()
    '''
    pg.init()
    clock = pg.time.Clock()
    pg.fastevent.init()
    scr = pg.display.set_mode((WIDTH, HEIGHT))
    font = pg.font.SysFont('segoeui', 26)

    player_pos = 150
    player_max_speed = 100
    player_velocity = 0

    delta = 0

    print("Waiting for the match to start...")
    sleep(1)
    request_start_game(send_queue)

    i = 0
    while running:

        #
        # Handle events
        #
        if not recv_queue.empty():  # poll messages from the socket
            msg = recv_queue.get()
            #print("New message:", msg)
            if msg['type'] == 'game_state':
                #{'type': 'game_state', 'game_state': {'4': 0.0}}
                if str(client_id) in msg['game_state']:
                    player_pos = msg['game_state'][str(client_id)]

        for event in pg.fastevent.get():
            if event.type == pg.QUIT:
                quit()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_q:
                    quit()
                if event.key == pg.K_x:
                    update('shoot', None, send_queue)
                elif event.key == pg.K_LEFT:
                    player_velocity = -player_max_speed
                    update('move', player_velocity, send_queue)
                elif event.key == pg.K_RIGHT:
                    player_velocity = player_max_speed
                    update('move', player_velocity, send_queue)
            elif event.type == pg.KEYUP:
                if event.key in [pg.K_LEFT, pg.K_RIGHT]:
                    player_velocity = 0
                    update('move', player_velocity, send_queue)

        #
        # Update (physics etc.)
        #

        if player_velocity != 0:
            player_pos += delta * player_velocity

        #
        # Render
        #
        scr.fill(( 0 , 0 , 0 ))
        pg.draw.circle(scr, pg.Color('red'), (player_pos, 75), 25)
        text = font.render(f"Pos: ({round(player_pos)}, {0})", True, (255, 255, 255))
        scr.blit(text, text.get_rect())

        for another_player in another_players:
            pg.draw.circle(scr, pg.Color('white'), (another_player, 75), 25)

        delta = clock.tick(FPS) / 1000.0
        pg.display.update()
        i += 1


async def producer(websocket, send_queue: janus.AsyncQueue[int]) -> None:
    '''
    for i in range(100):
        val = await send_queue.get()
        assert val == i
        send_queue.task_done()
    '''
    while running:
        msg = await send_queue.get()
        #await asyncio.sleep(0.25)  # mimic some network latency...
        await websocket.send(encode_msg(msg))
        print('Handled:', msg)

async def consumer(websocket, recv_queue: janus.AsyncQueue[int]):
    global client_id
    count = 0
    seq = 0
    #last_time = time.monotonic()
    #client_id = None
    last_msg_id = None
    
    async for message_raw in websocket:
        count += 1
        msg = decode_msg(message_raw)
        
        if msg['type'] == 'joined':
            client_id = msg['client_id']
            print("Joined. Client ID:", client_id)

        if msg['type'] == 'game_state':
            print("Game state updated.")
            await recv_queue.put(msg)
            #{'type': 'game_state', 'game_state': {'1': 0.0}}



        print("Received:", msg)

async def main() -> None:
    global loop

    uri = "ws://localhost:8765"
    player_name = "Spacha"
    room = "js-room"

    recv_queue: janus.Queue[int] = janus.Queue()
    send_queue: janus.Queue[int] = janus.Queue()
    loop = asyncio.get_running_loop()

    print("Connecting...")
    async with websockets.connect(uri) as websocket:
        print("Connected. Joining...")
        await websocket.send( encode_msg({ 'type': 'join', 'room': room, 'player_name': player_name }) )
        print("Joined.")

        fut = loop.run_in_executor(None, threaded, recv_queue.sync_q, send_queue.sync_q)
        #await producer(websocket, queue.async_q)
        consumer_task = asyncio.ensure_future( consumer(websocket, recv_queue.async_q) )
        producer_task = asyncio.ensure_future( producer(websocket, send_queue.async_q) )
        done = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        await fut

    queue.close()
    await queue.wait_closed()
    print("Connection closed.")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Nicely shutting down ...")
    quit()
else:
    raise
    
'''
import asyncio
import time

queue = asyncio.Queue()

counter = 0
async def listen():
    global counter

    print("Start listen...")

    while True:
        data = await queue.get()
        print("Updated:", data, counter)
        counter += 1

async def update(data):
    print(">>> Putting data")
    #await queue.put(data)

async def main_loop():
    i = 0
    while True:
        print('Handle events')
        if i % 10 == 0:
            await update('somedatahere')
        print('Draw screen')
        # await asyncio.sleep(2)
        await asyncio.sleep(0.5)
        #time.sleep(0.5)
        i += 1

async def main():
    #loop = asyncio.get_event_loop()
    main_task = asyncio.create_task( main_loop() )
    listen_task = asyncio.create_task( listen() )

    await asyncio.wait([main_task, listen_task], return_when=asyncio.FIRST_COMPLETED)

asyncio.run( main() )
'''

#loop = asyncio.get_event_loop()
#loop.create_task(main_loop)
#a = asyncio.ensure_future(listen())
#b = asyncio.ensure_future(main_loop())

# loop.run_until_complete(a)
#task = loop.create_task( main_loop() )
#loop.run_until_complete(task)
'''
from concurrent.futures import ProcessPoolExecutor
if __name__ == "__main__":
    executor = ProcessPoolExecutor(2)
    loop = asyncio.get_event_loop()
    boo = loop.run_in_executor(executor, listen)
    baa = loop.run_in_executor(executor, main_loop)

    loop.run_forever()
'''
