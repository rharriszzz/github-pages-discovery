"""Shared fixed-route loopback HTTP protections for private review interfaces."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json


class PrivateHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def valid_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

    def valid_write(self, token):
        return (self.valid_host() and self.headers.get('Origin') == f'http://127.0.0.1:{self.server.server_port}'
                and hmac.compare_digest(self.headers.get('X-Review-Token', '').encode(), token.encode()))

    def payload(self, maximum=20_000_000):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= maximum or self.headers.get('Content-Type') != 'application/json':
            raise ValueError('Invalid request size or type')
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError('Request must be an object')
        return value

    def reply(self, status, body, kind='application/json'):
        try:
            self.send_response(status)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def json(self, status, value):
        return self.reply(status, json.dumps(value, ensure_ascii=False).encode())


def loopback_server(handler, port):
    if not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535')
    return HTTPServer(('127.0.0.1', port), handler)


def run_server(server, label):
    print(f'{label}: http://127.0.0.1:{server.server_port}/', flush=True)
    print('Keep this terminal running. On WSL2, open the URL in your Windows browser. '
          'If Windows cannot connect, check WSL localhost forwarding; the service binds only to loopback.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
