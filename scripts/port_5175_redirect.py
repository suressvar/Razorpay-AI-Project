"""Lightweight helper redirecting any requests on legacy port 5175 to active Vite port 5173."""

import http.server
import socketserver

PORT = 5175
TARGET_PORT = 5173


class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def handle_redirect(self):
        target = f"http://localhost:{TARGET_PORT}{self.path}"
        self.send_response(307)
        self.send_header("Location", target)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(f"Redirecting to {target}".encode("utf-8"))

    def do_GET(self):
        self.handle_redirect()

    def do_POST(self):
        self.handle_redirect()

    def do_HEAD(self):
        self.handle_redirect()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), RedirectHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        pass
