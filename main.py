import asyncio
import os
import threading
import tkinter as tk

import message_server
from app import App
from config import ICON_PATH

# Recommended Python version 3.13.1
# Min Python version: 3.12
# Required modules: asyncio, threading, tkinter, cryptography, shlex, json, socket, queue, copy, time, unicodedata, secrets, typing, os, uuid, argparse

# This is THE MAIN file for the whole app
# Run this file with `python3 main.py` (on Linux) or `python main.py` (on Windows)
# Do not run any other file unless you absolutely know what you're doing

def setup_dir():
    if not os.path.exists('./data/'):
        os.makedirs('./data')
    if not os.path.exists('./user_scripts/'):
        os.makedirs('./user_scripts')

def setup_tkinter():
    root = tk.Tk()

    icon = tk.PhotoImage(file=ICON_PATH)
    root.iconphoto(True, icon)

    myapp = App(root)

    def destroy(e: object):
        root.destroy()

    myapp.bind("exit", destroy, '+')
    tk.mainloop()
    message_server.exit()

async def async_main():
    message_server_main_task = asyncio.create_task(message_server.main())
    await message_server_main_task

# this is the most cleanest AND the dirtiest part of the program
# running tkinter alongside asyncio without errors 💀

def main():
    setup_dir()
    asyncio_thread = threading.Thread(target=asyncio.run, args=[async_main()])
    asyncio_thread.daemon = True
    asyncio_thread.start()
    setup_tkinter()
    
    asyncio_thread.join()


if __name__ == "__main__":
    main()