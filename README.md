# MoRes-Chat
A simple local network chat app made for a school project.

## ✨ Features
* 📔 User list (allows you to see available users)
* 💬 Chat with other users
* ⌨️ Slash commands
  - Type $${\color{lightgreen}\texttt{\textsf{/help }}}$$ in chat to see a list of commands
* 🔐 Basic message content encryption during transmit
  - **WARNING**: NOT SECURE due to given project requirements
* 🐍 User scripts
  - User scripts allows the user to add their $${\color{#0af}py\color{#ff0}thon}$$ scripts to extend the capabilities of the app
  - Add your script to the `user_scripts` folder (generated after first run) then use the `/exec` slash comamnd to execute your script
* 🎨 Themes
  - You can use pre-installed themes, or make your own
* 📁 Message attachments
  - You can attach small files to your messages

## Dependencies
* Python 3.12 or later
* cryptography `pip install cryptography`
* pillow `pip install pillow`
