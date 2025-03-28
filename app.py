import tkinter as tk
import tkinter.font
import tkinter.scrolledtext
import threading
import queue
import time

import utils
import message_server
from message import Message
from message_packet import MessagePacket
from user import User, Users

# This module is entirely for the UI and its functions
# NOTE: Try to minimize the access to other modules' variables and methods.

# TODO: Implement RichText

BG_0 = '#2a2a2c'
BG_1 = '#3f3f4a'
BUTTON_BG_0 = '#30303a'
BUTTON_BG_1 = '#222'
BUTTON_ACTIVE = '#11e'
SEND_BUTTON_BG_0 = '#7777cc'
SEND_BUTTON_BG_1 = '#4343bb'
FONT = 'ariel 10'

class App(tk.Frame):
    message_targets = []

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
        self.chatlog.configure(state="disabled", cursor='arrow')
        self.chatlog.vbar.configure(bg=BG_1)
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

        def listen_to_messages():
            self.after(500, listen_to_messages)
            message = message_server.pull_inbound_message()
            if message:
                self.message_queue.put(message)
                self.event_generate("<<message_recieved>>")

        self.bind("<<message_recieved>>", self._on_message_recieved, '')
        self.chatlog.bind('<1>', lambda e: self.chatlog.focus()) # enable highlighting on chatlog

        listen_to_messages()
    # TODO: Make this actually send messages to peers
    def send_message(self, e=None):
        text: str = self.entry.get()
        if text.isspace() or len(text) < 1:
            return
        self.entry.delete(first=0, last=len(text))
        msg = MessagePacket(Message('<localhost>', text), App.message_targets)
        message_server.outbound_message_queue.put(msg)
    
    def _on_message_recieved(self, e=None):
        packet = self.message_queue.get(block=False)
        if packet:
            message = packet.message
            username = message.get_author_username()
            if username == "<localhost>":
                username = utils.get_current_username()
            formatted_text = username + ": " + message.get_text_content()
            self.chatlog.configure(state="normal")
            self.chatlog.insert(tk.END, formatted_text + '\n')
            self.chatlog.configure(state="disabled")
            print(formatted_text)


class UserList(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(bg=BG_0, padx=4, pady=4)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.label = tk.Label(self, text="Online Users", bg=BG_0, fg='#fff')
        self.label.grid(row=0, column=0, pady=4, sticky='new')

        self.user_list = tk.Frame(self, bg=BG_1, padx=2, pady=2)
        self.user_list.columnconfigure(0, weight=1)
        self.user_list.grid(row=1, column=0, sticky='news')

        self._user_buttons: dict[User, tk.Button] = {}
        self.update_list()
    def update_list(self):
        self.after(200, self.update_list)
        for user in Users.get_all_users():
            if user not in self._user_buttons and user.is_active():
                self.add_user(user)
        for user in self._user_buttons.copy():
            if not user.is_active():
                self.remove_user(user)
    def add_user(self, user: User):
        username = user.get_username()
        button = UserListButton(self.user_list, text=username)
        self._user_buttons[user] = button
        button.pack(side='top', fill='x')
    def remove_user(self, user: User):
        self._user_buttons.pop(user).destroy()

class UserListButton(tk.Button):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.configure(bg=BUTTON_BG_0, fg='#fff', border=0, anchor='w', command=self._on_command)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self._selected = False
        self._hover = False
    def _update(self):
        if self._selected:
            self.configure(bg=BUTTON_ACTIVE)
        elif self._hover:
            self.configure(bg=BUTTON_BG_1)
        else:
            self.configure(bg=BUTTON_BG_0)
    def _on_enter(self, e):
        self._hover = True
        self._update()
    def _on_leave(self, e):
        self._hover = False
        self._update()
    def _on_command(self):
        name = self["text"]
        if name in App.message_targets:
            App.message_targets.remove(name)
            self._selected = False
        else:
            App.message_targets.append(name)
            self._selected = True
        self._update()


class MessageSendButton(tk.Button):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.configure(bg=SEND_BUTTON_BG_0, fg='#fff', border=0, anchor='center', text='> Send >')
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    def _on_enter(self, e):
        self.configure(bg=SEND_BUTTON_BG_1)
    def _on_leave(self, e):
        self.configure(bg=SEND_BUTTON_BG_0)

#TODO: Implement this
class ChatBox(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = canvas = tk.Canvas(self)
        canvas.grid(row=0, column=0, sticky="news")

        self.scrollbar = scrollbar = tk.Scrollbar(self, bg=BG_1, orient=tk.VERTICAL, command=self._on_scroll_ycommand)
        scrollbar.grid(row=0, column=1, sticky="new")
    def add_message(message: Message):
        pass
    def _on_mouse_enter(self, e):
        pass
    def _on_scroll_ycommand(self, e):
        pass

# for testing the UI without a real message server
def main():
    root = tk.Tk()
    app = App(root)
    app.bind("exit", root.destroy, '+')
    root.mainloop()

if __name__ == "__main__":
    main()