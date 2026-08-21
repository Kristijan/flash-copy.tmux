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

# Get the key binding and key table from user config or use defaults
bind_key=$(get_tmux_option "@flash-copy-bind-key" "F")
bind_key_mode=$(get_tmux_option "@flash-copy-bind-key-mode" "prefix")

case "${bind_key_mode}" in
    prefix|root) ;;
    *) bind_key_mode="prefix" ;;
esac

# Bind the key to trigger the flash-copy interactive mode. Capture runtime identity
# while tmux still has the key event's pane and client context.
tmux bind-key -T "${bind_key_mode}" "${bind_key}" run-shell \
    "\"${PLUGIN_DIR}/bin/tmux-flash-copy.py\" --pane-id \"#{pane_id}\" --client-name \"#{client_name}\""
