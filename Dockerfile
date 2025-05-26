 FROM python:3.13-slim

 # install OS packages…
 RUN apt-get update && apt-get install -y \
       build-essential python3-dev libevdev-dev libx11-dev \
     && rm -rf /var/lib/apt/lists/*

 WORKDIR /app

 # install Python deps
 COPY requirements.txt .
 RUN pip install --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

+# pull down Playwright’s browser binaries
+RUN python3 -m playwright install chromium

 # copy your code
 COPY . .

 CMD ["python", "emailscript.py"]
