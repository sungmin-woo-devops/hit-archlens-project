import re
from typing import Iterable

RE_PARENS = re.compile(r"\(.*?\)")
RE_MULTI_WS = re.compile(r"\s+")
DROP_WORDS = {"service", "services", "family"}

def canon(text: str) -> str:
    if not isinstance(text, str): return ""
    t = RE_PARENS.sub("", text)
    t = re.sub(r"^(amazon|aws)\s+", "", t, flags=re.I)
    t = t.replace("&","and").replace("–","-").replace("—","-")
    t = t.replace("-"," ").replace("_"," ").replace("/"," ")
    tokens = [w for w in re.split(r"\s+", t) if w]
    tokens = [w for w in tokens if w.lower() not in DROP_WORDS]
    t = " ".join(tokens)
    t = RE_MULTI_WS.sub(" ", t).strip().lower()
    return t

def tokenize(text: str):
    if not isinstance(text, str): return []
    import re
    t = text.replace("&","and")
    t = re.sub(r"[^0-9a-zA-Z]+", " ", t)
    return [w.lower() for w in t.split() if w]

def contains_blacklist(text: str, blacklist):
    key = canon(text)
    return any(b in key for b in blacklist)
