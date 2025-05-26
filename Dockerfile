FROM python:3.11-slim

# Install any OS deps your script needs
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scheduler.py .

# Use a minimal init to reap zombies & forward signals cleanly
# Tini is included in many official images under /usr/bin/tini
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "scheduler.py"]
