FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    xdg-utils \
    libxcb-cursor0 \
    libegl1 \
    libopengl0 \
    xvfb \
    ca-certificates \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Calibre headless (gives us ebook-convert for CBZ -> EPUB)
RUN wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin

# Install kepubify (EPUB -> real KePub, same tool Grimmory uses internally)
RUN wget -nv -O /usr/local/bin/kepubify \
      https://github.com/pgaskin/kepubify/releases/latest/download/kepubify-linux-64bit \
    && chmod +x /usr/local/bin/kepubify

RUN pip3 install --no-cache-dir --break-system-packages flask

WORKDIR /app
COPY app.py .
COPY templates ./templates

ENV INPUT_ROOT=/input
ENV OUTPUT_ROOT=/output
ENV FLASK_SECRET_KEY=change-me

EXPOSE 5000

CMD ["python3", "app.py"]
