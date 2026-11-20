"""
Antigravity Alpha Trader - Built-in Dashboard Web Server
Serves the live interactive trading dashboard on localhost:5000.
"""

import http.server
import logging
import os
import socketserver
import threading
from config import BASE_DIR, WEB_SERVER_HOST, WEB_SERVER_PORT
from dashboard_generator import generate_dashboard

logger = logging.getLogger("AlphaTrader.WebServer")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # Health check endpoint for cloud uptime monitors
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Serve the 3 Master Bots Suite Dashboard
        if self.path == "/suite" or self.path == "/suite_dashboard.html":
            suite_dash = os.path.join(BASE_DIR, "bots_suite", "suite_dashboard.html")
            if os.path.exists(suite_dash):
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                with open(suite_dash, "rb") as f:
                    self.wfile.write(f.read())
                return

        # Auto-regenerate dashboard whenever user hits root URL
        if self.path == "/" or self.path == "/index.html" or self.path == "/dashboard.html":
            generate_dashboard()
            self.path = "/dashboard.html"
        return super().do_GET()

    def log_message(self, format, *args):
        # Silence routine HTTP access logs to keep terminal output clean
        return


def start_server_daemon(port=WEB_SERVER_PORT, host=WEB_SERVER_HOST):
    """Starts the web server in a background daemon thread."""
    generate_dashboard()

    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        httpd = ReusableTCPServer((host, port), DashboardHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Dashboard Web UI is running live at http://{host}:{port}/")
        return httpd
    except Exception as e:
        logger.warning(f"Could not start dashboard web server on {host}:{port}: {e}")
        return None


if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        generate_dashboard()
        httpd = ReusableTCPServer((WEB_SERVER_HOST, WEB_SERVER_PORT), DashboardHandler)
        print(f"\n========================================================")
        print(f"  DASHBOARD IS LIVE: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/")
        print(f"  Open this link in any browser to see the live bot UI!")
        print(f"========================================================\n")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping web server.")
    except Exception as e:
        print(f"Server error: {e}")
