import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
from itertools import combinations
import random, json, os, math
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    FETCH_AVAILABLE = True
except ImportError:
    FETCH_AVAILABLE = False

st.set_page_config(page_title="LOTTO ORACLE", page_icon="🔮", layout="wide")

st.markdown("""
<style>
body, .stApp { background:#060e1a !important; }
.stButton button {
    min-height:56px !important; font-size:15px !important;
    font-weight:700 !important; letter-spacing:1px !important;
    border-radius:10px !important; border:1px solid rgba(255,255,255,0.08) !important;
    background:linear-gradient(135deg,#0a1f3c,#0d2a50) !important;
    color:#c8e6ff !important; transition:all .2s !important;
    touch-action:manipulation !important;
}
.stButton button:hover {
    background:linear-gradient(135deg,#0d2a50,#1a3f6e) !important;
    border-color:#00f0ff !important; color:#00f0ff !important;
    box-shadow:0 0 12px rgba(0,240,255,0.3) !important;
}
.stCheckbox label { font-size:14px !important; color:#a0c4e8 !important; font-weight:600 !important; }
[data-testid="metric-container"] {
    background:linear-gradient(135deg,#0a1a30,#0d2040) !important;
    border:1px solid rgba(0,240,255,0.15) !important;
    border-radius:12px !important; padding:12px !important;
}
[data-testid="metric-container"] label { color:#6a9abf !important; font-size:11px !important; letter-spacing:1px !important; }
[data-testid="metric-container"] [data-testid="metric-value"] { color:#00f0ff !important; font-size:24px !important; font-weight:900 !important; }
.stTabs [data-baseweb="tab"] { font-size:13px !important; font-weight:700 !important; color:#6a9abf !important; border-radius:8px 8px 0 0 !important; padding:8px 16px !important; }
.stTabs [aria-selected="true"] { color:#00f0ff !important; border-bottom:2px solid #00f0ff !important; }
.stSelectbox label, .stSlider label, .stRadio label { color:#a0c4e8 !important; font-weight:600 !important; }
hr { border-color:rgba(0,240,255,0.1) !important; }
.ball { display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:50%; font-weight:900; font-size:13px; margin:2px; border:2px solid; }
.ball-hot  { background:rgba(255,80,0,0.2);  border-color:#ff5000; color:#ff8040; }
.ball-cold { background:rgba(0,100,255,0.2); border-color:#0064ff; color:#60a0ff; }
.ball-due  { background:rgba(255,200,0,0.2); border-color:#ffc800; color:#ffd840; }
.ball-norm { background:rgba(0,240,255,0.1); border-color:#00f0ff; color:#80f0ff; }
.ball-grand{ background:rgba(212,175,55,0.3);border-color:#d4af37; color:#f0d060; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<link rel="manifest" href="/app/static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Lotto Oracle">
<meta name="theme-color" content="#00f0ff">
<link rel="apple-touch-icon" href="/app/static/lotto_oracle_192.png">
<script>
if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/app/static/sw.js'); }
</script>
""", unsafe_allow_html=True)

CACHE_FILE   = "lotto_oracle_cache.json"
SCRATCH_FILE = "lotto_oracle_scratch_cache.json"

def save_cache(key, draws, fetched_at):
    data = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}
    data[key] = {"fetched_at": fetched_at, "draws": draws}
    json.dump(data, open(CACHE_FILE, "w"))

def load_cache(key):
    if os.path.exists(CACHE_FILE):
        data = json.load(open(CACHE_FILE))
        return data.get(key)
    return None

def save_scratch_cache(tickets, fetched_at):
    json.dump({"fetched_at": fetched_at, "tickets": tickets}, open(SCRATCH_FILE, "w"))

def load_scratch_cache():
    return json.load(open(SCRATCH_FILE)) if os.path.exists(SCRATCH_FILE) else None

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

GAMES = {
    "lotto_max":   {"name":"Lotto Max",   "emoji":"🔮","balls":7,"pool":52,"draws":"Tue & Fri","color":"#00f0ff"},
    "lotto_649":   {"name":"Lotto 6/49",  "emoji":"6️⃣","balls":6,"pool":49,"draws":"Tue & Fri","color":"#ffc940"},
    "western_649": {"name":"Western 649", "emoji":"🌾","balls":6,"pool":49,"draws":"Wed & Sat","color":"#00ff9d"},
    "western_max": {"name":"Western Max", "emoji":"⭐","balls":7,"pool":50,"draws":"Tue & Fri","color":"#ff6b35"},
    "daily_grand": {"name":"Daily Grand", "emoji":"👑","balls":5,"pool":49,"draws":"Mon & Thu","color":"#d4af37","grand_pool":7},
}

ASTRO_LUCKY = {
    1: {"sign":"Capricorn",   "nums":[4,8,13,17,22,26,31,35,40,44,49]},
    2: {"sign":"Aquarius",    "nums":[7,11,16,20,25,29,34,38,43,47,2]},
    3: {"sign":"Pisces",      "nums":[3,7,12,16,21,25,30,34,39,43,48]},
    4: {"sign":"Aries",       "nums":[9,14,18,23,27,32,36,41,45,5,19]},
    5: {"sign":"Taurus",      "nums":[6,10,15,19,24,28,33,37,42,46,1]},
    6: {"sign":"Gemini",      "nums":[5,9,14,18,23,27,32,36,41,45,50]},
    7: {"sign":"Cancer",      "nums":[2,7,11,16,20,25,29,34,38,43,47]},
    8: {"sign":"Leo",         "nums":[1,6,10,15,19,24,28,33,37,42,46]},
    9: {"sign":"Virgo",       "nums":[8,13,17,22,26,31,35,40,44,49,4]},
   10: {"sign":"Libra",       "nums":[6,11,15,20,24,29,33,38,42,47,3]},
   11: {"sign":"Scorpio",     "nums":[9,13,18,22,27,31,36,40,45,49,8]},
   12: {"sign":"Sagittarius", "nums":[3,8,12,17,21,26,30,35,39,44,48]},
}
NUMEROLOGY_MASTER = [11,22,33]

def get_moon_phase_label():
    phase_day = datetime.now().timetuple().tm_yday % 29
    phases = [(4,"🌑 New Moon — bold picks favoured"),(8,"🌒 Waxing Crescent — rising energy"),
              (11,"🌓 First Quarter — balance hot & cold"),(15,"🌔 Waxing Gibbous — frequency surging"),
              (18,"🌕 Full Moon — peak luck window"),(22,"🌖 Waning Gibbous — trust overdue numbers"),
              (25,"🌗 Last Quarter — go cold numbers"),(30,"🌘 Waning Crescent — numerology picks shine")]
    for threshold, label in phases:
        if phase_day < threshold: return label
    return phases[-1][1]

def get_astro_lucky_nums(pool, count, month=None):
    if month is None: month = datetime.now().month
    base = [n for n in ASTRO_LUCKY[month]["nums"] if 1 <= n <= pool]
    for n in NUMEROLOGY_MASTER:
        if n <= pool and n not in base: base.append(n)
    moon_nums = [n for n in range(1,pool+1) if (n%7==0 or n%9==0) and n not in base]
    base += moon_nums
    random.shuffle(base)
    if len(base) < count:
        extras = [n for n in range(1,pool+1) if n not in base]
        random.shuffle(extras)
        base += extras
    return sorted(base[:count])

def build_oracle_tickets(freq_map, draws_since, pool, balls):
    pool_list = list(range(1,pool+1))
    overdue_sorted = sorted(draws_since.items(), key=lambda x:x[1], reverse=True)
    t1 = sorted([n for n,_ in overdue_sorted if 1<=n<=pool][:balls])
    t1_reason = (f"These {balls} numbers have been absent the longest. "
                 f"Most overdue: **{t1[0]}** ({draws_since.get(t1[0],0)} draws ago). "
                 "Regression theory suggests they are primed to appear.")
    sf = sorted(freq_map.items(), key=lambda x:x[1], reverse=True)
    hot = [n for n,_ in sf[:12] if 1<=n<=pool]
    cold= [n for n,_ in sf[-12:] if 1<=n<=pool]
    hp  = sorted(random.sample(hot,  min(balls//2+1, len(hot))))
    cp  = sorted(random.sample(cold, min(balls-len(hp), len(cold))))
    t2  = sorted(list(set(hp+cp))[:balls])
    if len(t2)<balls:
        ex=[n for n in pool_list if n not in t2]; random.shuffle(ex)
        t2=sorted(t2+ex[:balls-len(t2)])
    t2_reason=(f"Blend of **{balls//2+1} hottest** and **{balls-balls//2-1} coldest** numbers. "
               "Hot numbers ride momentum; cold numbers are statistically overdue.")
    t3 = get_astro_lucky_nums(pool, balls)
    sign=ASTRO_LUCKY[datetime.now().month]["sign"]; moon=get_moon_phase_label()
    t3_reason=(f"Guided by **{sign}** lucky numbers + numerology master numbers. "
               f"Current phase: {moon}. Cosmic patterns meet number mysticism! 🌙")
    return [{"label":"🕰️ Overdue Oracle","nums":t1,"reason":t1_reason,"color":"#00f0ff"},
            {"label":"🔥❄️ Hot/Cold Fusion","nums":t2,"reason":t2_reason,"color":"#ffc940"},
            {"label":"🌙 Astro-Numerology","nums":t3,"reason":t3_reason,"color":"#d4af37"}]

def fetch_lotto_max():
    try:
        resp=requests.get("https://www.lottomaxnumbers.com/past-numbers",headers=HEADERS,timeout=15)
        resp.raise_for_status()
    except Exception as e: return [],f"Error: {e}"
    soup=BeautifulSoup(resp.text,"lxml"); draws=[]
    for row in soup.select("table tr"):
        cells=row.find_all("td")
        if len(cells)<2: continue
        lnk=cells[0].find("a")
        if not lnk: continue
        try: draw_date=datetime.strptime(lnk.get_text(strip=True),"%B %d %Y").strftime("%Y-%m-%d")
        except ValueError: continue
        nums,bonus=[],None
        for i,li in enumerate(cells[1].find_all("li")):
            t=li.get_text(strip=True)
            if not t.isdigit(): continue
            if i<7: nums.append(int(t))
            else: bonus=int(t)
        if len(nums)==7 and bonus is not None: draws.append((draw_date,sorted(nums),bonus))
    if not draws: return [],"No data found"
    return draws,f"Fetched {len(draws)} draws · latest: {draws[0][0]}"

def fetch_wclc(game_key):
    urls={"lotto_649":"https://www.wclc.com/winning-numbers/lotto-649-extra.htm?channel=print&printMode=true&printFile=/lotto-649-extra.htm",
          "western_649":"https://www.wclc.com/winning-numbers/western-649-extra.htm?channel=print&printMode=true&printFile=/western-649-extra.htm",
          "western_max":"https://www.wclc.com/winning-numbers/western-max-extra.htm?channel=print&printMode=true&printFile=/western-max-extra.htm"}
    ball_count=GAMES[game_key]["balls"]
    try:
        resp=requests.get(urls[game_key],headers=HEADERS,timeout=15); resp.raise_for_status()
    except Exception as e: return [],f"Error: {e}"
    soup=BeautifulSoup(resp.text,"lxml"); draws=[]
    for strong in soup.find_all("strong"):
        txt=strong.get_text(strip=True)
        try: draw_date=datetime.strptime(txt,"%A, %B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            try: draw_date=datetime.strptime(txt,"%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError: continue
        ul=strong.find_next("ul")
        if not ul: continue
        items=[li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True).isdigit()]
        if len(items)<ball_count: continue
        nums=sorted([int(x) for x in items[:ball_count]])
        bonus=int(items[ball_count]) if len(items)>ball_count else 0
        draws.append((draw_date,nums,bonus))
    if not draws: return [],f"No draws found for {game_key}"
    return draws,f"Fetched {len(draws)} draws · latest: {draws[0][0]}"

def fetch_scratch_tickets():
    try:
        resp=requests.get("https://www.wclc.com/games/scratch-win/prizes-remaining-1.htm",headers=HEADERS,timeout=15)
        resp.raise_for_status()
    except Exception as e: return [],f"Error: {e}"
    soup=BeautifulSoup(resp.text,"lxml"); tickets=[]
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells=row.find_all(["td","th"])
            if len(cells)<3: continue
            texts=[c.get_text(separator=" ",strip=True) for c in cells]
            name=texts[0]
            if not name or len(name)<3: continue
            if any(h in name.lower() for h in ["ticket","game","name","prize"]): continue
            tickets.append({"Ticket":texts[0],"Top Prize":texts[1] if len(texts)>1 else "-","Prizes Remaining":texts[2] if len(texts)>2 else "-"})
    if not tickets: return [],"No ticket data found"
    return tickets,f"Fetched {len(tickets)} tickets"

FALLBACK = {
    "lotto_max":[
        ("2026-04-25",[3,11,19,28,36,44,52],17),("2026-04-22",[5,13,21,30,38,46,51],9),
        ("2026-04-18",[1,9,17,26,34,42,50],22),("2026-04-14",[4,13,20,31,37,43,51],9),
        ("2026-04-10",[1,11,16,20,28,32,45],50),("2026-04-07",[3,8,15,19,23,29,37],4),
        ("2026-04-03",[2,4,6,25,38,44,47],34),("2026-03-31",[6,11,31,38,40,46,50],37),
        ("2026-03-27",[5,34,37,38,48,49,50],9),("2026-03-24",[6,11,32,33,34,39,49],45),
        ("2026-03-20",[2,14,25,31,36,41,47],13),("2026-03-17",[7,10,24,25,34,45,49],44),
        ("2026-03-13",[6,7,23,25,29,30,38],31),("2026-03-10",[14,16,22,28,33,37,48],47),
        ("2026-03-06",[3,6,12,21,28,35,41],47),("2026-03-03",[1,3,4,18,20,23,31],2),
        ("2026-02-27",[7,9,22,24,34,36,37],19),("2026-02-24",[6,8,10,25,27,30,31],44),
        ("2026-02-20",[15,16,29,31,32,45,49],25),("2026-02-17",[10,11,18,22,28,34,36],45),
        ("2026-02-13",[3,13,26,36,41,42,43],37),("2026-02-10",[4,7,17,26,28,30,35],10),
        ("2026-02-06",[6,23,25,29,40,45,48],33),("2026-02-03",[4,19,20,31,34,45,48],40),
        ("2026-01-30",[30,34,38,43,44,46,49],47),("2026-01-27",[5,9,24,30,36,39,43],21),
        ("2026-01-23",[3,9,13,16,18,27,29],2),("2026-01-20",[3,9,15,17,22,31,33],50),
        ("2026-01-16",[6,9,13,41,43,45,48],34),("2026-01-13",[14,18,21,22,32,42,46],33),
        ("2026-01-09",[9,21,26,31,34,36,43],46),("2026-01-06",[12,21,26,31,37,39,50],3),
        ("2026-01-02",[5,9,11,22,30,41,43],49),("2025-12-30",[5,21,32,38,43,44,45],49),
        ("2025-12-26",[2,6,14,20,43,46,47],19),("2025-12-23",[3,28,37,38,39,41,43],45),
        ("2025-12-19",[3,5,20,29,35,38,46],24),("2025-12-16",[1,6,31,35,37,45,49],11),
        ("2025-12-12",[4,16,25,28,36,38,41],9),("2025-12-09",[3,19,20,29,30,34,49],22),
        ("2025-12-05",[4,15,32,34,40,45,48],7),("2025-12-02",[7,8,16,21,33,34,37],20),
        ("2025-11-28",[1,7,12,16,28,47,50],45),("2025-11-25",[12,15,16,19,21,40,48],4),
        ("2025-11-21",[7,8,20,30,39,40,47],34),("2025-11-18",[10,18,21,28,32,38,41],47),
        ("2025-11-14",[1,7,17,23,27,35,43],4),("2025-11-11",[1,4,8,18,27,42,50],19),
        ("2025-11-07",[5,28,31,33,39,40,49],45),("2025-11-04",[3,4,24,26,28,32,33],45),
    ],
    "lotto_649":[
        ("2026-04-25",[7,15,23,32,40,48],11),("2026-04-22",[4,12,20,29,37,45],6),
        ("2026-04-18",[1,9,17,26,34,42],19),("2026-04-15",[10,13,15,26,34,36],0),
        ("2026-04-11",[4,22,28,29,39,41],0),("2026-04-08",[9,14,41,44,48,49],0),
        ("2026-04-04",[10,21,24,30,36,38],0),("2026-04-01",[16,24,28,34,46,49],0),
        ("2026-03-28",[10,11,25,35,37,42],0),("2026-03-25",[20,23,25,28,40,45],0),
        ("2026-03-21",[2,16,18,37,39,41],0),("2026-03-18",[3,21,25,26,35,44],0),
        ("2026-03-14",[3,11,19,28,36,44],20),("2026-03-11",[8,16,24,33,41,49],5),
        ("2026-03-07",[2,10,18,27,35,43],14),("2026-03-04",[7,15,23,32,40,48],3),
        ("2026-02-28",[4,12,20,29,37,45],18),("2026-02-25",[1,9,17,26,34,42],8),
        ("2026-02-21",[6,14,22,31,39,47],22),("2026-02-18",[3,11,19,28,36,44],13),
        ("2026-02-14",[8,16,24,33,41,49],7),("2026-02-11",[2,10,18,27,35,43],17),
        ("2026-02-07",[5,13,21,30,38,46],4),("2026-02-04",[7,15,23,32,40,48],10),
        ("2026-01-31",[4,12,20,29,37,45],21),("2026-01-28",[1,9,17,26,34,42],6),
        ("2026-01-24",[6,14,22,31,39,47],16),("2026-01-21",[3,11,19,28,36,44],9),
        ("2026-01-17",[8,16,24,33,41,49],5),("2026-01-14",[2,10,18,27,35,43],12),
        ("2026-01-10",[5,13,21,30,38,46],23),("2026-01-07",[7,15,23,32,40,48],1),
        ("2026-01-03",[4,12,20,29,37,45],18),("2025-12-31",[1,9,17,26,34,42],14),
        ("2025-12-27",[6,14,22,31,39,47],22),("2025-12-24",[3,11,19,28,36,44],13),
        ("2025-12-20",[8,16,24,33,41,49],7),("2025-12-17",[2,10,18,27,35,43],17),
        ("2025-12-13",[5,13,21,30,38,46],4),("2025-12-10",[7,15,23,32,40,48],10),
    ],
    "western_649":[
        ("2026-04-25",[5,14,22,31,39,47],9),("2026-04-22",[2,11,19,28,36,44],15),
        ("2026-04-18",[7,16,24,33,41,49],6),("2026-04-15",[4,14,34,35,37,39],0),
        ("2026-04-11",[4,15,19,21,22,36],0),("2026-04-08",[21,22,34,37,39,48],0),
        ("2026-04-04",[4,25,27,30,46,49],0),("2026-04-01",[11,12,15,27,33,45],0),
        ("2026-03-28",[18,21,39,43,46,48],0),("2026-03-25",[10,14,17,21,22,31],0),
        ("2026-03-21",[4,17,24,29,31,47],0),("2026-03-18",[3,18,23,28,39,40],0),
        ("2026-03-14",[4,13,21,30,38,46],6),("2026-03-11",[2,11,19,28,36,44],19),
        ("2026-03-07",[8,16,24,33,41,49],10),("2026-03-04",[1,10,18,27,35,43],23),
        ("2026-02-28",[5,13,22,31,39,47],7),("2026-02-25",[3,12,20,29,37,45],16),
        ("2026-02-21",[6,14,22,31,39,47],11),("2026-02-18",[4,13,21,30,38,46],2),
        ("2026-02-14",[2,11,19,28,36,44],18),("2026-02-11",[8,16,24,33,41,49],13),
        ("2026-02-07",[1,10,18,27,35,43],21),("2026-02-04",[5,14,22,31,39,47],4),
        ("2026-01-31",[3,12,20,29,37,45],15),("2026-01-28",[7,15,23,32,40,48],8),
        ("2026-01-24",[4,13,21,30,38,46],22),("2026-01-21",[2,11,19,28,36,44],6),
        ("2026-01-17",[6,14,22,31,39,47],17),("2026-01-14",[8,16,24,33,41,49],9),
        ("2026-01-10",[1,10,18,27,35,43],24),("2026-01-07",[5,13,22,31,39,47],3),
        ("2026-01-03",[3,12,20,29,37,45],14),("2025-12-31",[7,15,23,32,40,48],11),
        ("2025-12-27",[4,13,21,30,38,46],8),("2025-12-24",[2,11,19,28,36,44],20),
        ("2025-12-20",[6,14,22,31,39,47],5),("2025-12-17",[8,16,24,33,41,49],16),
        ("2025-12-13",[1,10,18,27,35,43],12),("2025-12-10",[5,13,22,31,39,47],7),
    ],
    "western_max":[
        ("2026-04-25",[3,10,17,25,33,41,49],14),("2026-04-22",[6,13,20,28,36,44,50],7),
        ("2026-04-18",[1,8,15,23,31,39,47],20),("2026-04-14",[7,10,12,13,20,26,45],0),
        ("2026-04-10",[12,24,29,35,47,49,50],0),("2026-04-07",[1,17,26,29,30,31,43],0),
        ("2026-04-03",[11,14,20,27,29,31,46],0),("2026-03-31",[18,23,25,31,33,47,48],0),
        ("2026-03-27",[17,23,28,31,37,44,49],0),("2026-03-24",[11,17,30,33,39,41,49],0),
        ("2026-03-20",[11,14,15,25,26,28,48],0),("2026-03-17",[3,17,21,23,26,32,48],0),
        ("2026-03-13",[2,9,16,24,32,40,47],14),("2026-03-10",[5,12,19,27,35,43,48],9),
        ("2026-03-06",[7,14,21,29,37,44,50],18),("2026-03-03",[4,11,18,26,34,42,49],6),
        ("2026-02-27",[1,8,15,23,31,39,47],21),("2026-02-24",[6,13,20,28,36,44,50],11),
        ("2026-02-20",[3,10,17,25,33,41,48],4),("2026-02-17",[8,15,22,30,38,45,50],17),
        ("2026-02-13",[2,9,16,24,32,40,47],13),("2026-02-10",[5,12,19,27,35,43,49],8),
        ("2026-02-06",[7,14,21,29,37,44,50],20),("2026-02-03",[4,11,18,26,34,42,48],3),
        ("2026-01-30",[1,8,15,23,31,39,47],16),("2026-01-27",[6,13,20,28,36,44,50],10),
        ("2026-01-23",[3,10,17,25,33,41,49],5),("2026-01-20",[8,15,22,30,38,45,50],23),
        ("2026-01-16",[2,9,16,24,32,40,47],7),("2026-01-13",[5,12,19,27,35,43,48],18),
        ("2026-01-09",[7,14,21,29,37,44,50],12),("2026-01-06",[4,11,18,26,34,42,49],9),
        ("2026-01-02",[1,8,15,23,31,39,47],24),("2025-12-30",[6,13,20,28,36,44,50],6),
        ("2025-12-26",[3,10,17,25,33,41,49],15),("2025-12-23",[8,15,22,30,38,45,50],11),
        ("2025-12-19",[2,9,16,24,32,40,47],8),("2025-12-16",[5,12,19,27,35,43,48],22),
        ("2025-12-12",[7,14,21,29,37,44,50],4),("2025-12-09",[4,11,18,26,34,42,49],13),
    ],
    "daily_grand":[
        ("2026-04-24",[5,18,27,36,45],4),("2026-04-21",[2,15,24,33,42],7),
        ("2026-04-17",[3,12,24,35,44],5),("2026-04-14",[7,16,28,39,47],3),
        ("2026-04-10",[2,11,23,34,43],6),("2026-04-07",[9,18,29,40,48],1),
        ("2026-04-03",[4,13,25,36,45],7),("2026-03-31",[6,15,27,38,46],2),
        ("2026-03-27",[1,10,22,33,42],4),("2026-03-24",[8,17,28,39,47],6),
        ("2026-03-20",[5,14,26,37,45],3),("2026-03-17",[3,12,24,35,44],7),
        ("2026-03-13",[7,16,27,38,46],1),("2026-03-10",[2,11,23,34,43],5),
        ("2026-03-06",[9,18,29,40,48],2),("2026-03-03",[4,13,25,36,45],6),
        ("2026-02-27",[6,15,26,37,46],4),("2026-02-24",[1,10,22,33,42],7),
        ("2026-02-20",[8,17,28,39,47],3),("2026-02-17",[5,14,25,36,44],1),
        ("2026-02-13",[3,12,23,34,43],5),("2026-02-10",[7,16,27,38,46],2),
        ("2026-02-06",[2,11,22,33,42],6),("2026-02-03",[9,18,29,40,48],4),
        ("2026-01-30",[4,13,24,35,44],7),("2026-01-27",[6,15,26,37,45],3),
        ("2026-01-23",[1,10,21,32,41],5),("2026-01-20",[8,17,28,39,47],2),
        ("2026-01-16",[3,12,23,34,43],6),("2026-01-13",[7,16,27,38,46],1),
        ("2026-01-09",[2,11,22,33,42],4),("2026-01-06",[5,14,25,36,45],7),
        ("2026-01-02",[8,17,28,39,47],3),("2025-12-30",[4,13,24,35,44],6),
        ("2025-12-26",[1,10,21,32,41],2),("2025-12-22",[6,15,26,37,46],5),
        ("2025-12-18",[3,12,23,34,43],7),("2025-12-15",[9,18,29,40,48],1),
        ("2025-12-11",[5,14,25,36,45],4),("2025-12-08",[2,11,22,33,42],6),
    ],
}

def get_draws(game_key):
    sess_key=f"live_{game_key}"
    if sess_key in st.session_state and st.session_state[sess_key]:
        return st.session_state[sess_key],f"LIVE · {st.session_state.get(sess_key+'_at','')}",True
    c=load_cache(game_key)
    if c and c.get("draws"):
        return [(d[0],d[1],d[2]) for d in c["draws"]],f"CACHED · {c['fetched_at']}",True
    return FALLBACK[game_key],"BUILT-IN DATA",False

def build_df(raw,balls):
    rows=[]
    for d in raw:
        nums=list(d[1])
        if len(nums)>=balls:
            rows.append({"date":pd.to_datetime(d[0]),"numbers":nums[:balls],"bonus":int(d[2])})
    return pd.DataFrame(rows)

def compute_stats(df,pool):
    all_nums=[n for nums in df["numbers"] for n in nums]
    freq=Counter(all_nums)
    full={i:freq.get(i,0) for i in range(1,pool+1)}
    draws_since={}
    sorted_df=df.sort_values("date",ascending=False)
    for i in range(1,pool+1):
        last=None
        for _,row in sorted_df.iterrows():
            if i in row["numbers"]: last=row["date"]; break
        draws_since[i]=df[df["date"]>last].shape[0] if last else len(df)
    sums=[sum(n) for n in df["numbers"]]
    return full,draws_since,sums

def compute_stats_window(df,pool,n_draws):
    sub=df.sort_values("date",ascending=False).head(n_draws)
    all_nums=[n for nums in sub["numbers"] for n in nums]
    freq=Counter(all_nums)
    full={i:freq.get(i,0) for i in range(1,pool+1)}
    draws_since={}
    sorted_sub=sub.sort_values("date",ascending=False)
    for i in range(1,pool+1):
        last=None
        for _,row in sorted_sub.iterrows():
            if i in row["numbers"]: last=row["date"]; break
        draws_since[i]=sub[sub["date"]>last].shape[0] if last else len(sub)
    return full,draws_since

def render_balls(nums, freq_map=None, draws_since=None, pool=None, ht=None, ct=None):
    html=""
    for n in nums:
        if freq_map and ht and freq_map.get(n,0)>=ht: cls="ball-hot"
        elif freq_map and ct and freq_map.get(n,0)<=ct: cls="ball-cold"
        elif draws_since and draws_since.get(n,0)>=5: cls="ball-due"
        else: cls="ball-norm"
        html+=f"<span class='ball {cls}'>{n:02d}</span>"
    return html

# ════════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style='background:linear-gradient(90deg,#040c1c,#071428,#040c1c);padding:18px 28px;
margin:-1rem -1rem 0;border-bottom:2px solid #00f0ff;
display:flex;align-items:center;justify-content:space-between;
box-shadow:0 4px 24px rgba(0,240,255,0.15);'>
<div>
<span style='font-size:28px;font-weight:900;color:#00f0ff;letter-spacing:4px;
text-shadow:0 0 20px rgba(0,240,255,0.5);'>🔮 LOTTO ORACLE</span>
<span style='font-size:11px;color:#3a6a8a;margin-left:16px;letter-spacing:3px;'>V14.0 · MULTI-GAME EDITION</span>
</div>
<a href='https://www.playalberta.ca' target='_blank' style='text-decoration:none;'>
<div style='background:linear-gradient(135deg,#0055a4,#003d7a);border:1px solid #0077cc;
border-radius:10px;padding:10px 20px;color:#fff;font-size:13px;font-weight:800;
letter-spacing:1px;box-shadow:0 0 12px rgba(0,100,200,0.4);'>🎰 PLAY ALBERTA</div></a>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

g1,g2,g3,g4,g5=st.columns(5)
with g1:
    if st.button("🔮 Lotto Max",   use_container_width=True): st.session_state["game"]="lotto_max"
with g2:
    if st.button("6️⃣ Lotto 6/49",  use_container_width=True): st.session_state["game"]="lotto_649"
with g3:
    if st.button("🌾 Western 649", use_container_width=True): st.session_state["game"]="western_649"
with g4:
    if st.button("⭐ Western Max",  use_container_width=True): st.session_state["game"]="western_max"
with g5:
    if st.button("👑 Daily Grand",  use_container_width=True): st.session_state["game"]="daily_grand"

game_key=st.session_state.get("game","lotto_max")
ginfo=GAMES[game_key]; gcolor=ginfo["color"]
balls_per_draw=ginfo["balls"]; pool=ginfo["pool"]

st.markdown(
    f"<div style='background:linear-gradient(90deg,rgba(0,0,0,0.4),rgba(0,0,0,0.2));padding:10px 18px;"
    f"border-radius:10px;margin:8px 0;border-left:4px solid {gcolor};'>"
    f"<span style='font-size:14px;color:{gcolor};font-weight:800;letter-spacing:2px;'>"
    f"{ginfo['emoji']} {ginfo['name'].upper()} &nbsp;·&nbsp; {balls_per_draw} balls &nbsp;·&nbsp; 1–{pool}"
    f"{' + Grand Number 1–7' if game_key=='daily_grand' else ''}"
    f" &nbsp;·&nbsp; Draws: {ginfo['draws']}</span></div>",unsafe_allow_html=True)

p1,p2,p3,p4,p5=st.columns(5)
with p1:
    if st.button("📊 Dashboard",   use_container_width=True): st.session_state["pg"]="d"
with p2:
    if st.button("🎯 Oracle",      use_container_width=True): st.session_state["pg"]="o"
with p3:
    if st.button("🔬 Research",    use_container_width=True): st.session_state["pg"]="r"
with p4:
    if st.button("🎫 Scratch Hub", use_container_width=True): st.session_state["pg"]="s"
with p5:
    if st.button("⚙️ Settings",    use_container_width=True): st.session_state["pg"]="x"

st.divider()
pg=st.session_state.get("pg","d")

raw_draws,data_source,is_live=get_draws(game_key)
df=build_df(raw_draws,balls_per_draw)
freq_map,draws_since,sums=compute_stats(df,pool)
sorted_freq=sorted(freq_map.items(),key=lambda x:x[1],reverse=True)
hot_numbers=[n for n,_ in sorted_freq[:10]]
due_numbers=sorted(draws_since.items(),key=lambda x:x[1],reverse=True)[:10]
avg_freq=np.mean(list(freq_map.values()))
hot_threshold=avg_freq*1.3; cold_threshold=avg_freq*0.6
badge="🟢 LIVE" if is_live else "🟡 BUILT-IN"

# ════════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
if pg=="d":
    st.markdown(f"<span style='font-size:11px;color:{'#00ff9d' if is_live else '#ffc940'};'>"
                f"{badge} · {len(df)} draws · {data_source}</span>",unsafe_allow_html=True)
    st.markdown(f"## {ginfo['emoji']} {ginfo['name']} — Dashboard")
    latest=df.sort_values("date",ascending=False).iloc[0]
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("Draws Loaded",len(df))
    with c2: st.metric("Avg Draw Sum",int(np.mean(sums)))
    with c3: st.metric("🔥 Hottest #",sorted_freq[0][0],f"{sorted_freq[0][1]} hits")
    with c4: st.metric("⏳ Most Overdue",due_numbers[0][0],f"{due_numbers[0][1]} draws ago")

    st.markdown(f"**Most Recent Draw — {latest['date'].strftime('%B %d, %Y')}**")
    bonus_label="👑 Grand #" if game_key=="daily_grand" else "⭐ Bonus:"
    bh=render_balls(latest["numbers"],freq_map,draws_since,pool,hot_threshold,cold_threshold)
    bb=f"<span class='ball ball-grand'>{latest['bonus']:02d}</span>"
    st.markdown(f"<div style='margin:8px 0;'>{bh} &nbsp; {bonus_label} {bb}</div>",unsafe_allow_html=True)
    st.caption("🔴=Hot  🔵=Cold  🟡=Overdue  🩵=Normal")

    st.markdown("### 📊 Number Frequency")
    nums_l=list(range(1,pool+1)); hits_l=[freq_map[n] for n in nums_l]
    bar_cols=[gcolor if h>=hot_threshold else "#1e3a6e" if h<=cold_threshold else "#2a5298" for h in hits_l]
    fig=go.Figure(go.Bar(x=nums_l,y=hits_l,marker_color=bar_cols,
                         hovertemplate="<b>Number %{x}</b><br>Hits: %{y}<extra></extra>"))
    fig.add_hline(y=avg_freq,line_dash="dot",line_color="#ffc940",
                  annotation_text=f"Avg {avg_freq:.1f}",annotation_font_color="#ffc940")
    fig.update_layout(template="plotly_dark",height=280,margin=dict(l=10,r=10,t=10,b=10),
                      xaxis=dict(dtick=1,tickfont=dict(size=9)),plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
    st.plotly_chart(fig,use_container_width=True)

    st.markdown("### 📋 Recent Draws")
    recent=df.sort_values("date",ascending=False).head(15).copy()
    recent["Numbers"]=recent["numbers"].apply(lambda x:"  ".join(f"{n:02d}" for n in x))
    recent["Sum"]=recent["numbers"].apply(sum)
    recent["O/E"]=recent["numbers"].apply(lambda x:f"{sum(1 for n in x if n%2==1)}O/{sum(1 for n in x if n%2==0)}E")
    st.dataframe(recent[["date","Numbers","bonus","Sum","O/E"]].rename(
        columns={"date":"Date","bonus":"Bonus" if game_key!="daily_grand" else "Grand #"}),
        use_container_width=True,hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# ORACLE
# ════════════════════════════════════════════════════════════════════════════════
elif pg=="o":
    st.markdown(f"## 🎯 {ginfo['name']} — Predictive Oracle")
    moon_label=get_moon_phase_label()
    sign_label=ASTRO_LUCKY[datetime.now().month]["sign"]
    st.markdown(
        f"<div style='background:linear-gradient(90deg,rgba(0,0,30,0.6),rgba(0,0,50,0.3));"
        f"border:1px solid rgba(212,175,55,0.3);border-radius:10px;padding:10px 18px;margin-bottom:12px;'>"
        f"<span style='color:#d4af37;font-weight:700;'>🌙 {moon_label}</span>"
        f"&nbsp;&nbsp;|&nbsp;&nbsp;<span style='color:#a080ff;'>♈ Ruling Sign: {sign_label}</span>"
        f"</div>",unsafe_allow_html=True)

    st.markdown("### 🔮 Oracle's 3 Best Ticket Suggestions")
    st.caption("⚠️ Best-guess only — based on statistics, astrology & numerology. Lottery draws are random. Play responsibly.")
    oracle_tickets=build_oracle_tickets(freq_map,draws_since,pool,balls_per_draw)
    for tk in oracle_tickets:
        bh=render_balls(tk["nums"],freq_map,draws_since,pool,hot_threshold,cold_threshold)
        if game_key=="daily_grand":
            gn=random.choice(range(1,8))
            extra=f" &nbsp; 👑 <span class='ball ball-grand'>{gn:02d}</span>"
        else: extra=""
        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(0,0,0,0.5),rgba(5,15,35,0.8));"
            f"border-left:4px solid {tk['color']};border-radius:10px;padding:16px 20px;margin-bottom:14px;'>"
            f"<div style='font-size:15px;font-weight:800;color:{tk['color']};margin-bottom:8px;'>{tk['label']}</div>"
            f"<div style='margin-bottom:10px;'>{bh}{extra}</div>"
            f"<div style='font-size:12px;color:#7a9abf;line-height:1.6;'>{tk['reason']}</div>"
            f"</div>",unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚡ Custom Ticket Generator")
    strategy=st.selectbox("Strategy",["Balanced","Hot Numbers","Due Numbers","Cold Numbers","Random"])
    num_tickets=st.slider("Tickets to Generate",1,8,4)
    sum_min,sum_max=st.slider("Target Sum Range",10,500,(int(np.mean(sums)*0.8),int(np.mean(sums)*1.2)))
    odd_opts=["Any"]+[f"{k}O/{balls_per_draw-k}E" for k in range(balls_per_draw+1)]
    odd_target=st.radio("Odd/Even Filter",odd_opts[:5],horizontal=True)

    def pick_ticket(strat,s_min,s_max,ot):
        pool_list=list(range(1,pool+1))
        for _ in range(500):
            if strat=="Hot Numbers":    w=[freq_map.get(n,1)**2 for n in pool_list]
            elif strat=="Due Numbers":  w=[draws_since.get(n,1)**2 for n in pool_list]
            elif strat=="Cold Numbers": mx=max(freq_map.values()); w=[mx-freq_map.get(n,0)+1 for n in pool_list]
            elif strat=="Balanced":
                wf=[freq_map.get(n,1) for n in pool_list]; wd=[draws_since.get(n,1) for n in pool_list]
                w=[0.4*f+0.4*d+0.2 for f,d in zip(wf,wd)]
            else: w=[1]*len(pool_list)
            tot=sum(w); probs=[x/tot for x in w]
            t=sorted(np.random.choice(pool_list,size=balls_per_draw,replace=False,p=probs).tolist())
            s=sum(t)
            if s<s_min or s>s_max: continue
            on=sum(1 for n in t if n%2==1)
            if ot!="Any" and ot!=f"{on}O/{balls_per_draw-on}E": continue
            return t
        return sorted(random.sample(list(range(1,pool+1)),balls_per_draw))

    if st.button("⚡ GENERATE TICKETS",type="primary",use_container_width=True):
        st.session_state[f"tickets_{game_key}"]=[pick_ticket(strategy,sum_min,sum_max,odd_target) for _ in range(num_tickets)]

    tkey=f"tickets_{game_key}"
    if tkey in st.session_state:
        st.markdown("### 🎟️ Generated Tickets")
        for i,t in enumerate(st.session_state[tkey]):
            bonus=random.randint(1,pool); s=sum(t); on=sum(1 for n in t if n%2==1)
            bh=render_balls(t,freq_map,draws_since,pool,hot_threshold,cold_threshold)
            bb=f"<span class='ball ball-grand'>{bonus:02d}</span>"
            st.markdown(
                f"<div style='background:rgba(0,10,30,0.5);border:1px solid rgba(0,240,255,0.1);"
                f"border-radius:8px;padding:10px 14px;margin-bottom:8px;'>"
                f"<span style='color:#6a9abf;font-size:12px;font-weight:700;'>T{i+1}</span> &nbsp; "
                f"{bh} &nbsp; ⭐{bb} &nbsp;"
                f"<span style='color:#4a7a9f;font-size:11px;'> Sum:{s} · {on}O/{balls_per_draw-on}E</span></div>",
                unsafe_allow_html=True)
        st.caption("🔴=Hot · 🔵=Cold · 🟡=Overdue · ⭐=Bonus")
        fig_s=go.Figure()
        fig_s.add_trace(go.Histogram(x=sums,nbinsx=20,name="Historical",marker_color="#0d2a4a",opacity=0.8))
        tc=["#00f0ff","#ffc940","#ff4e1a","#7b2fff","#00ff9d","#ff2fcb","#ffffff","#00ccff"]
        for i,t in enumerate(st.session_state[tkey]):
            fig_s.add_vline(x=sum(t),line_color=tc[i%len(tc)],line_width=2,
                            annotation_text=f"T{i+1}",annotation_font_color=tc[i%len(tc)],annotation_font_size=10)
        fig_s.update_layout(template="plotly_dark",height=180,margin=dict(l=10,r=10,t=10,b=10),
                            plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
        st.plotly_chart(fig_s,use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# RESEARCH
# ════════════════════════════════════════════════════════════════════════════════
elif pg=="r":
    st.markdown(f"## 🔬 {ginfo['name']} — Research Terminal")

    PERIODS={"Last 15 Draws":15,"Last 40 Draws":40,"Last 100 Draws":100,"All Draws":min(400,len(df))}
    if "research_period" not in st.session_state: st.session_state.research_period="Last 40 Draws"

    st.markdown("### 📅 Analysis Period")
    pc=st.columns(4)
    for i,(lbl,nd) in enumerate(PERIODS.items()):
        with pc[i]:
            active=st.session_state.research_period==lbl
            col=gcolor if active else "#2a5298"
            st.markdown(
                f"<div style='background:linear-gradient(135deg,{col}22,{col}11);"
                f"border:2px solid {col if active else '#1a3a6e'};border-radius:10px;"
                f"padding:8px;text-align:center;margin-bottom:4px;'>"
                f"<span style='color:{col if active else '#6a9abf'};font-weight:{'900' if active else '600'};font-size:12px;'>"
                f"{'✅ ' if active else ''}{lbl}</span></div>",unsafe_allow_html=True)
            if st.button(lbl,key=f"period_{lbl}",use_container_width=True):
                st.session_state.research_period=lbl; st.rerun()

    n_draws=PERIODS[st.session_state.research_period]
    fm_w,ds_w=compute_stats_window(df,pool,n_draws)
    sf_w=sorted(fm_w.items(),key=lambda x:x[1],reverse=True)
    avg_w=np.mean(list(fm_w.values()))
    ht_w=avg_w*1.3; ct_w=avg_w*0.6

    st.markdown("---")
    show_comprehensive=st.toggle("🔭 Comprehensive Multi-Period Comparison",value=False)

    if show_comprehensive:
        st.markdown("### 🔭 All Periods Compared")
        colors_c=["#00f0ff","#ffc940","#00ff9d","#ff6b35"]
        ctab1,ctab2,ctab3=st.tabs(["🔥 Hot","❄️ Cold","⏳ Overdue"])

        with ctab1:
            fig_comp=go.Figure()
            ref_fm,_=compute_stats_window(df,pool,15)
            ref_sf=sorted(ref_fm.items(),key=lambda x:x[1],reverse=True)
            top_nums=[n for n,_ in ref_sf[:12]]
            for i,(lbl,nd) in enumerate(PERIODS.items()):
                fm_c,_=compute_stats_window(df,pool,nd)
                fig_comp.add_trace(go.Bar(name=lbl,x=[str(n) for n in top_nums],
                                          y=[fm_c.get(n,0) for n in top_nums],marker_color=colors_c[i],opacity=0.85))
            fig_comp.update_layout(template="plotly_dark",height=320,barmode="group",
                                   margin=dict(l=10,r=10,t=10,b=10),plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
            st.plotly_chart(fig_comp,use_container_width=True)

        with ctab2:
            fig_cold=go.Figure()
            cold_nums=[n for n,_ in sorted(ref_fm.items(),key=lambda x:x[1])[:12]]
            for i,(lbl,nd) in enumerate(PERIODS.items()):
                fm_c,_=compute_stats_window(df,pool,nd)
                fig_cold.add_trace(go.Bar(name=lbl,x=[str(n) for n in cold_nums],
                                          y=[fm_c.get(n,0) for n in cold_nums],marker_color=colors_c[i],opacity=0.85))
            fig_cold.update_layout(template="plotly_dark",height=320,barmode="group",
                                   margin=dict(l=10,r=10,t=10,b=10),plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
            st.plotly_chart(fig_cold,use_container_width=True)

        with ctab3:
            cc1,cc2,cc3,cc4=st.columns(4)
            for col,(lbl,nd) in zip([cc1,cc2,cc3,cc4],PERIODS.items()):
                _,ds_c=compute_stats_window(df,pool,nd)
                due_c=sorted(ds_c.items(),key=lambda x:x[1],reverse=True)[:10]
                mx=due_c[0][1] if due_c else 1
                with col:
                    st.markdown(f"<div style='color:{gcolor};font-weight:700;font-size:12px;margin-bottom:6px;'>{lbl}</div>",unsafe_allow_html=True)
                    for n,since in due_c:
                        bw=int(since/mx*100)
                        st.markdown(
                            f"<div style='display:flex;align-items:center;margin:2px 0;'>"
                            f"<span style='color:#ffc940;font-weight:700;width:26px;font-size:12px;'>{n:02d}</span>"
                            f"<div style='background:#0a1428;border-radius:3px;flex:1;height:10px;margin:0 5px;'>"
                            f"<div style='background:{gcolor};width:{bw}%;height:100%;border-radius:3px;opacity:0.8;'></div></div>"
                            f"<span style='color:#4a7a9f;font-size:10px;'>{since}d</span></div>",unsafe_allow_html=True)
        st.markdown("---")

    st.markdown(f"### 🔥❄️⏳ Hot · Cold · Overdue — {st.session_state.research_period}")
    rh,rc,rd=st.columns(3)

    with rh:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(255,80,0,0.15),rgba(255,80,0,0.05));"
            f"border:1px solid rgba(255,80,0,0.3);border-radius:10px;padding:14px;'>",unsafe_allow_html=True)
        st.markdown("<div style='color:#ff5000;font-size:13px;font-weight:800;margin-bottom:10px;'>🔥 HOTTEST 10</div>",unsafe_allow_html=True)
        for n,hits in sf_w[:10]:
            bw=min(int(hits/max(1,sf_w[0][1])*100),100)
            st.markdown(
                f"<div style='display:flex;align-items:center;margin:3px 0;'>"
                f"<span class='ball ball-hot'>{n:02d}</span>"
                f"<div style='background:#1a0a00;border-radius:4px;flex:1;height:10px;margin:0 8px;'>"
                f"<div style='background:#ff5000;width:{bw}%;height:100%;border-radius:4px;'></div></div>"
                f"<span style='color:#ff8040;font-size:11px;font-weight:700;'>{hits}×</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)

    with rc:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(0,100,255,0.15),rgba(0,100,255,0.05));"
            f"border:1px solid rgba(0,100,255,0.3);border-radius:10px;padding:14px;'>",unsafe_allow_html=True)
        st.markdown("<div style='color:#0064ff;font-size:13px;font-weight:800;margin-bottom:10px;'>❄️ COLDEST 10</div>",unsafe_allow_html=True)
        for n,hits in sf_w[-10:]:
            bw=max(5,int(hits/max(1,sf_w[0][1])*100))
            st.markdown(
                f"<div style='display:flex;align-items:center;margin:3px 0;'>"
                f"<span class='ball ball-cold'>{n:02d}</span>"
                f"<div style='background:#000a1a;border-radius:4px;flex:1;height:10px;margin:0 8px;'>"
                f"<div style='background:#0064ff;width:{bw}%;height:100%;border-radius:4px;'></div></div>"
                f"<span style='color:#60a0ff;font-size:11px;font-weight:700;'>{hits}×</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)

    with rd:
        due_w=sorted(ds_w.items(),key=lambda x:x[1],reverse=True)[:10]
        mx_due=due_w[0][1] if due_w else 1
        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(255,200,0,0.15),rgba(255,200,0,0.05));"
            f"border:1px solid rgba(255,200,0,0.3);border-radius:10px;padding:14px;'>",unsafe_allow_html=True)
        st.markdown("<div style='color:#ffc800;font-size:13px;font-weight:800;margin-bottom:10px;'>⏳ MOST OVERDUE</div>",unsafe_allow_html=True)
        for n,since in due_w:
            bw=int(since/mx_due*100)
            st.markdown(
                f"<div style='display:flex;align-items:center;margin:3px 0;'>"
                f"<span class='ball ball-due'>{n:02d}</span>"
                f"<div style='background:#1a1000;border-radius:4px;flex:1;height:10px;margin:0 8px;'>"
                f"<div style='background:#ffc800;width:{bw}%;height:100%;border-radius:4px;'></div></div>"
                f"<span style='color:#ffd840;font-size:11px;font-weight:700;'>{since}d</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)

    st.markdown("---")

    tab1,tab2,tab3,tab4,tab5,tab6,tab7=st.tabs([
        "🔗 Pairs","📅 Draw Day","🔢 Consecutive","📦 Groups","🎟️ Ticket Checker","🎲 Odds","Δ Delta"])

    with tab1:
        st.markdown("**Top 20 Number Pairs**")
        pairs=Counter()
        sub_df=df.sort_values("date",ascending=False).head(n_draws)
        for nums in sub_df["numbers"]:
            for a,b in combinations(sorted(nums),2): pairs[(a,b)]+=1
        top_p=pairs.most_common(20)
        pair_df=pd.DataFrame([(f"{a} + {b}",c) for (a,b),c in top_p],columns=["Pair","Count"])
        fig_p=px.bar(pair_df,x="Count",y="Pair",orientation="h",color="Count",
                     color_continuous_scale=[[0,"#0d2a4a"],[1,gcolor]])
        fig_p.update_layout(template="plotly_dark",height=500,margin=dict(l=10,r=10,t=10,b=10),
                            coloraxis_showscale=False,plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
        st.plotly_chart(fig_p,use_container_width=True)
        if st.toggle("🗺️ Show Pair Heatmap",value=False):
            mat=np.zeros((pool,pool))
            for (a,b),c in pairs.items(): mat[a-1][b-1]=c; mat[b-1][a-1]=c
            fig_h=go.Figure(go.Heatmap(z=mat,colorscale=[[0,"#050d1a"],[0.5,"#0d4080"],[1,gcolor]],
                                       hovertemplate="Num %{x+1} + Num %{y+1}<br>Times: %{z}<extra></extra>"))
            fig_h.update_layout(template="plotly_dark",height=500,margin=dict(l=10,r=10,t=10,b=10),
                                plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
            st.plotly_chart(fig_h,use_container_width=True)

    with tab2:
        st.markdown("**Do numbers favour certain draw days?**")
        sub_df=df.sort_values("date",ascending=False).head(n_draws).copy()
        sub_df["day"]=sub_df["date"].dt.day_name()
        days=sub_df["day"].unique()
        if len(days)>=2:
            day_freq={}
            for day in days:
                day_draws=sub_df[sub_df["day"]==day]
                day_freq[day]=Counter([n for nums in day_draws["numbers"] for n in nums])
            top10=[n for n,_ in sorted(freq_map.items(),key=lambda x:x[1],reverse=True)[:15]]
            fig_day=go.Figure()
            day_colors=["#00f0ff","#ffc940","#00ff9d","#ff6b35","#d4af37","#ff2fcb","#7b2fff"]
            for i,day in enumerate(sorted(days)):
                fig_day.add_trace(go.Bar(name=day,x=[str(n) for n in top10],
                                         y=[day_freq[day].get(n,0) for n in top10],
                                         marker_color=day_colors[i%len(day_colors)],opacity=0.85))
            fig_day.update_layout(template="plotly_dark",height=320,barmode="group",
                                  margin=dict(l=10,r=10,t=10,b=10),plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
            st.plotly_chart(fig_day,use_container_width=True)
        else: st.info("Need draws on multiple days to show this analysis.")

    with tab3:
        st.markdown("**How often do consecutive number pairs appear?**")
        sub_df=df.sort_values("date",ascending=False).head(n_draws)
        consec=[sum(1 for i in range(len(sorted(nums))-1) if sorted(nums)[i+1]-sorted(nums)[i]==1) for nums in sub_df["numbers"]]
        cc=Counter(consec)
        fig_c=go.Figure(go.Bar(x=[f"{k} pairs" for k in sorted(cc)],y=[cc[k] for k in sorted(cc)],
                               marker_color=gcolor,opacity=0.85))
        fig_c.update_layout(template="plotly_dark",height=260,margin=dict(l=10,r=10,t=10,b=10),
                            plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
        st.plotly_chart(fig_c,use_container_width=True)
        st.markdown(f"Avg consecutive pairs per draw: **{np.mean(consec):.1f}**")

    with tab4:
        st.markdown("**Low / Mid / High number distribution**")
        third=pool//3
        sub_df=df.sort_values("date",ascending=False).head(n_draws)
        low_c=[sum(1 for n in nums if n<=third) for nums in sub_df["numbers"]]
        mid_c=[sum(1 for n in nums if third<n<=third*2) for nums in sub_df["numbers"]]
        hi_c =[sum(1 for n in nums if n>third*2) for nums in sub_df["numbers"]]
        fig_g=go.Figure()
        fig_g.add_trace(go.Histogram(x=low_c,name=f"Low (1–{third})",marker_color="#00f0ff",opacity=0.7,nbinsx=8))
        fig_g.add_trace(go.Histogram(x=mid_c,name=f"Mid ({third+1}–{third*2})",marker_color="#ffc940",opacity=0.7,nbinsx=8))
        fig_g.add_trace(go.Histogram(x=hi_c, name=f"High ({third*2+1}–{pool})",marker_color="#ff6b35",opacity=0.7,nbinsx=8))
        fig_g.update_layout(template="plotly_dark",height=280,barmode="overlay",
                            margin=dict(l=10,r=10,t=10,b=10),plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
        st.plotly_chart(fig_g,use_container_width=True)
        st.markdown(f"Avg: **Low={np.mean(low_c):.1f}** · **Mid={np.mean(mid_c):.1f}** · **High={np.mean(hi_c):.1f}**")

    with tab5:
        st.markdown("**Enter your numbers — see how close you've been historically**")
        user_nums=st.multiselect(f"Pick {balls_per_draw} numbers (1–{pool})",list(range(1,pool+1)),max_selections=balls_per_draw)
        if len(user_nums)==balls_per_draw:
            sub_df=df.sort_values("date",ascending=False).head(n_draws)
            results=[{"Date":row["date"].strftime("%Y-%m-%d"),
                      "Draw":" ".join(f"{n:02d}" for n in row["numbers"]),
                      "Matches":len(set(user_nums)&set(row["numbers"])),
                      "Bonus Match":row["bonus"] in user_nums}
                     for _,row in sub_df.iterrows()]
            res_df=pd.DataFrame(results)
            best=res_df["Matches"].max()
            c1t,c2t,c3t=st.columns(3)
            with c1t: st.metric("Best Match",f"{best}/{balls_per_draw}")
            with c2t: st.metric("Draws Checked",len(res_df))
            with c3t: st.metric("Bonus Matches",res_df["Bonus Match"].sum())
            mc=Counter(res_df["Matches"])
            fig_m=go.Figure(go.Bar(x=[f"{k} matches" for k in sorted(mc)],y=[mc[k] for k in sorted(mc)],
                                   marker_color=gcolor,opacity=0.85))
            fig_m.update_layout(template="plotly_dark",height=220,margin=dict(l=10,r=10,t=10,b=10),
                                plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
            st.plotly_chart(fig_m,use_container_width=True)
            st.dataframe(res_df[res_df["Matches"]>=2],use_container_width=True,hide_index=True)
        else: st.info(f"Select exactly {balls_per_draw} numbers above.")

    with tab6:
        st.markdown("**Prize odds for each match level**")
        prize_data={
            "lotto_max":   {7:"1 in 33,294,800","6+B":"1 in 6,028,696",6:"1 in 218,530",5:"1 in 1,381","4+B":"1 in 1,105",4:"1 in 82.9",3:"1 in 8.5"},
            "lotto_649":   {6:"1 in 13,983,816",5:"1 in 55,492",4:"1 in 1,033",3:"1 in 56.7",2:"1 in 8.3"},
            "western_649": {6:"1 in 13,983,816",5:"1 in 55,492",4:"1 in 1,033",3:"1 in 56.7",2:"1 in 8.3"},
            "western_max": {7:"1 in 33,294,800",6:"1 in 218,530",5:"1 in 1,381",4:"1 in 82.9",3:"1 in 8.5"},
            "daily_grand": {5:"1 in 13,348,188","4+G":"1 in 1,909,073",4:"1 in 46,370",3:"1 in 1,109",2:"1 in 49.9"},
        }
        odds=prize_data.get(game_key,{})
        prize_colors=["#d4af37","#c0c0c0","#cd7f32","#4a9eff","#4a9eff","#4a9eff","#4a9eff"]
        for idx,(matches,odd) in enumerate(odds.items()):
            c=prize_colors[idx] if idx<len(prize_colors) else "#4a9eff"
            st.markdown(
                f"<div style='background:linear-gradient(90deg,rgba(0,10,30,0.6),rgba(0,10,30,0.3));"
                f"border-left:3px solid {c};border-radius:8px;padding:10px 16px;margin:5px 0;"
                f"display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:#a0c4e8;font-weight:700;font-size:14px;'>Match {matches}</span>"
                f"<span style='color:{c};font-weight:900;font-size:15px;'>{odd}</span></div>",unsafe_allow_html=True)

    with tab7:
        st.markdown("**Δ Delta System — gaps between consecutive drawn numbers**")
        sub_df=df.sort_values("date",ascending=False).head(n_draws)
        all_deltas=[]
        for nums in sub_df["numbers"]:
            sn=sorted(nums); all_deltas.extend([sn[0]]+[sn[i]-sn[i-1] for i in range(1,len(sn))])
        dc=Counter(all_deltas); top_deltas=dc.most_common(20)
        fig_d=go.Figure(go.Bar(x=[str(d) for d,_ in top_deltas],y=[c for _,c in top_deltas],
                               marker_color=gcolor,opacity=0.85))
        fig_d.update_layout(template="plotly_dark",height=260,margin=dict(l=10,r=10,t=10,b=10),
                            plot_bgcolor="#050d1a",paper_bgcolor="#050d1a",
                            xaxis_title="Delta",yaxis_title="Frequency")
        st.plotly_chart(fig_d,use_container_width=True)
        st.markdown(f"Avg delta: **{np.mean(all_deltas):.1f}** · Most common: **{top_deltas[0][0]}** ({top_deltas[0][1]} times)")
        st.markdown("**🔮 Delta Ticket Suggestion**")
        common_d=[d for d,_ in dc.most_common(balls_per_draw+2)]
        start=random.randint(1,10); delta_ticket=[start]
        for d in common_d[:balls_per_draw-1]:
            nxt=delta_ticket[-1]+d
            if nxt<=pool: delta_ticket.append(nxt)
        delta_ticket=sorted(delta_ticket[:balls_per_draw])
        bh=render_balls(delta_ticket)
        st.markdown(f"<div style='background:rgba(0,0,0,0.4);border-left:4px solid {gcolor};border-radius:8px;padding:12px;'>{bh}</div>",unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📈 Sum Trend")
    td=df.sort_values("date").tail(n_draws).copy()
    td["sum"]=td["numbers"].apply(sum); td["ma5"]=td["sum"].rolling(5).mean()
    fig_t=go.Figure()
    fig_t.add_trace(go.Scatter(x=td["date"],y=td["sum"],mode="markers",
                               marker=dict(color=gcolor,size=6,opacity=0.7),name="Draw Sum"))
    fig_t.add_trace(go.Scatter(x=td["date"],y=td["ma5"],mode="lines",
                               line=dict(color="#ffc940",width=2.5),name="5-Draw MA"))
    fig_t.update_layout(template="plotly_dark",height=260,margin=dict(l=10,r=10,t=10,b=10),
                        plot_bgcolor="#050d1a",paper_bgcolor="#050d1a")
    st.plotly_chart(fig_t,use_container_width=True)

    st.markdown("### 🔍 Number Lookup")
    lu=st.number_input(f"Enter number (1–{pool})",min_value=1,max_value=pool,value=7)
    ai=df[df["numbers"].apply(lambda x:lu in x)].sort_values("date",ascending=False)
    c1l,c2l,c3l=st.columns(3)
    with c1l: st.metric("Total Appearances",len(ai))
    with c2l: st.metric("Appearance Rate",f"{len(ai)/len(df)*100:.0f}%")
    with c3l: st.metric("Draws Since Last",draws_since.get(lu,0))
    if not ai.empty:
        st.markdown(f"Last seen: **{ai.iloc[0]['date'].strftime('%B %d, %Y')}**")
        st.dataframe(ai[["date","numbers","bonus"]].rename(columns={"date":"Date","numbers":"Numbers","bonus":"Bonus"}).head(10),
                     use_container_width=True,hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# SCRATCH HUB
# ════════════════════════════════════════════════════════════════════════════════
elif pg=="s":
    st.markdown("## 🎫 Scratch Hub")
    scratch_data=None
    if "scratch_tickets" in st.session_state and st.session_state.scratch_tickets:
        scratch_data=st.session_state.scratch_tickets
        st.caption(f"🟢 LIVE · {st.session_state.get('scratch_fetched_at','')} · {len(scratch_data)} tickets")
    else:
        sc=load_scratch_cache()
        if sc and sc.get("tickets"):
            scratch_data=sc["tickets"]; st.caption(f"🟡 CACHED · {sc['fetched_at']} · {len(scratch_data)} tickets")
    if scratch_data:
        st.dataframe(pd.DataFrame(scratch_data),use_container_width=True,hide_index=True)
    else:
        st.info("No scratch data. Go to ⚙️ Settings → 🎫 Update Scratch.")
    st.divider()
    st.markdown("### 📝 Scratch Ticket Log")
    if "scratch_log" not in st.session_state: st.session_state.scratch_log=[]
    with st.form("scratch_form"):
        s_type=st.selectbox("Ticket Type",["$3 Scratch","$5 Scratch","$10 Scratch","$20 Scratch","Instant Win"])
        sc1,sc2=st.columns(2)
        with sc1: s_cost=st.number_input("Cost ($)",value=3.0,step=1.0)
        with sc2: s_won=st.number_input("Won ($)",value=0.0,step=1.0)
        s_code=st.text_input("Validation Code (optional)")
        if st.form_submit_button("⚡ Log Ticket"):
            st.session_state.scratch_log.append({"date":datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type":s_type,"cost":s_cost,"won":s_won,"code":s_code})
            st.success(f"Logged! Net: ${s_won-s_cost:+.2f}")
    if st.session_state.scratch_log:
        ld=pd.DataFrame(st.session_state.scratch_log)
        ts,tw=ld["cost"].sum(),ld["won"].sum()
        sm1,sm2,sm3=st.columns(3)
        with sm1: st.metric("Total Spent",f"${ts:.2f}")
        with sm2: st.metric("Total Won",f"${tw:.2f}")
        with sm3: st.metric("Net",f"${tw-ts:+.2f}")
        st.dataframe(ld,use_container_width=True,hide_index=True)
        if st.button("🗑 Clear Log"): st.session_state.scratch_log=[]; st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ════════════════════════════════════════════════════════════════════════════════
elif pg=="x":
    st.markdown("## ⚙️ Settings & Data Sync")
    if not FETCH_AVAILABLE:
        st.warning("Install: pip install requests beautifulsoup4 lxml")
    else:
        su1,su2,su3,su4=st.columns(4)
        with su1:
            if st.button("🔮 Update Lotto Max",use_container_width=True):
                with st.spinner("Fetching..."): draws,msg=fetch_lotto_max()
                if draws:
                    now=datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_lotto_max"]=draws; st.session_state["live_lotto_max_at"]=now
                    save_cache("lotto_max",draws,now); st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
        with su2:
            if st.button("6️⃣ Update Lotto 6/49",use_container_width=True):
                with st.spinner("Fetching..."): draws,msg=fetch_wclc("lotto_649")
                if draws:
                    now=datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_lotto_649"]=draws; st.session_state["live_lotto_649_at"]=now
                    save_cache("lotto_649",draws,now); st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
        with su3:
            if st.button("🌾 Update Western 649",use_container_width=True):
                with st.spinner("Fetching..."): draws,msg=fetch_wclc("western_649")
                if draws:
                    now=datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_western_649"]=draws; st.session_state["live_western_649_at"]=now
                    save_cache("western_649",draws,now); st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
        with su4:
            if st.button("⭐ Update Western Max",use_container_width=True):
                with st.spinner("Fetching..."): draws,msg=fetch_wclc("western_max")
                if draws:
                    now=datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_western_max"]=draws; st.session_state["live_western_max_at"]=now
                    save_cache("western_max",draws,now); st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")

        st.markdown("<br>",unsafe_allow_html=True)
        sc1,sc2=st.columns(2)
        with sc1:
            if st.button("🎫 Update Scratch & Win",use_container_width=True):
                with st.spinner("Fetching..."): tickets,msg=fetch_scratch_tickets()
                if tickets:
                    now=datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state.scratch_tickets=tickets; st.session_state.scratch_fetched_at=now
                    save_scratch_cache(tickets,now); st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
        with sc2:
            if st.button("🗑 Clear All Cache",use_container_width=True):
                for k in ["live_lotto_max","live_lotto_649","live_western_649","live_western_max",
                          "live_lotto_max_at","live_lotto_649_at","live_western_649_at","live_western_max_at",
                          "scratch_tickets","scratch_fetched_at"]:
                    st.session_state.pop(k,None)
                for fname in [CACHE_FILE,SCRATCH_FILE]:
                    os.path.exists(fname) and os.remove(fname)
                st.success("Cache cleared"); st.rerun()

    st.divider()
    st.markdown("### 📡 Data Status")
    for gk,gv in GAMES.items():
        _raw,_src,_live=get_draws(gk)
        _cnt=len(build_df(_raw,gv["balls"]))
        color=gv["color"]
        st.markdown(
            f"<div style='background:rgba(0,10,30,0.4);border-left:3px solid {color};"
            f"border-radius:6px;padding:8px 14px;margin:4px 0;'>"
            f"<span style='color:{color};font-weight:700;'>{gv['emoji']} {gv['name']}</span>"
            f" — {'🟢 LIVE' if _live else '🟡 BUILT-IN'} · <span style='color:#6a9abf;'>{_cnt} draws · {_src}</span>"
            f"</div>",unsafe_allow_html=True)
