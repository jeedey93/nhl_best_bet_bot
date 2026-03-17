#!/usr/bin/env python3
"""
Simple local test server for testing the Habs voting page
Runs a local HTTP server and mocks the voting API
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
from datetime import datetime

# In-memory vote storage for testing
votes_db = {}

class VotingRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve from docs directory
        super().__init__(*args, directory='docs', **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)

        # Proxy NHL API requests to avoid CORS
        if parsed_path.path == '/nhl/schedule':
            query_params = parse_qs(parsed_path.query)
            date = query_params.get('date', [datetime.now().strftime('%Y-%m-%d')])[0]

            try:
                nhl_url = f'https://api-web.nhle.com/v1/schedule/{date}'
                with urlopen(nhl_url, timeout=10) as response:
                    nhl_data = response.read()

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(nhl_data)
                print(f"[NHL API] Proxied schedule for {date}")
                return
            except Exception as e:
                print(f"[NHL API] Error: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'error': str(e)}
                self.wfile.write(json.dumps(response).encode())
                return

        # Mock voting API
        if parsed_path.path == '/api/vote':
            query_params = parse_qs(parsed_path.query)
            date = query_params.get('date', [datetime.now().strftime('%Y-%m-%d')])[0]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                'success': True,
                'votes': votes_db.get(date, {})
            }
            self.wfile.write(json.dumps(response).encode())
            return

        # Serve static files
        super().do_GET()

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)

        # Mock voting API
        if parsed_path.path == '/api/vote':
            query_params = parse_qs(parsed_path.query)
            date = query_params.get('date', [datetime.now().strftime('%Y-%m-%d')])[0]

            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            pick_id = data.get('pickId')

            if not pick_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Missing pickId'}
                self.wfile.write(json.dumps(response).encode())
                return

            # Get client IP (simplified for local testing)
            client_ip = self.client_address[0]

            # Initialize date votes if needed
            if date not in votes_db:
                votes_db[date] = {}

            # Check if user already voted (simplified - just increment for testing)
            if pick_id not in votes_db[date]:
                votes_db[date][pick_id] = 0

            votes_db[date][pick_id] += 1

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                'success': True,
                'votes': votes_db[date]
            }
            self.wfile.write(json.dumps(response).encode())
            print(f"✓ Vote recorded: {pick_id} (Total: {votes_db[date][pick_id]})")
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log format"""
        # Convert args to strings to avoid type errors
        str_args = [str(arg) for arg in args]
        if '/api/vote' in str_args[0]:
            # Only log API calls with custom format
            print(f"[API] {str_args[0]}")
        elif len(str_args) > 1 and str_args[1] == '200':
            # Only log successful file requests
            print(f"[WEB] {str_args[0]}")

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, VotingRequestHandler)

    print("=" * 60)
    print("🏒 Habs Voting Test Server Running!")
    print("=" * 60)
    print(f"\n📍 Local URL: http://localhost:{port}/habs-vote.html")
    print(f"\n🔧 Mock API: http://localhost:{port}/api/vote")
    print("\n💡 Tips:")
    print("   - The page will automatically check if Habs are playing today")
    print("   - Voting is stored in memory (resets when server stops)")
    print("   - Open in multiple browsers/tabs to test voting")
    print("\n⏹️  Press Ctrl+C to stop\n")
    print("=" * 60)
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
        print(f"📊 Final vote counts: {votes_db}")

if __name__ == '__main__':
    run_server()
