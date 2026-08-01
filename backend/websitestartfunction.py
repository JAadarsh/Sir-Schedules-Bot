from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

"""
Following switch to wispbyte, websitestartfunction will be used
to start a web server. 

>>> this is NOT a priority for the project, delayed indefinitely

will be used to deploy a website for the bot in 2027 (maybe), 
but could evolve into a different project all together.
"""
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()