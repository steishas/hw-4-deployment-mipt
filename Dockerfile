# Сборка зависимостей
FROM python:3.9-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.9-slim

WORKDIR /app

# Копируем зависимости из стадии builder
COPY --from=builder /root/.local /home/appuser/.local

COPY app.py .

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Добавляем пакеты в PATH
ENV PATH=/home/appuser/.local/bin:$PATH

USER appuser
ENV PORT=8000
EXPOSE 8000

CMD ["python", "app.py"]
