FROM python:3.12-slim

# Chromium + Xvfb: nodriver (the Yad2 scraper) needs a real, headed Chrome to
# get past Yad2's bot-detection - Xvfb gives it a virtual display since this
# container has no physical screen.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    xvfb \
    xauth \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Otherwise stdout is fully buffered (no TTY), so `docker compose logs` shows
# nothing for long-running services until enough output accumulates to flush.
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apartment_bot ./apartment_bot
COPY scripts ./scripts

# config.yaml, .env, listings.db, telethon_session.session, and the Yad2
# browser profile are all mounted as volumes in docker-compose.yml, not
# baked into the image - they're per-deployment state, not code.

CMD ["python", "-m", "apartment_bot.cli"]
