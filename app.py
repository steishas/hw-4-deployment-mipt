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
