# MoRes-Chat
A **local network** instant messaging app written in Python **for an university project**.

## ✨ Features
* 📔 User list (allows you to see available users on your LAN)
* 💬 Chat with other users
* ⌨️ Slash commands
  - Type $${\color{lightgreen}\texttt{\textsf{/help }}}$$ in chat to see a list of commands
* 🔐 Basic message content encryption during transmit
  - **WARNING**: It is NOT SECURE due to given project requirements.
* 🐍 User scripts
  - User scripts allows the user to add their $${\color{#0af}Py\color{#ff0}thon}$$ scripts to extend the capabilities of the app
  - Add your script to the `user_scripts` folder (generated after first run) then use the `/exec` slash comamnd to execute your script
* 🎨 Themes
  - You can use pre-installed themes, or make your own
* 📁 Message attachments
  - You can attach small files to your messages

## Dependencies
* Python 3
* cryptography `pip install cryptography`
* pillow `pip install pillow`
* An IPv4 connection.

## Known issues
* Attachments larger than a few kilobytes can't be sent reliably
* Uses the wrong network if connected to multiple networks (for example: ethernet + wifi + vpn)
  - In this case, broadcast address should be configured to the desired network's broadcast address in `config.py`
* Most emojis render incorrectly or not at all (tkinter issue)
* Glitchy user interface on MacOS (another tkinter issue)
* Markdown may not work well in some cases.
* Networking does not work properly inside proot.
