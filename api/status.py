from http.server import BaseHTTPRequestHandler
from ghostlight_api import handle_status


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        handle_status(self)

    def do_POST(self):
        self.send_error(405, "Use GET")

    def log_message(self, fmt, *args):
        pass
