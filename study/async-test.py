import asyncio
import janus
from time import sleep

import pygame as pg
import sys

WIDTH, HEIGHT = 300, 150
FPS = 60

running = True

def quit():
    global running
    running = False
    pg.quit()
    sys.exit()

def update(data, q):
    print("New data.")
    q.put(data)

def threaded(sync_q: janus.SyncQueue[int]) -> None:
    '''for i in range(100):
        sync_q.put(i)
    sync_q.join()
    '''
    pg.init()
    clock = pg.time.Clock()
    pg.fastevent.init()
    scr = pg.display.set_mode((WIDTH, HEIGHT))

    i = 0
    while running:
        for event in pg.fastevent.get():
            if event.type == pg.QUIT:
                quit()
            elif event.type == pg.KEYDOWN:
                print("keydown")
                if event.key == pg.K_x:
                    print("x")
                    update('shoot', sync_q)
        scr.fill(( 0 , 0 , 0 ))

        '''
        if i % 10 == 9:
            update('shitti-' + str(i), sync_q)
        '''

        clock.tick(FPS)
        pg.display.update()
        i += 1


async def async_listen(async_q: janus.AsyncQueue[int]) -> None:
    '''
    for i in range(100):
        val = await async_q.get()
        assert val == i
        async_q.task_done()
    '''
    while running:
        val = await async_q.get()
        await asyncio.sleep(1)
        print('Handled:', val)

async def main() -> None:
    queue: janus.Queue[int] = janus.Queue()
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(None, threaded, queue.sync_q)
    await async_listen(queue.async_q)
    await fut
    queue.close()
    await queue.wait_closed()


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
