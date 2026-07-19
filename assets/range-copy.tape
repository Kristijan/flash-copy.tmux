# https://github.com/charmbracelet/vhs

# GIF output file
Output range-copy.gif

# Terminal setup
Set Theme "Catppuccin Mocha"
Set FontFamily "MonaspiceAr Nerd Font Mono"
Set FontSize 16
Set Padding 0
Set Framerate 60
Set Width 1000
Set Height 610

# Shell setup
Set Shell zsh

# Require programs
Require tmux
Require bat

# Launch tmux (hidden in GIF)
Hide
Type "tmux new -s tmux-flash-copy -n range-copy" Enter
Sleep 5s
Type "cd /Users/kristijan/GitHub/flash-copy.tmux" Enter
Type "clear" Enter
Show

# cat tmux-flash-copy.tmux file
Sleep 2s
Type "bat -pp --color never tmux-flash-copy.tmux" Enter
Sleep 500ms

# Commentary
Type `"I'll now copy 'tmux-flash-copy plugin file' from the second line in this file."`
Sleep 2s
Ctrl+u

# Start tmux-flash-copy
Ctrl+p
Sleep 500ms
Type "f"
Sleep 500ms

# Type first marker
Type@500ms "tmux"
Sleep 1.5s
Type ",k"
Sleep 1s

# Type second marker
Type@500ms "file"
Sleep 1.5s
Type "a"
Sleep 1s

# Paste copied text
Type `"The first marker remains highlighted while you search for the second marker."`
Sleep 1s
Ctrl+u
Copy "tmux-flash-copy plugin file"
Type "Pasting"
Type@500ms "..."
Type " "
Paste

# Admire the output for a bit.
Sleep 5s

# Kill the tmux server (hidden in GIF)
Hide
Type "tmux kill-server" Enter
