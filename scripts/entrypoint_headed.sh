#!/bin/bash
# Starts a virtual display then execs the given command against it.
# Used instead of `xvfb-run`, which was observed to hang silently (with
# buffered output masking the failure) when Chrome is launched as root.
set -e
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &

for i in $(seq 1 50); do
    [ -e /tmp/.X11-unix/X99 ] && break
    sleep 0.2
done

export DISPLAY=:99
exec "$@"
