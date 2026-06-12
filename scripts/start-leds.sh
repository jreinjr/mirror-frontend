#!/usr/bin/env bash
#
# start-leds.sh — drive the mirror LED ring white, and nothing else.
#
# This is the LED step extracted from start-mirror.sh. It runs ONLY the
# one-shot LED script (led/white.py via the mirror-frontend venv). It does NOT:
#   - start the Next.js dev server,
#   - open the Firefox kiosk,
#   - start the cursor-hide idle watcher.
#
# Use this when you want the Pi purely as an LED controller, independent of the
# mirror frontend or any remote stream server.
#
# Runs on boot via ~/.config/autostart/start-mirror.desktop, and can also be
# run by hand at any time:  start-leds.sh

set -u

# ---- config -----------------------------------------------------------------
APP_DIR="$HOME/mirror-frontend"
STATE_DIR="$HOME/.local/state/mirror"
LED_LOG="$STATE_DIR/white.log"
VENV_PY="$APP_DIR/.venv/bin/python"               # mirror-frontend venv
WHITE_SCRIPT="$APP_DIR/led/white.py"              # one-shot: set LED ring white

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
mkdir -p "$STATE_DIR"

log() { printf '[start-leds %s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ---- drive the LED ring white (one-shot) -----------------------------------
if [ -x "$VENV_PY" ] && [ -f "$WHITE_SCRIPT" ]; then
  log "setting LED ring white: $WHITE_SCRIPT"
  if ( cd "$APP_DIR" && "$VENV_PY" "$WHITE_SCRIPT" ) >"$LED_LOG" 2>&1; then
    log "LED ring set white"
  else
    log "ERROR: white.py failed (see $LED_LOG)"
    exit 1
  fi
else
  log "ERROR: venv python ($VENV_PY) or white.py ($WHITE_SCRIPT) missing"
  exit 1
fi

log "done."
