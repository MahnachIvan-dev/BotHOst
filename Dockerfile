FROM python:3.11-slim

# Устанавливаем Docker CLI (нужен для управления контейнерами)
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Директория для ботов пользователей
RUN mkdir -p /app/user_bots

# Пробрасываем docker.sock для управления контейнерами
# Это делается при запуске: -v /var/run/docker.sock:/var/run/docker.sock

EXPOSE 8000

CMD ["python", "runner.py"]
