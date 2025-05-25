# Use Python 3.13 so audioop‑lts will install
FROM python:3.13-slim

# Install OS packages needed for building Python extensions
RUN apt-get update && apt-get install -y \
      build-essential \
      python3-dev \
      libevdev-dev \
      libx11-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Run your email script by default
CMD ["python", "emailscript.py"]
