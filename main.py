import asyncio
import threading
import time
import tkinter as tk

import utils
import message_server
from message import Message
from user import Users
from app import App

# this is the most cleanest AND the dirtiest part of the program
# running tkinter alongside asyncio without errors 💀

def setup_tkinter():
    root = tk.Tk()
    myapp = App(root)
    myapp.bind("exit", root.destroy, '+')
    root.mainloop()
    message_server.exit()

async def async_main():
    message_server_main_task = asyncio.create_task(message_server.main())
    await message_server_main_task

def main():
    asyncio_thread = threading.Thread(target=asyncio.run, args=[async_main()])
    asyncio_thread.daemon = True
    asyncio_thread.start()
    setup_tkinter()
    
    asyncio_thread.join()


if __name__ == "__main__":
    main()