"""SQLite price history, anomaly scoring, API budget guard and manual review queue."""
from __future__ import annotations
import sqlite3, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from statistics import median
from urllib.parse import urlparse

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def product_key(title, product_id=None):
    raw = (product_id or title or "").strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

class PriceEngine:
    def __init__(self, database_path):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db
    def _init_db(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS price_observations (
              id INTEGER PRIMARY KEY AUTOINCREMENT, product_key TEXT NOT NULL,
              title TEXT NOT NULL, price REAL NOT NULL CHECK(price > 0),
              currency TEXT NOT NULL, seller TEXT, url TEXT, source TEXT NOT NULL,
              shipping_cost REAL, condition TEXT, in_stock INTEGER,
              product_id TEXT, observed_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_observations_product_time ON price_observations(product_key, observed_at);
            CREATE TABLE IF NOT EXISTS api_budget (
              id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL, day TEXT NOT NULL,
              requests INTEGER NOT NULL DEFAULT 0, estimated_usd REAL NOT NULL DEFAULT 0,
              UNIQUE(provider, day)
            );
            CREATE TABLE IF NOT EXISTS review_queue (
              id INTEGER PRIMARY KEY AUTOINCREMENT, product_key TEXT NOT NULL,
              title TEXT NOT NULL, current_price REAL NOT NULL, currency TEXT NOT NULL,
              seller TEXT, url TEXT, source TEXT NOT NULL, shipping_cost REAL,
              condition TEXT, in_stock INTEGER, score INTEGER NOT NULL,
              discount_pct REAL, baseline_price REAL, reasons TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
              reviewed_at TEXT, review_note TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_review_status_created ON review_queue(status, created_at);
            """)
    def budget_status(self, provider="dataforseo", daily_request_limit=5, daily_usd_limit=1.0):
        day=datetime.now(timezone.utc).date().isoformat()
        with self._connect() as db:
            row=db.execute("SELECT requests,estimated_usd FROM api_budget WHERE provider=? AND day=?",(provider,day)).fetchone()
        req,usd=(row["requests"],row["estimated_usd"]) if row else (0,0.0)
        return {"provider":provider,"day":day,"requests_used":req,"estimated_usd":round(usd,6),
                "requests_limit":daily_request_limit,"usd_limit":daily_usd_limit,
                "allowed":req<daily_request_limit and usd<daily_usd_limit}
    def reserve_api_request(self, provider="dataforseo", estimated_cost_usd=0.001,
                            daily_request_limit=5, daily_usd_limit=1.0):
        if estimated_cost_usd<0: raise ValueError("estimated_cost_usd must be >= 0")
        day=datetime.now(timezone.utc).date().isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT requests,estimated_usd FROM api_budget WHERE provider=? AND day=?",(provider,day)).fetchone()
            req,usd=(row["requests"],row["estimated_usd"]) if row else (0,0.0)
            if req>=daily_request_limit or usd+estimated_cost_usd>daily_usd_limit: return False
            db.execute("""INSERT INTO api_budget(provider,day,requests,estimated_usd) VALUES(?,?,1,?)
              ON CONFLICT(provider,day) DO UPDATE SET requests=requests+1,estimated_usd=estimated_usd+excluded.estimated_usd""",(provider,day,estimated_cost_usd))
            return True
    def record_observation(self, *, title, price, currency="EUR", seller=None, url=None, source="unknown",
                          shipping_cost=None, condition=None, in_stock=None, product_id=None, observed_at=None):
        if not title or float(price)<=0 or not currency: raise ValueError("title, positive price and currency are required")
        if url and urlparse(url).scheme not in ("http","https"): raise ValueError("URL must use HTTP or HTTPS")
        stamp=observed_at or utcnow(); key=product_key(title,product_id)
        with self._connect() as db:
            cutoff=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()
            duplicate=db.execute("SELECT id FROM price_observations WHERE product_key=? AND price=? AND currency=? AND COALESCE(seller,'')=COALESCE(?, '') AND source=? AND observed_at>=? ORDER BY id DESC LIMIT 1",(key,float(price),currency.upper(),seller,source,cutoff)).fetchone()
            if duplicate:
                return duplicate["id"],key
            cur=db.execute("""INSERT INTO price_observations(product_key,title,price,currency,seller,url,source,shipping_cost,condition,in_stock,product_id,observed_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(key,title,float(price),currency.upper(),seller,url,source,shipping_cost,condition,None if in_stock is None else int(bool(in_stock)),product_id,stamp))
            return cur.lastrowid,key
    def history(self, product_key, days=90, limit=500):
        cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        with self._connect() as db:
            rows=db.execute("SELECT * FROM price_observations WHERE product_key=? AND observed_at>=? ORDER BY observed_at DESC LIMIT ?",(product_key,cutoff,limit)).fetchall()
        return [dict(r) for r in rows]
    def was_recently_queued(self, product_key, *, price, seller=None, hours=24):
        cutoff=(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat()
        with self._connect() as db:
            row=db.execute("SELECT id FROM review_queue WHERE product_key=? AND current_price=? AND COALESCE(seller,'')=COALESCE(?, '') AND created_at>=? AND status IN ('pending','approved') LIMIT 1",(product_key,float(price),seller,cutoff)).fetchone()
        return bool(row)
    def evaluate(self, observation_id, *, min_samples=5, lookback_days=90, peer_reference=None, peer_count=0):
        with self._connect() as db:
            obs=db.execute("SELECT * FROM price_observations WHERE id=?",(observation_id,)).fetchone()
        if not obs: raise KeyError(observation_id)
        history=self.history(obs["product_key"],days=lookback_days)
        prior=[float(r["price"]) for r in history if r["id"]!=observation_id]
        baseline=median(prior) if len(prior)>=min_samples else None
        if baseline is None and peer_reference and peer_count >= 2:
            baseline=float(peer_reference)
        discount=((baseline-obs["price"])/baseline*100) if baseline and obs["price"]<baseline else 0.0
        score=0; reasons=[]
        if baseline is None: reasons.append(f"Historique insuffisant ({len(prior)}/{min_samples} observations minimum)")
        else:
            score+=min(60,int(discount*1.5))
            reasons.append(f"{discount:.1f}% sous la médiane historique ({baseline:.2f} {obs['currency']})")
            if discount>=30: score+=15
            if discount>=50: score+=10
        if obs["seller"]: score+=5
        if obs["url"] and urlparse(obs["url"]).scheme in ("http","https"): score+=5
        if obs["condition"] and obs["condition"].lower() in ("new","neuf"): score+=10
        if obs["in_stock"]==1: score+=5
        if peer_reference and peer_count>=2:
            score+=min(20,5*int(peer_count))
            reasons.append(f"Comparaison vendeurs: {peer_count} vendeurs distincts; médiane {float(peer_reference):.2f} {obs['currency']}")
        elif peer_count==1:
            score+=5
            reasons.append("Une seule offre concurrente identifiée; corroboration limitée.")
        score=min(100,score)
        reasons.append("Signal heuristique uniquement : anomalie non confirmée.")
        with self._connect() as db:
            cur=db.execute("""INSERT INTO review_queue(product_key,title,current_price,currency,seller,url,source,shipping_cost,condition,in_stock,score,discount_pct,baseline_price,reasons,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(obs["product_key"],obs["title"],obs["price"],obs["currency"],obs["seller"],obs["url"],obs["source"],obs["shipping_cost"],obs["condition"],obs["in_stock"],score,discount,baseline," | ".join(reasons),"pending",utcnow()))
            return cur.lastrowid
    def list_review(self,status="pending",limit=10):
        with self._connect() as db:
            rows=db.execute("SELECT * FROM review_queue WHERE status=? ORDER BY score DESC,created_at ASC LIMIT ?",(status,limit)).fetchall()
        return [dict(r) for r in rows]
    def review(self,candidate_id,decision,note=None):
        if decision not in ("approved","rejected"): raise ValueError("decision must be approved or rejected")
        with self._connect() as db:
            cur=db.execute("UPDATE review_queue SET status=?,reviewed_at=?,review_note=? WHERE id=? AND status='pending'",(decision,utcnow(),note,candidate_id))
            return cur.rowcount>0
    def candidate(self,candidate_id):
        with self._connect() as db:
            row=db.execute("SELECT * FROM review_queue WHERE id=?",(candidate_id,)).fetchone()
        return dict(row) if row else None
