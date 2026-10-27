from http.server import BaseHTTPRequestHandler
from ghostlight_api import handle_speak


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        handle_speak(self)

    def do_GET(self):
        self.send_error(405, "Use POST")

    def log_message(self, fmt, *args):
        pass
