import tkinter as tk
import tkinter.font
import tkinter.scrolledtext
import platform
import queue
import subprocess
from PIL import Image, ImageTk
from typing import Any
from tkinter import StringVar, BooleanVar, font, filedialog

import PIL.Image

import utils
import message_server
import commands
import markdown
from attachment import Attachment
from message import Message
from message_packet import MessagePacket
from user import User, Users
from config import *

# This module is entirely for the UI and its functions
# TODO: Implement RichText

MSPT = int(1000/TPS) # miliseconds per tick

should_exit = False

def exit_app():
    global should_exit
    should_exit = True

class App(tk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)

        self.var_bg0 = utils.bind_variable_to_setting(tk.StringVar(), 'theme.background.color0', '#2a2a2c')
        self.var_bg1 = utils.bind_variable_to_setting(tk.StringVar(), 'theme.background.color1', '#3f3f4a')
        self.var_font = utils.bind_variable_to_setting(tk.StringVar(), 'theme.font', 'ariel 10')
        self.var_fg = utils.bind_variable_to_setting(tk.StringVar(), 'theme.foreground', '#fff')
        self.var_input_bar_highlight_color = utils.bind_variable_to_setting(tk.StringVar(), 'theme.chatInputBar.highlight.color', '#33f')
        self.var_input_bar_insert_bg = utils.bind_variable_to_setting(tk.StringVar(), 'theme.chatInputBar.insert.background', '#fff')

        master.title("MoResChat")
        self.pack(ipadx=30, ipady=30, fill="both", expand=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.chatlog = tkinter.scrolledtext.ScrolledText(self, background=self.var_bg1.get(), foreground=self.var_fg.get(), font=self.var_font.get())
        self.chatlog['relief'] = "flat"
        self.chatlog.configure(state="disabled", cursor='arrow', wrap=tk.WORD)

        # user highlighting
        self.chatlog.tag_configure('system', foreground='#fe0', font=('Arial', 10, 'bold'))
        self.chatlog.tag_configure('user', foreground='#2de', font=('Arial', 10, 'bold'))
        self.chatlog.tag_configure('localuser', foreground='#d5e', font=('Arial', 10, 'bold'))
        self.chatlog.tag_configure('attachment_info', foreground='#888', font=('Arial', 10, 'italic'))

        # markdown
        fonts = {
        'header1': font.Font(family='Arial', size=18, weight='bold'),
        'header2': font.Font(family='Arial', size=14, weight='bold'),
        'header3': font.Font(family='Arial', size=12, weight='bold'),
        'subtext': font.Font(family='Arial', size=8),
        'underline+bold+italics': font.Font(family='Arial', size=10, weight='bold', slant='italic', underline=True),
        'underline+bold': font.Font(family='Arial', size=10, weight='bold', underline=True),
        'underline+italics': font.Font(family='Arial', size=10, slant='italic', underline=True),
        'bold+italics': font.Font(family='Arial', size=10, weight='bold', slant='italic'),
        'multiline_codeblock': font.Font(family='Consolas', size=10),
        'bold': font.Font(family='Arial', size=10, weight='bold'),
        'strikethrough': font.Font(family='Arial', size=10, overstrike=True),
        'underline': font.Font(family='Arial', size=10, underline=True),
        'codeblock': font.Font(family='Consolas', size=10),
        'italics': font.Font(family='Arial', size=10, slant='italic'),
        }

        self.chatlog.tag_configure('normal', font=('Arial', 10))
        self.chatlog.tag_configure('header1', font=fonts['header1'])
        self.chatlog.tag_configure('header2', font=fonts['header2'])
        self.chatlog.tag_configure('header3', font=fonts['header3'])
        self.chatlog.tag_configure('subtext', font=fonts['subtext'], foreground=utils.get_setting('theme.markdown.subtext.foreground', '#999'))
        self.chatlog.tag_configure('underline+bold+italics', font=fonts['underline+bold+italics'])
        self.chatlog.tag_configure('underline+bold', font=fonts['underline+bold'])
        self.chatlog.tag_configure('underline+italics', font=fonts['underline+italics'])
        self.chatlog.tag_configure('bold+italics', font=fonts['bold+italics'])
        self.chatlog.tag_configure('multiline_codeblock', font=fonts['multiline_codeblock'], background=utils.get_setting('theme.markdown.codeblock.background', '#444'))
        self.chatlog.tag_configure('bold', font=fonts['bold'])
        self.chatlog.tag_configure('strikethrough', font=fonts['strikethrough'])
        self.chatlog.tag_configure('underline', font=fonts['underline'])
        self.chatlog.tag_configure('codeblock', font=fonts['codeblock'], background=utils.get_setting('theme.markdown.codeblock.background', '#444'))
        self.chatlog.tag_configure('italics', font=fonts['italics'])

        self.chatlog.grid(column=0, row=0, padx=8, pady=8, sticky="news")

        self.chat_input_frame = tk.Frame(self)
        self.chat_input_frame.grid(column=0, row=1, sticky='we')
        self.chat_input_frame.columnconfigure(2, weight=1)
        self.chat_input_frame.rowconfigure(0, weight=0)

        self.attachment_bar = tk.Frame(self.chat_input_frame, height=0)
        self.attachment_bar.rowconfigure(0, weight=0)
        self.attachment_bar_exist = False
        self.attachment_bar_up_to_date = False
        
        self.add_attachment_button = tk.Button(
            self.chat_input_frame, text='+',
            command=self.open_attachment_selection,
            relief='flat', width=2,
            font=font.Font(family='Arial', size=12)
        )
        self.add_attachment_button.grid(column=1, row=1, padx=2, pady=8, sticky='news')
        self.aab_pad = tk.Frame(self.chat_input_frame, width=0, height=0)
        self.aab_pad.grid(column=0, row=1, padx=3, pady=0)

        self.text_input_bar = tk.Text(
            self.chat_input_frame, relief='flat', highlightthickness=1,
            insertwidth=1, insertofftime="400", insertontime="300",
            height=1, state=tk.NORMAL
        )
        self.text_input_bar.grid(column=2, row=1, padx=8, pady=8, ipadx=6, ipady=6, sticky="ew")

        self.button = MessageSendButton(self.chat_input_frame, command=self.send_message)
        self.button.grid(column=3, row=1, padx=10, pady=10, sticky='news')

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

        self.update()
        tick()

    def update(self):
        self.after(MSPT, self.update)
        self.configure(bg=self.var_bg0.get())
        self.chatlog.configure(bg=self.var_bg1.get(), fg=self.var_fg.get(), font=self.var_font.get())
        self.chatlog.vbar.configure(bg=self.var_bg0.get())
        self.chat_input_frame.configure(bg=self.var_bg0.get())
        self.attachment_bar.configure(bg=self.var_bg0.get())
        self.add_attachment_button.configure(background=self.var_bg1.get(), foreground=self.var_fg.get())
        self.aab_pad.configure(bg=self.var_bg0.get())

        input_text_height = 0
        for line in (self.text_input_bar.get('1.0', 'end-1c').split('\n')):
            input_text_height += 1
        self.text_input_bar.configure(
            bg=self.var_bg1.get(), fg=self.var_fg.get(),
            font=self.var_font.get(), highlightcolor=self.var_input_bar_highlight_color.get(), highlightbackground=self.var_bg1.get(),
            insertbackground=self.var_input_bar_insert_bg.get(),
            height=min(input_text_height, utils.get_setting('theme.chatInputBar.maxHeight', 7))
        )

        slaves = self.attachment_bar.pack_slaves()
        if not self.attachment_bar_up_to_date:
            if self.attachment_bar_exist:
                self.attachment_bar.grid_forget()
                self.attachment_bar_exist = False
            if len(slaves):
                self.attachment_bar.grid(column=0, row=0, pady=0, sticky='ew', columnspan=4)
                self.attachment_bar_exist = True
            self.attachment_bar_up_to_date = True
        for slave in slaves:
            if slave.should_remove:
                slave.destroy()
                self.attachment_bar_up_to_date = False

    def upload_attachment(self, attachment: Attachment):
        frame = AttachmentFrame(self.attachment_bar, attachment)
        frame.pack(side='left', padx=8)
        self.attachment_bar_up_to_date = False

    def pop_uploaded_attachments(self) -> list[Attachment]:
        attachments = []
        if self.attachment_bar_exist:
            for slave in self.attachment_bar.pack_slaves():
                assert(isinstance(slave.attachment, Attachment))
                attachments.append(slave.attachment)
                slave.destroy()
            self.attachment_bar_up_to_date = False
        return attachments

    def send_message(self):
        text: str = self.text_input_bar.get('1.0', 'end-1c')
        if text.isspace() or len(text) < 1:
            return
        self.text_input_bar.delete('1.0', 'end')
        message = Message('<localhost>', text, self.pop_uploaded_attachments())
        self.attachment_bar_up_to_date = False
        if commands.run_command(text):
            if utils.get_setting('commands.echo', True):
                self.message_queue.put(MessagePacket(message, ['<localhost>']))
                self.after(1, self.event_generate, "<<message_recieved>>")
        else:
            packet = MessagePacket(message, self.user_list.get_selected_usernames() + ['<localhost>'])
            message_server.outbound_message_queue.put(packet)
    
    def open_attachment_selection(self):
        filenames = filedialog.askopenfilenames()
        self.attachment_bar_up_to_date = False
        for filename in filenames:
            try:
                with open(filename, mode='rb') as file:
                    attachment = Attachment(filename, file.read())
                    self.upload_attachment(attachment)
            except:
                message_server.inbound_message_queue.put(MessagePacket(Message('<system>', f'Failed to access `{filename}`'), ['<localhost>']))

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
            elif utils.get_setting('chat.bell.enabled', True):
                if self.focus_get() == None:
                    self.bell()
            if username:
                sanitized_text = message.get_text_content()
                sanitized_text = sanitized_text.replace('\033', "ESC")
                sanitized_text = sanitized_text.replace('\r', "CR")
                sanitized_text = sanitized_text.replace('\f', "FF")
                sanitized_text = sanitized_text.replace('\177', "DEL")
                self.chatlog.configure(state="normal")
                user_suffix = utils.get_setting('theme.chat.userSuffix', '\n')
                if username == "<system>":
                    self.chatlog.insert(tk.END, "<system>" + user_suffix, 'system')
                elif local:
                    self.chatlog.insert(tk.END, username + user_suffix, 'localuser')
                else:
                    self.chatlog.insert(tk.END, username + user_suffix, 'user')
                parsed_text = markdown.parse_markdown(sanitized_text)
                for wordblock, tag in parsed_text:
                    if tag == 'multiline_codeblock':
                        max_width = 0
                        for line in wordblock.split('\n'):
                            max_width = max(max_width, len(line))
                        self.chatlog.insert(tk.END, '  \n' , 'normal')
                        for line in wordblock.split('\n'):
                            self.chatlog.insert(tk.END, line + (' ' * (max_width - len(line))) , 'codeblock')
                            self.chatlog.insert(tk.END, '  \n' , 'normal')
                    else:
                        self.chatlog.insert(tk.END, wordblock, tag)
                self.chatlog.insert(tk.END, '\n', 'normal')
                if message.has_attachments():
                    for attachment in message.get_attachments():
                        rel_path = utils.save_attachment(attachment)
                        self.chatlog.insert(tk.END, f'Attachment: {rel_path}\n', 'attachment_info')
                        if utils.get_setting('security.attachments.autoOpen.enabled', False):
                            if rel_path[-4:] in AUTO_OPEN_FILE_EXTENSIONS:
                                match platform.system():
                                    case 'Windows':
                                        subprocess.Popen(['start' , '', rel_path], shell=True)
                                    case 'Linux':
                                        subprocess.Popen(['xdg-open', rel_path])
                                    case 'Darwin':
                                        subprocess.Popen(['open', rel_path])
                                    case _:
                                        utils.print_error('Unknown OS.')
                self.chatlog.configure(state="disabled")

class UserList(tk.Frame):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.var_bg0 = utils.bind_variable_to_setting(tk.StringVar(), 'theme.background.color0', '#2a2a2c')
        self.var_bg1 = utils.bind_variable_to_setting(tk.StringVar(), 'theme.background.color1', '#3f3f4a')
        self.var_fg = utils.bind_variable_to_setting(tk.StringVar(), 'theme.foreground', '#fff')
        self.var_title = utils.bind_variable_to_setting(tk.StringVar(), 'theme.userlist.title.text', "Online Users")

        self.configure(padx=4, pady=4)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.label = tk.Label(self)
        self.label.grid(row=0, column=0, pady=4, sticky='new')

        self.user_list = tk.Frame(self, padx=2, pady=2)
        self.user_list.columnconfigure(0, weight=1)
        self.user_list.grid(row=1, column=0, sticky='news')

        self._user_buttons: dict[User, UserListButton] = {}
        self.update()
    def update(self):
        self.after(MSPT, self.update)
        self.configure(bg = self.var_bg0.get())
        self.label.configure(bg = self.var_bg0.get(), fg = self.var_fg.get(), text = self.var_title.get())
        self.user_list.configure(bg = self.var_bg1.get())

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

        self.var_bg_idle = utils.bind_variable_to_setting(tk.StringVar(), 'theme.button.idle', '#30303a')
        self.var_bg_hover = utils.bind_variable_to_setting(tk.StringVar(), 'theme.button.hover', '#222')
        self.var_bg_selected = utils.bind_variable_to_setting(tk.StringVar(), 'theme.button.selected', '#11e')
        self.var_fg = utils.bind_variable_to_setting(tk.StringVar(), 'theme.font.color', '#fff')

        self.configure(border=0, anchor='w', command=self._on_command, text=user.get_username())
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
        fg, bg, text = self.var_fg.get(), self.var_bg_idle.get(), ''
        if self._selected:
            bg = self.var_bg_selected.get()
        elif self._hover:
            bg = self.var_bg_hover.get()
        if self.user.is_active():
            text = self._get_username()
        else:
            fg, text ='#aaa', self._get_username() + " (Inactive)"
        self.configure(fg=fg, bg=bg, text=text)

class MessageSendButton(tk.Button):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.var_bg0 = utils.bind_variable_to_setting(StringVar(), 'theme.button.send.idle', '#7777cc')
        self.var_bg1 = utils.bind_variable_to_setting(StringVar(), 'theme.button.send.hover', '#4343bb')
        self.var_fg = utils.bind_variable_to_setting(StringVar(), 'theme.button.send.foreground', '#fff')
        self.var_text = utils.bind_variable_to_setting(StringVar(), 'theme.button.send.text', '> Send >')
        self.var_hover = BooleanVar()
        self.var_bg0.trace_add('write', self.update)
        self.var_bg1.trace_add('write', self.update)
        self.var_fg.trace_add('write', self.update)
        self.var_text.trace_add('write', self.update)
        self.var_hover.trace_add('write', self.update)

        self.configure(border=0, anchor='center')
        self.bind('<Enter>', lambda *args: self.var_hover.set(True))
        self.bind('<Leave>', lambda *args: self.var_hover.set(False))
        self.update()
    def update(self, *args):
        self.configure(fg = self.var_fg.get(), bg = self.var_bg1.get() if self.var_hover.get() else self.var_bg0.get(), text = self.var_text.get())

class AttachmentFrame(tk.Frame):
    def __init__(self, parent, attachment: Attachment):
        super().__init__(parent)

        self.attachment = attachment
        self.should_remove = False

        self.columnconfigure(0, weight=0)
        filename = attachment.get_sanitized_filename()
        size = attachment.get_content_size()
        size_str = str(int(size))
        units = [' Bytes',' KB', ' MB', ' GB', ' TB']
        unit_index = min(4, int((len(size_str)-1)//3))
        unit_size = size / (1000 ** unit_index)
        size_str = f'{format(unit_size, '.2f').rstrip('0').rstrip('.')}{units[unit_index]}'

        self.var_bg1 = utils.bind_variable_to_setting(tk.StringVar(), 'theme.background.color1', '#3f3f4a')
        self.var_font = utils.bind_variable_to_setting(tk.StringVar(), 'theme.font', 'ariel 10')
        self.var_fg = utils.bind_variable_to_setting(tk.StringVar(), 'theme.foreground', '#fff')

        image = Image.open('./res/icons/file.png')
        image.apply_transparency()
        photo_image = ImageTk.PhotoImage(image)
        self.image_label = tk.Label(self, image=photo_image)
        self.image_label.image = photo_image
        self.image_label.grid(column=0, row=0, sticky='news', rowspan=2)

        self.filename_label = tk.Label(self, text=filename)
        self.filename_label.grid(column=1, row=0, sticky='news')

        self.size_label = tk.Label(self, text=size_str)
        self.size_label.grid(column=1, row=1, sticky='news')

        self.remove_button = tk.Button(self, text='x', fg='#f00', command=self.mark_for_removal, relief='flat')
        self.remove_button.grid(column=2, row=0, rowspan=2, sticky='news')

        self.update()

    def update(self):
        self.after(TPS, self.update)
        self.image_label.configure(background=self.var_bg1.get())
        self.filename_label.configure(fg=self.var_fg.get(), bg=self.var_bg1.get(), font=self.var_font.get())
        self.size_label.configure(fg=self.var_fg.get(), bg=self.var_bg1.get(), font=self.var_font.get())
        self.remove_button.configure(bg=self.var_bg1.get(), font=self.var_font.get())

    def mark_for_removal(self):
        self.should_remove = True
