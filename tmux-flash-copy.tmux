#!/usr/bin/env bash
# tmux-flash-copy plugin file for TPM
# This is the entry point for TPM to load the plugin and set up key bindings.

PLUGIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to get tmux variable value
get_tmux_option() {
    local option="${1}"
    local default_value="${2}"
    local option_override
    option_override="$(tmux show-option -gqv "${option}")"
    if [ -z "${option_override}" ]; then
        echo "${default_value}"
    else
        echo "${option_override}"
    fi
}

# Get the key binding from user config or use default
bind_key=$(get_tmux_option "@flash-copy-bind-key" "F")

# Bind the key to trigger the flash-copy interactive mode
tmux bind-key "${bind_key}" run-shell "${PLUGIN_DIR}/bin/tmux-flash-copy.py"
