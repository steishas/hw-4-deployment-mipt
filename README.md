# Домашнее задание 4. Dockerfile

**Автор:** Смирнова Анастасия  
**Группа:** РМ2  
**Дата:** 16.04.2026

---

## Описание приложения

В качестве контейнеризируемого сервиса используется CRUD API из ДЗ 1. Приложение реализовано на Python с использованием стандартной библиотеки `http.server`. Данные хранятся в памяти (in-memory database).

**Эндпоинты API:**
- `GET /items` — список всех товаров
- `GET /items/{id}` — получить товар по ID
- `POST /items` — создать новый товар

**Код приложения (`app.py`):**
```python
import json
import re
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# In-memory database
items_db = {
    "1": {
        "id": "1",
        "name": "Антифриз EURO G11",
        "price": 1025,
        "discount": 11,
        "category": "антифриз"
    },
    "2": {
        "id": "2", 
        "name": "Антифриз Синтек MULTIFREEZE",
        "price": 250,
        "discount": 38,
        "category": "антифриз"
    }
}
next_id = 3

class SimpleCRUDHandler(BaseHTTPRequestHandler):
    
    def _send_json_response(self, status_code, data=None):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        if data is not None:
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _parse_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return None
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            return None
    
    def do_GET(self):
        global items_db
        match_all = re.match(r'^/items/?$', self.path)
        match_single = re.match(r'^/items/([0-9]+)/?$', self.path)
        
        if match_all:
            self._send_json_response(200, list(items_db.values()))
        elif match_single:
            item_id = match_single.group(1)
            if item_id in items_db:
                self._send_json_response(200, items_db[item_id])
            else:
                self._send_json_response(404, {'detail': 'Item not found'})
        else:
            self._send_json_response(404, {'detail': 'Not Found'})
    
    def do_POST(self):
        match_path = re.match(r'^/items/?$', self.path)
        if match_path:
            data_to_post = self._parse_json_body()
            
            if data_to_post is None:
                self._send_json_response(400, {'detail': 'Invalid JSON'})
                return
            
            global items_db, next_id
            item_to_post = dict(data_to_post)
            item_to_post['id'] = str(next_id)
            items_db[str(next_id)] = item_to_post
            
            next_id += 1
            
            self._send_json_response(201, item_to_post)
        else:
            self._send_json_response(404, {'detail': 'Not Found'})
    
    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

def run_server(port=8000):
    port = int(os.environ.get('PORT', 8000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleCRUDHandler)
    print(f'Запускаем CRUD сервис на порту {port}...')
    print(f'Инициализрована БД с {len(items_db)} товарами')
    print(f'API эндпоинты:')
    print(f'  GET    /items     - Список всех товаров')
    print(f'  GET    /items/<id> - Получить товар по ID')
    print(f'  POST   /items     - Создать новый товар')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
```

*Приложение не имеет внешних зависимостей, что устраняет проблемы совместимости.*

---

## 1. Базовый Dockerfile

```dockerfile
FROM python:3.9-slim AS builder

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

CMD ["python", "app.py"]
```

**Ключевые моменты:**
- Фиксированная версия Python (`3.9-slim`)
- Кеширование зависимостей через порядок слоёв и `--no-cache-dir`
- Непривилегированный пользователь для безопасности
- Поддержка переменной `PORT` для облачных платформ

**Проверка через hadolint:**
```
Без ошибок и предупреждений
```

---

## 2. Многостадийная сборка

```dockerfile
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
```

**Преимущества:**
- Стадия `builder` устанавливает зависимости с флагом `--user`
- Финальный образ копирует только готовые пакеты
- Уменьшение размера образа за счёт исключения временных файлов

**Проверка через hadolint:**
```
Без ошибок и предупреждений
```

---

## 3. docker-compose (сети, volumes, restart)

```yaml
---
services:
  crud-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: crud-api-container
    ports:
      - "8000:8000"
    volumes:
      - app-data:/app/data
    networks:
      - internal
      - external
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1

volumes:
  app-data:
    driver: local

networks:
  internal:
    internal: true
  external:
```

**Пояснения:**
| Элемент | Назначение |
|---------|------------|
| `networks.internal` | Внутренняя сеть (`internal: true`), только между контейнерами |
| `networks.external` | Внешняя сеть, доступ из интернета |
| `volumes.app-data` | Сохранение данных между перезапусками |
| `restart: unless-stopped` | Автоматический перезапуск при сбоях |
| `PYTHONUNBUFFERED=1` | Логи сразу в `docker-compose logs` |

**Проверка через yamllint:**
```
Без ошибок
```

---

## 4. docker-compose (ограничения ресурсов)

```yaml
---
services:
  crud-api:
    # ... (все настройки выше)
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.50'
        reservations:
          memory: 128M
          cpus: '0.25'
```

**Ограничения:**
| Тип | CPU | Память |
|-----|-----|--------|
| Максимум (limits) | 0.50 ядра | 256 МБ |
| Минимум (reservations) | 0.25 ядра | 128 МБ |

*Значения выбраны с учётом профиля потребления (~100 МБ памяти).*

---

## 5. Kubernetes манифесты

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crud-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crud-api
  template:
    metadata:
      labels:
        app: crud-api
    spec:
      containers:
      - name: crud-api
        image: crud-api:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "500m"
            memory: "256Mi"
          requests:
            cpu: "250m"
            memory: "128Mi"
        livenessProbe:
          httpGet:
            path: /items
            port: 8000
        readinessProbe:
          httpGet:
            path: /items
            port: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: crud-api-service
spec:
  selector:
    app: crud-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Компоненты:**
| Ресурс | Назначение |
|--------|------------|
| Deployment | Управление подами, 1 реплика, probes для здоровья |
| Service | Тип LoadBalancer, доступ извне кластера |

*Манифест готов к применению: `kubectl apply -f deploy.yaml`*

---

## 6. Деплой в облако (Render)

**Платформа:** Render (PaaS)  
**Тип:** Web Service (Docker)  
**Тариф:** Free

**Публичный адрес для доступа к items:**
```
https://hw-4-deployment-mipt.onrender.com/items
```

**Особенности:**
- Контейнер засыпает после 15 минут бездействия
- Холодный старт: 30-50 секунд

**Скриншоты:**
- Dashboard Render со статусом "Live"
<img width="1427" height="477" alt="image" src="https://github.com/user-attachments/assets/d1eb83b4-b35b-41af-9124-35a31abbf8ba" />

---

- Успешный `curl` к публичному URL
<img width="1355" height="49" alt="image" src="https://github.com/user-attachments/assets/b2079735-1e87-44d3-8e59-a2065f8d7ea4" />

---
- Логи контейнера в Render
<img width="1080" height="575" alt="image" src="https://github.com/user-attachments/assets/e4249519-42f7-432d-a88c-67e09cf64878" />

---

## 7. Выводы

В ходе выполнения домашнего задания были освоены базовые принципы контейнеризации веб-сервисов с использованием Docker и оркестрации с помощью Kubernetes.

**Что оказалось простым:** Написание базового Dockerfile и docker-compose файлов — синтаксис интуитивно понятен. Настройка сетей и томов также не вызвала затруднений после изучения документации. Деплой сервиса на Render также не вызвал затруднений. Воспользовалась [инструкцией](https://ru.hexlet.io/blog/posts/kak-deploit-prilozhenie-na-render-gayd-dlya-frontenderov-i-bekenderov).

**Что вызвало трудности:** Многостадийная сборка потребовала внимания к деталям: флаг `--user` для pip, копирование `/root/.local`, настройка `PATH`. На Mac с Apple Silicon возникли проблемы бинарной совместимости pandas с numpy, что было решено заменой на встроенные структуры Python.

**Выводы:** Docker и Kubernetes — незаменимые инструменты в реальных проектах. Docker обеспечивает воспроизводимость окружения и упрощает деплой. Kubernetes предоставляет декларативное управление инфраструктурой, автоматическое масштабирование и самовосстановление. Освоение этих инструментов критически важно для современной разработки ML-сервисов.

---

## Приложения

1. Репозиторий GitHub: `https://github.com/steishas/hw-4-deployment-mipt`
2. Публичный URL: `https://hw-4-deployment-mipt.onrender.com/items`
3. [Jupyter Notebook](https://github.com/steishas/hw-4-deployment-mipt/blob/main/HW4_Docker_%D0%A1%D0%BC%D0%B8%D1%80%D0%BD%D0%BE%D0%B2%D0%B0_%D0%90_%D0%9C.ipynb)с кодом и заметками по ходу выполнения задания
