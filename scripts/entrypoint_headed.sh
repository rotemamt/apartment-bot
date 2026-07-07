#!/bin/bash
# Starts a virtual display then execs the given command against it.
# Used instead of `xvfb-run`, which was observed to hang silently (with
# buffered output masking the failure) when Chrome is launched as root.
set -e
# A container restart (not recreate - e.g. after a host reboot or `docker
# compose restart`) reuses the same writable /tmp, so a lock file left by
# an unclean shutdown survives and makes Xvfb refuse to start ("Server is
# already active for display 99"). We're always the only Xvfb in this
# container, so any leftover lock is necessarily stale.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &

for i in $(seq 1 50); do
    [ -e /tmp/.X11-unix/X99 ] && break
    sleep 0.2
done

export DISPLAY=:99
exec "$@"
