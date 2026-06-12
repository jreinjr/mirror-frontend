#!/usr/bin/env bash
#
# start-mirror.sh — bring up the comfystream-mirror frontend and display it
# fullscreen in a Firefox kiosk window.
#
#   1. If the Next.js dev server (http://localhost:3000) isn't already
#      running, start it with `npm run dev` (detached) and wait for it.
#   2. Open Firefox in --kiosk mode pointed at the mirror, fullscreen with
#      no tabs/toolbars (the F11 look).
#
# Runs on boot via ~/.config/autostart/start-mirror.desktop, and can also be
# run by hand at any time:  start-mirror.sh
#
# Safe to run repeatedly: it won't start a second dev server or a second
# kiosk window if they are already up.

set -u

# ---- config -----------------------------------------------------------------
APP_DIR="$HOME/mirror-frontend"
PORT=3000
URL="http://localhost:${PORT}"
PROFILE_DIR="$HOME/.local/share/mirror-firefox"   # dedicated Firefox profile
STATE_DIR="$HOME/.local/state/mirror"
DEV_LOG="$STATE_DIR/dev-server.log"
FF_LOG="$STATE_DIR/firefox.log"
LED_LOG="$STATE_DIR/white.log"
VENV_PY="$APP_DIR/.venv/bin/python"               # mirror-frontend venv
WHITE_SCRIPT="$APP_DIR/led/white.py"              # one-shot: set LED ring white
READY_TIMEOUT=120                                  # seconds to wait for the server

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
mkdir -p "$STATE_DIR" "$PROFILE_DIR"

log() { printf '[start-mirror %s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ---- wayland / display env (helps when triggered over SSH) ------------------
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
: "${WAYLAND_DISPLAY:=wayland-0}"
: "${DISPLAY:=:0}"
export XDG_RUNTIME_DIR WAYLAND_DISPLAY DISPLAY
export MOZ_ENABLE_WAYLAND=1

# ---- helpers ----------------------------------------------------------------
# True if something is bound to / listening on $PORT (i.e. the dev server is up).
port_listening() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -q ":${PORT} "
  else
    (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") 2>/dev/null && { exec 3>&-; return 0; }
    return 1
  fi
}

# ---- 1. ensure the dev server is up ----------------------------------------
if port_listening; then
  log "dev server already listening on :${PORT}"
else
  if [ ! -d "$APP_DIR" ]; then
    log "ERROR: app directory not found: $APP_DIR"
    exit 1
  fi
  log "starting dev server: npm run dev  (in $APP_DIR)"
  ( cd "$APP_DIR" && exec setsid npm run dev ) >"$DEV_LOG" 2>&1 < /dev/null &
  log "dev server launched (PID group detached); logging to $DEV_LOG"

  log "waiting up to ${READY_TIMEOUT}s for :${PORT} to come up ..."
  deadline=$(( $(date +%s) + READY_TIMEOUT ))
  until port_listening; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
      log "ERROR: dev server did not start within ${READY_TIMEOUT}s — see $DEV_LOG"
      exit 1
    fi
    sleep 2
  done
  log "dev server is up"
  sleep 1   # small grace so the first page request compiles cleanly
fi

# ---- 2. drive the LED ring white (one-shot) --------------------------------
if [ -x "$VENV_PY" ] && [ -f "$WHITE_SCRIPT" ]; then
  log "setting LED ring white: $WHITE_SCRIPT"
  if ( cd "$APP_DIR" && "$VENV_PY" "$WHITE_SCRIPT" ) >"$LED_LOG" 2>&1; then
    log "LED ring set white"
  else
    log "WARNING: white.py failed (see $LED_LOG) — continuing"
  fi
else
  log "WARNING: venv python or white.py missing — skipping LED step"
fi

# ---- 3. seed a quiet kiosk Firefox profile (first run only) -----------------
seed_profile() {
  local ujs="$PROFILE_DIR/user.js"
  [ -f "$ujs" ] && return 0
  cat > "$ujs" <<'EOF'
// Mirror kiosk profile — keep Firefox quiet and out of the way.
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.messaging-system.whatsNewPanel.enabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.tabs.warnOnClose", false);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("full-screen-api.warning.timeout", 0);
// No white flash before the page paints — keep the mirror background black.
user_pref("browser.display.background_color", "#000000");
// Auto-grant camera/mic so the kiosk never prompts. localhost is a secure
// context, so these stick; media.navigator.permission.disabled skips the
// getUserMedia prompt entirely and grants with the default devices.
user_pref("permissions.default.camera", 1);
user_pref("permissions.default.microphone", 1);
user_pref("media.navigator.permission.disabled", true);
EOF
  log "seeded kiosk Firefox profile at $PROFILE_DIR"
}

# ---- 4. open Firefox in kiosk (fullscreen, no chrome) -----------------------
if pgrep -f -- "--profile ${PROFILE_DIR}" >/dev/null 2>&1; then
  log "kiosk Firefox already running — leaving it as is"
else
  seed_profile
  log "launching Firefox kiosk at $URL"
  setsid firefox --kiosk --no-remote --profile "$PROFILE_DIR" "$URL" \
    >"$FF_LOG" 2>&1 < /dev/null &
  log "Firefox launched; logging to $FF_LOG"
fi

# ---- 5. auto-hide the mouse cursor after 5s of inactivity -------------------
# labwc's HideCursor action hides the pointer until the next real pointer move.
# ~/.config/labwc/rc.xml binds the (otherwise unused) F35 keysym to HideCursor;
# swayidle "taps" F35 via wtype after 5s idle, and the cursor returns on the
# next mouse movement. Idempotent: won't start a second watcher.
if command -v swayidle >/dev/null 2>&1 && command -v wtype >/dev/null 2>&1; then
  if pgrep -f 'swayidle.*F35' >/dev/null 2>&1; then
    log "cursor-hide idle watcher already running"
  else
    log "starting cursor-hide idle watcher (hide pointer after 5s idle)"
    setsid swayidle -w timeout 5 'wtype -k F35' \
      >"$STATE_DIR/swayidle.log" 2>&1 < /dev/null &
    log "cursor-hide watcher started; logging to $STATE_DIR/swayidle.log"
  fi
else
  log "WARNING: swayidle or wtype missing — cursor will not auto-hide"
  log "         install with:  sudo apt install -y wtype   (swayidle is already present)"
fi

log "done."
