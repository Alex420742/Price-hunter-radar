"""Read-only, token-protected dashboard API and static file server."""
from __future__ import annotations
import hmac, json, logging, sqlite3, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
log=logging.getLogger(__name__)
class DashboardHandler(BaseHTTPRequestHandler):
 server_version="PriceHunterDashboard/1.0"
 def log_message(self,fmt,*args): log.info("dashboard %s - %s",self.address_string(),fmt%args)
 def _json(self,payload,status=200):
  body=json.dumps(payload,ensure_ascii=False,default=str).encode()
  self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.end_headers();self.wfile.write(body)
 def _authorized(self):
  return hmac.compare_digest(self.headers.get("Authorization","").encode(),("Bearer "+self.server.token).encode())
 def _db(self):
  path=Path(self.server.db_path).resolve()
  return sqlite3.connect("file:"+path.as_posix()+"?mode=ro",uri=True,timeout=5)
 def do_GET(self):
  parsed=urlparse(self.path)
  if parsed.path.startswith("/api/"):
   if not self._authorized():return self._json({"error":"unauthorized"},401)
   try:
    with self._db() as db:
     db.row_factory=sqlite3.Row
     if parsed.path=="/api/status":
      pending=db.execute("SELECT COUNT(*) n FROM review_queue WHERE status='pending'").fetchone()["n"]
      approved=db.execute("SELECT COUNT(*) n FROM review_queue WHERE status='approved'").fetchone()["n"]
      observations=db.execute("SELECT COUNT(*) n FROM price_observations").fetchone()["n"]
      watch=[r[0] for r in db.execute("SELECT query FROM watchlist ORDER BY query COLLATE NOCASE")]
      paused=(db.execute("SELECT value FROM settings WHERE key='paused'").fetchone() or ["false"])[0]=="true"
      latest=db.execute("SELECT MAX(observed_at) FROM price_observations").fetchone()[0]
      return self._json({"pending":pending,"approved":approved,"observations":observations,"watchlist":watch,"paused":paused,"latest_observation":latest})
     if parsed.path=="/api/offers":
      qs=parse_qs(parsed.query);status=qs.get("status",["pending"])[0]
      if status not in ("pending","approved","rejected"):return self._json({"error":"invalid status"},400)
      limit=min(max(int(qs.get("limit",["100"])[0]),1),200)
      rows=db.execute("SELECT id,title,current_price,currency,seller,url,source,shipping_cost,condition,in_stock,score,discount_pct,baseline_price,reasons,status,created_at FROM review_queue WHERE status=? ORDER BY score DESC,created_at DESC LIMIT ?",(status,limit)).fetchall()
      return self._json([dict(r) for r in rows])
     if parsed.path=="/api/history":
      qs=parse_qs(parsed.query);key=qs.get("product_key",[""])[0]
      if not key:return self._json({"error":"product_key required"},400)
      rows=db.execute("SELECT title,price,currency,seller,source,observed_at FROM price_observations WHERE product_key=? ORDER BY observed_at DESC LIMIT 200",(key,)).fetchall()
      return self._json([dict(r) for r in rows])
     return self._json({"error":"not found"},404)
   except (sqlite3.Error,ValueError):
    log.exception("dashboard API query failed");return self._json({"error":"query failed"},500)
  root=Path(self.server.web_dir).resolve();target=(root/("index.html" if parsed.path in ("/","/index.html") else parsed.path.lstrip("/"))).resolve()
  if root not in target.parents and target!=root:return self.send_error(403)
  if not target.is_file():return self.send_error(404)
  content=target.read_bytes();mime="text/html" if target.suffix==".html" else "text/css" if target.suffix==".css" else "application/javascript" if target.suffix==".js" else "application/octet-stream"
  self.send_response(200);self.send_header("Content-Type",mime+"; charset=utf-8");self.send_header("Content-Length",str(len(content)));self.send_header("X-Content-Type-Options","nosniff");self.end_headers();self.wfile.write(content)
def start_dashboard_server(db_path,web_dir,token,host="0.0.0.0",port=8080):
 if not token or len(token)<24:raise ValueError("Dashboard token must be at least 24 characters")
 server=ThreadingHTTPServer((host,int(port)),DashboardHandler);server.daemon_threads=True;server.token=token;server.db_path=db_path;server.web_dir=web_dir
 threading.Thread(target=server.serve_forever,name="price-hunter-dashboard",daemon=True).start()
 log.info("Dashboard server listening on %s:%s",host,port);return server
