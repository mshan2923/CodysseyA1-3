import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)

load_env(os.path.join(os.path.dirname(__file__), ".env"))

from plan import handler as PlanHandler  # plan.py의 os.getenv 호출보다 반드시 뒤에 위치

PORT = int(os.getenv("PORT", "8000"))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")

class Router(SimpleHTTPRequestHandler, PlanHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=PUBLIC_DIR, **kw)

    def do_POST(self):
        if self.path == "/api/plan":
            PlanHandler.do_POST(self)
        else:
            self.send_error(404)

if __name__ == "__main__":
    print(f"http://localhost:{PORT} 에서 서비스 중 (Ctrl+C로 종료)")
    HTTPServer(("", PORT), Router).serve_forever()
