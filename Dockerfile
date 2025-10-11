FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libsqlite3-0 \
    libsqlite3-dev \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
