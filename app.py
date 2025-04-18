import tkinter as tk
import tkinter.font
import tkinter.scrolledtext
import queue
from typing import Any

import utils
import message_server
import commands
from message import Message
from message_packet import MessagePacket
from user import User, Users
from config import *

# This module is entirely for the UI and its functions

# TODO: Implement RichText

BG_0 = '#2a2a2c'
BG_1 = '#3f3f4a'
BUTTON_BG_0 = '#30303a'
BUTTON_BG_1 = '#222'
BUTTON_ACTIVE = '#11e'
SEND_BUTTON_BG_0 = '#7777cc'
SEND_BUTTON_BG_1 = '#4343bb'
FONT = 'ariel 10'

MSPT = int(1000/TPS) # miliseconds per tick

should_exit = False

def exit_app():
    global should_exit
    should_exit = True

class App(tk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self['bg'] = BG_0
        master.title("MoResChat")
        self.pack(ipadx=30, ipady=30, fill="both", expand=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.chatlog = tkinter.scrolledtext.ScrolledText(self)
        self.chatlog['bg'] = BG_1
        self.chatlog['fg'] = '#ffffff'
        self.chatlog['font'] = FONT
        self.chatlog['relief'] = "flat"
        self.chatlog.configure(state="disabled", cursor='arrow', wrap=tk.WORD, font=('Arial', 10))
        self.chatlog.vbar.configure(bg=BG_1)
        self.chatlog.tag_configure('system', foreground='#fe0', font=('Arial', 10, 'bold'))
        self.chatlog.tag_configure('user', foreground='#2de', font=('Arial', 10, 'bold'))
        self.chatlog.tag_configure('localuser', foreground='#d5e', font=('Arial', 10, 'bold'))
        self.chatlog.grid(column=0, row=0, padx=8, pady=8, sticky="news")

        self.text_input_frame = tk.Frame(self)
        self.text_input_frame['bg'] = self['bg']
        self.text_input_frame.grid(column=0, row=1, sticky='we')
        self.text_input_frame.columnconfigure(0, weight=1)

        self.entry = tk.Entry(self.text_input_frame, relief='flat', highlightthickness=1, highlightcolor='#3333ff', highlightbackground=BG_0, insertbackground='white', insertwidth=1)
        self.entry['bg'] = BG_1
        self.entry['fg'] = '#f0f0f0'
        self.entry.grid(column=0, row=0, padx=8, pady=8, ipadx=6, ipady=6, sticky="ew")

        self.button = MessageSendButton(self.text_input_frame, command=self.send_message)
        self.button.grid(column=1, row=0, padx=10, pady=10, sticky='news')

        self.user_list = UserList(self)
        self.user_list.grid(row=0, column=1, rowspan=2, sticky='news')

        # dirty event stuff; but if it works, it works

        self.message_queue: queue.SimpleQueue[MessagePacket] = queue.SimpleQueue()

        # send the initial system message
        if INITIAL_SYSTEM_MESSAGE and len(INITIAL_SYSTEM_MESSAGE) > 0:
            message_server.outbound_message_queue.put(MessagePacket(Message('<system>', INITIAL_SYSTEM_MESSAGE), ['<localhost>']))

        def listen_to_messages():
            message = message_server.pull_inbound_message()
            if message:
                self.message_queue.put(message)
                self.after(MSPT, self.event_generate, "<<message_recieved>>")
        
        def tick():
            self.after(MSPT, tick)
            self.after(2, listen_to_messages)
            if should_exit:
                master.destroy()

        self.bind("<<message_recieved>>", self._on_message_recieved, '+')
        self.chatlog.bind('<1>', lambda _: self.chatlog.focus()) # enable highlighting on chatlog

        tick()
    # TODO: Make this actually send messages to peers
    def send_message(self):
        text: str = self.entry.get()
        if text.isspace() or len(text) < 1:
            return
        self.entry.delete(first=0, last=len(text))
        if commands.run_command(text):
            pass
        else:
            msg = MessagePacket(Message('<localhost>', text), self.user_list.get_selected_usernames())
            message_server.outbound_message_queue.put(msg)
    
    def _on_message_recieved(self, e: object):
        packet = self.message_queue.get()
        if packet:
            message = packet.message
            username = message.get_author_username()
            local = False
            if username == "<localhost>":
                username = utils.get_current_username()
                local = True
            elif username == "<system>":
                local = True
            if username:
                formatted_text = message.get_text_content()
                formatted_text = formatted_text.replace('\033', "ESC")
                formatted_text = formatted_text.replace('\r', "CR")
                formatted_text = formatted_text.replace('\f', "FF")
                formatted_text = formatted_text.replace('\177', "DEL")
                formatted_text = formatted_text.replace('<system>', "<<system>>")
                self.chatlog.configure(state="normal")
                if username == "<system>":
                    self.chatlog.insert(tk.END, "<system>: ", 'system')
                elif local:
                    self.chatlog.insert(tk.END, username + ": ", 'localuser')
                else:
                    self.chatlog.insert(tk.END, username + ": ", 'user')
                self.chatlog.insert(tk.END, formatted_text + '\n')
                self.chatlog.configure(state="disabled")

class UserList(tk.Frame):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.configure(bg=BG_0, padx=4, pady=4)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.label = tk.Label(self, text="Online Users", bg=BG_0, fg='#fff')
        self.label.grid(row=0, column=0, pady=4, sticky='new')

        self.user_list = tk.Frame(self, bg=BG_1, padx=2, pady=2)
        self.user_list.columnconfigure(0, weight=1)
        self.user_list.grid(row=1, column=0, sticky='news')

        self._user_buttons: dict[User, UserListButton] = {}
        self.update()
    def update(self):
        self.after(MSPT, self.update)
        users = Users.get_all_users()
        for user in users:
            if user not in self._user_buttons and user.is_active():
                self.add_user(user)
    def add_user(self, user: User):
        username = user.get_username()
        button = UserListButton(self.user_list, user=user, text=username)
        self._user_buttons[user] = button
        button.pack(side='top', fill='x')
    def get_selected_users(self):
        result: list[User] = []
        for user in self._user_buttons:
            button = self._user_buttons[user]
            if button.is_selected():
                result.append(user)
        return result
    def get_selected_usernames(self):
        result: list[str] = []
        for user in self.get_selected_users():
            result.append(user.get_username())
        return result

class UserListButton(tk.Button):
    def __init__(self, *args: Any, user: User, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.configure(bg=BUTTON_BG_0, fg='#fff', border=0, anchor='w', command=self._on_command, text=user.get_username())
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self._hover = False
        self._selected = False
        self.user = user
        self.update()
    def is_selected(self):
        return self._selected
    def _get_username(self):
        return self.user.get_username()
    def _on_enter(self, e: object):
        self._hover = True
    def _on_leave(self, e: object):
        self._hover = False
    def _on_command(self):
        self._selected = not self._selected
    def __lt__(self, other: object):
        if not isinstance(other, UserListButton):
            raise NotImplemented
        return self._get_username() < other._get_username()
    def update(self):
        self.after(MSPT, self.update)
        if self._selected:
            self.configure(bg=BUTTON_ACTIVE)
        elif self._hover:
            self.configure(bg=BUTTON_BG_1)
        else:
            self.configure(bg=BUTTON_BG_0)
        if self.user.is_active():
            self.configure(fg='#fff', text=self._get_username())
        else:
            self.configure(fg='#aaa', text=self._get_username() + " (Inactive)")

class MessageSendButton(tk.Button):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.configure(bg=SEND_BUTTON_BG_0, fg='#fff', border=0, anchor='center', text='> Send >')
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    def _on_enter(self, e: object) -> None:
        self.configure(bg=SEND_BUTTON_BG_1)
    def _on_leave(self, e: object) -> None:
        self.configure(bg=SEND_BUTTON_BG_0)

#TODO: Implement these
#TODO: RichText/Markdown, Image Attachments, Image Embeds
class ChatBox(tk.Frame):
    def __init__(self, master: tk.Frame):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = canvas = tk.Canvas(self)
        canvas.grid(row=0, column=0, sticky="news")

        self.scrollbar = scrollbar = tk.Scrollbar(self, bg=BG_1, orient=tk.VERTICAL, command=self._on_scroll_ycommand)
        scrollbar.grid(row=0, column=1, sticky="new")

        self.message_frames: list[MessageFrame] = []
    def add_message(self, message: Message) -> None:
        pass
    def _on_mouse_enter(self, e: object) -> None:
        pass
    def _on_scroll_ycommand(self, e: object) -> None:
        pass

class MessageFrame(tk.Frame):
    pass

class MessageText(tk.Text):
    pass

class MultiLineCodeBlock(tk.Text):
    pass