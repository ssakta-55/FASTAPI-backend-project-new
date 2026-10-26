"""A tiny local webhook receiver for trying the notification job.

Usage:
    python scripts/webhook_receiver.py                 # always replies OK
    python scripts/webhook_receiver.py --fail-first 2  # first 2 requests fail, so you can watch retries
Then set WEBHOOK_URL=http://127.0.0.1:9000 in .env and restart the worker.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=9000)
parser.add_argument("--fail-first", type=int, default=0)
args = parser.parse_args()
seen = {"count": 0}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        seen["count"] += 1
        if seen["count"] <= args.fail_first:
            print("request %d: replying 500 on purpose" % seen["count"], flush=True)
            self.send_response(500)
        else:
            print("request %d: OK %s" % (seen["count"], json.loads(body)), flush=True)
            self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


print("Listening on http://127.0.0.1:%d (Ctrl+C to stop)" % args.port, flush=True)
HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
