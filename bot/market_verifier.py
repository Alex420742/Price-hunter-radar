"""Merchant peer verification using independent seller domains in a single result batch.
This is corroborating marketplace evidence, not independent API/source verification.
"""
from __future__ import annotations
from statistics import median
from urllib.parse import urlparse
import re

def tokens(title):
    return {t for t in re.findall(r"[a-z0-9]+", (title or "").lower()) if len(t)>1}

def domain(url):
    try:
        host=(urlparse(url or "").hostname or "").lower()
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return ""

def similarity(a,b):
    ta,tb=tokens(a),tokens(b)
    return len(ta & tb)/len(ta | tb) if ta and tb else 0.0

def is_explicitly_new(item):
    condition=(getattr(item,"condition",None) or "").strip().lower()
    return condition in {"new","neuf","brand new","new in box"}

def verify_peers(candidates, min_similarity=0.65):
    """Return peer evidence for each item: median price, unique merchant domains and peer count."""
    evidence=[]
    for item in candidates:
        matches=[]
        target_domain=domain(item.product_url)
        for other in candidates:
            if other is item or not is_explicitly_new(other) or not other.product_url or not other.price or other.price<=0:
                continue
            other_domain=domain(other.product_url)
            if not other_domain or other_domain==target_domain:
                continue
            if similarity(item.title,other.title)>=min_similarity:
                matches.append(other)
        unique={}
        for m in matches:
            unique.setdefault(domain(m.product_url),m)
        prices=[float(m.price) for m in unique.values()]
        evidence.append({"peer_count":len(prices),"peer_domains":list(unique),"peer_median":median(prices) if prices else None})
    return evidence
