"""Smoke tests for private dashboard endpoints."""
import json,sqlite3,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from bot.dashboard import DashboardHandler
class DashboardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/"db.sqlite")
  with sqlite3.connect(self.db) as db:
   db.executescript("CREATE TABLE review_queue(id INTEGER,title TEXT,current_price REAL,currency TEXT,seller TEXT,url TEXT,source TEXT,shipping_cost REAL,condition TEXT,in_stock INTEGER,score INTEGER,discount_pct REAL,baseline_price REAL,reasons TEXT,status TEXT,created_at TEXT);CREATE TABLE price_observations(id INTEGER,product_key TEXT,title TEXT,price REAL,currency TEXT,seller TEXT,source TEXT,observed_at TEXT);CREATE TABLE watchlist(id INTEGER,query TEXT);CREATE TABLE settings(key TEXT,value TEXT);INSERT INTO price_observations VALUES(1,'k','Item',12,'EUR','Shop','test','2026-11-01');INSERT INTO settings VALUES('paused','false');INSERT INTO watchlist VALUES(1,'SSD');")
  self.token="dashboard-token-test-secret-long-123456";self.server=ThreadingHTTPServer(("127.0.0.1",0),DashboardHandler);self.server.token=self.token;self.server.db_path=self.db;self.server.web_dir=str(Path(__file__).parent.parent/"web");self.server.daemon_threads=True
  threading.Thread(target=self.server.serve_forever,daemon=True).start();self.base=f"http://127.0.0.1:{self.server.server_address[1]}"
 def tearDown(self):self.server.shutdown();self.server.server_close();self.tmp.cleanup()
 def get(self,path,token=None):
  req=urllib.request.Request(self.base+path)
  if token:req.add_header("Authorization","Bearer "+token)
  try:
   with urllib.request.urlopen(req) as r:return r.status,json.loads(r.read())
  except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
 def test_auth_required(self):self.assertEqual(401,self.get("/api/status")[0])
 def test_authenticated_status(self):
  code,data=self.get("/api/status",self.token);self.assertEqual(200,code);self.assertEqual(1,data["observations"]);self.assertEqual(["SSD"],data["watchlist"])
 def test_invalid_status(self):self.assertEqual(400,self.get("/api/offers?status=invalid",self.token)[0])
 def test_static_page(self):self.assertEqual(200,urllib.request.urlopen(self.base+"/").status)
if __name__=="__main__":unittest.main()
