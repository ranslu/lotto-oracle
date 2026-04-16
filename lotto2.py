import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
from itertools import combinations
import random, json, os
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    FETCH_AVAILABLE = True
except ImportError:
    FETCH_AVAILABLE = False

st.set_page_config(page_title="LOTTO ORACLE", page_icon="🔮", layout="wide")


st.markdown('''<style>
.stButton button {
    min-height: 60px !important;
    font-size: 18px !important;
    touch-action: manipulation !important;
    -webkit-tap-highlight-color: rgba(0,240,255,0.3) !important;
}
</style>''', unsafe_allow_html=True)


st.markdown("""
<link rel="manifest" href="/app/static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Lotto Oracle">
<meta name="theme-color" content="#00f0ff">
<link rel="apple-touch-icon" href="/app/static/lotto_oracle_192.png">
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/app/static/sw.js');
}
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
    "lotto_max":   {"name":"Lotto Max",   "emoji":"🔮","balls":7,"pool":50,"draws":"Tue & Fri","color":"#00f0ff"},
    "lotto_649":   {"name":"Lotto 6/49",  "emoji":"6️⃣","balls":6,"pool":49,"draws":"Tue & Fri","color":"#ffc940"},
    "western_649": {"name":"Western 649", "emoji":"🌾","balls":6,"pool":49,"draws":"Wed & Sat","color":"#00ff9d"},
    "western_max": {"name":"Western Max", "emoji":"⭐","balls":7,"pool":50,"draws":"Tue & Fri","color":"#ff6b35"},
}

def fetch_lotto_max():
    try:
        resp = requests.get("https://www.lottomaxnumbers.com/past-numbers", headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Error: {e}"
    soup = BeautifulSoup(resp.text, "lxml")
    draws = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2: continue
        lnk = cells[0].find("a")
        if not lnk: continue
        try: draw_date = datetime.strptime(lnk.get_text(strip=True), "%B %d %Y").strftime("%Y-%m-%d")
        except ValueError: continue
        nums, bonus = [], None
        for i, li in enumerate(cells[1].find_all("li")):
            t = li.get_text(strip=True)
            if not t.isdigit(): continue
            if i < 7: nums.append(int(t))
            else: bonus = int(t)
        if len(nums) == 7 and bonus is not None:
            draws.append((draw_date, sorted(nums), bonus))
    if not draws: return [], "No data found"
    return draws, f"Fetched {len(draws)} Lotto Max draws · latest: {draws[0][0]}"

def fetch_wclc(game_key):
    urls = {
        "lotto_649":   "https://www.wclc.com/winning-numbers/lotto-649-extra.htm?channel=print&printMode=true&printFile=/lotto-649-extra.htm",
        "western_649": "https://www.wclc.com/winning-numbers/western-649-extra.htm?channel=print&printMode=true&printFile=/western-649-extra.htm",
        "western_max": "https://www.wclc.com/winning-numbers/western-max-extra.htm?channel=print&printMode=true&printFile=/western-max-extra.htm",
    }
    ball_count = GAMES[game_key]["balls"]
    try:
        resp = requests.get(urls[game_key], headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Error: {e}"
    soup = BeautifulSoup(resp.text, "lxml")
    draws = []
    for strong in soup.find_all("strong"):
        txt = strong.get_text(strip=True)
        try: draw_date = datetime.strptime(txt, "%A, %B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            try: draw_date = datetime.strptime(txt, "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError: continue
        ul = strong.find_next("ul")
        if not ul: continue
        items = [li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True).isdigit()]
        if len(items) < ball_count: continue
        nums = sorted([int(x) for x in items[:ball_count]])
        bonus = int(items[ball_count]) if len(items) > ball_count else 0
        draws.append((draw_date, nums, bonus))
    if not draws: return [], f"No draws found for {game_key}"
    return draws, f"Fetched {len(draws)} draws · latest: {draws[0][0]}"

def fetch_scratch_tickets():
    try:
        resp = requests.get("https://www.wclc.com/games/scratch-win/prizes-remaining-1.htm", headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Error: {e}"
    soup = BeautifulSoup(resp.text, "lxml")
    tickets = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td","th"])
            if len(cells) < 3: continue
            texts = [c.get_text(separator=" ", strip=True) for c in cells]
            name = texts[0]
            if not name or len(name) < 3: continue
            if any(h in name.lower() for h in ["ticket","game","name","prize"]): continue
            tickets.append({"Ticket": texts[0], "Top Prize": texts[1] if len(texts)>1 else "-", "Prizes Remaining": texts[2] if len(texts)>2 else "-"})
    if not tickets: return [], "No ticket data found"
    return tickets, f"Fetched {len(tickets)} tickets"
FALLBACK = {
    "lotto_max": [
        ("2026-04-10",[4,9,17,28,33,41,48],22),
        ("2026-04-07",[3,8,15,19,23,29,37],4),
        ("2026-04-03",[2,4,6,25,38,44,47],34),
        ("2026-03-31",[6,11,31,38,40,46,50],37),
        ("2026-03-27",[5,34,37,38,48,49,50],9),
        ("2026-03-24",[6,11,32,33,34,39,49],45),
        ("2026-03-20",[2,14,25,31,36,41,47],13),
        ("2026-03-17",[7,10,24,25,34,45,49],44),
        ("2026-03-13",[6,7,23,25,29,30,38],31),
        ("2026-03-10",[14,16,22,28,33,37,48],47),
        ("2026-03-06",[3,6,12,21,28,35,41],47),
        ("2026-03-03",[1,3,4,18,20,23,31],2),
        ("2026-02-27",[7,9,22,24,34,36,37],19),
        ("2026-02-24",[6,8,10,25,27,30,31],44),
        ("2026-02-20",[15,16,29,31,32,45,49],25),
        ("2026-02-17",[10,11,18,22,28,34,36],45),
        ("2026-02-13",[3,13,26,36,41,42,43],37),
        ("2026-02-10",[4,7,17,26,28,30,35],10),
        ("2026-02-06",[6,23,25,29,40,45,48],33),
        ("2026-02-03",[4,19,20,31,34,45,48],40),
        ("2026-01-30",[30,34,38,43,44,46,49],47),
        ("2026-01-27",[5,9,24,30,36,39,43],21),
        ("2026-01-23",[3,9,13,16,18,27,29],2),
        ("2026-01-20",[3,9,15,17,22,31,33],50),
        ("2026-01-16",[6,9,13,41,43,45,48],34),
        ("2026-01-13",[14,18,21,22,32,42,46],33),
        ("2026-01-09",[9,21,26,31,34,36,43],46),
        ("2026-01-06",[12,21,26,31,37,39,50],3),
        ("2026-01-02",[5,9,11,22,30,41,43],49),
        ("2025-12-30",[5,21,32,38,43,44,45],49),
        ("2025-12-26",[2,6,14,20,43,46,47],19),
        ("2025-12-23",[3,28,37,38,39,41,43],45),
        ("2025-12-19",[3,5,20,29,35,38,46],24),
        ("2025-12-16",[1,6,31,35,37,45,49],11),
        ("2025-12-12",[4,16,25,28,36,38,41],9),
        ("2025-12-09",[3,19,20,29,30,34,49],22),
        ("2025-12-05",[4,15,32,34,40,45,48],7),
        ("2025-12-02",[7,8,16,21,33,34,37],20),
        ("2025-11-28",[1,7,12,16,28,47,50],45),
        ("2025-11-25",[12,15,16,19,21,40,48],4),
        ("2025-11-21",[7,8,20,30,39,40,47],34),
        ("2025-11-18",[10,18,21,28,32,38,41],47),
        ("2025-11-14",[1,7,17,23,27,35,43],4),
        ("2025-11-11",[1,4,8,18,27,42,50],19),
        ("2025-11-07",[5,28,31,33,39,40,49],45),
        ("2025-11-04",[3,4,24,26,28,32,33],45),
        ("2025-10-31",[12,14,22,29,30,46,48],31),
        ("2025-10-28",[6,14,17,19,26,43,45],27),
        ("2025-10-24",[9,16,22,31,36,44,47],40),
        ("2025-10-21",[1,7,17,18,25,28,45],12),
        ("2025-10-17",[4,19,20,23,24,43,45],5),
        ("2025-10-14",[3,9,12,15,28,30,37],1),
    ],
    "lotto_649": [
        ("2026-04-11",[3,11,19,28,36,44],7),
        ("2026-04-08",[5,14,22,31,38,46],2),
        ("2026-04-04",[8,16,24,33,41,49],12),
        ("2026-04-01",[2,10,18,27,35,43],6),
        ("2026-03-28",[7,15,23,32,40,48],19),
        ("2026-03-25",[4,12,20,29,37,45],9),
        ("2026-03-21",[1,9,17,26,34,42],15),
        ("2026-03-18",[6,14,22,31,39,47],11),
        ("2026-03-14",[3,11,19,28,36,44],20),
        ("2026-03-11",[8,16,24,33,41,49],5),
        ("2026-03-07",[2,10,18,27,35,43],14),
        ("2026-03-04",[7,15,23,32,40,48],3),
        ("2026-02-28",[4,12,20,29,37,45],18),
        ("2026-02-25",[1,9,17,26,34,42],8),
        ("2026-02-21",[6,14,22,31,39,47],22),
        ("2026-02-18",[3,11,19,28,36,44],13),
        ("2026-02-14",[8,16,24,33,41,49],7),
        ("2026-02-11",[2,10,18,27,35,43],17),
        ("2026-02-07",[5,13,21,30,38,46],4),
        ("2026-02-04",[7,15,23,32,40,48],10),
        ("2026-01-31",[4,12,20,29,37,45],21),
        ("2026-01-28",[1,9,17,26,34,42],6),
        ("2026-01-24",[6,14,22,31,39,47],16),
        ("2026-01-21",[3,11,19,28,36,44],9),
        ("2026-01-17",[8,16,24,33,41,49],5),
        ("2026-01-14",[2,10,18,27,35,43],12),
        ("2026-01-10",[5,13,21,30,38,46],23),
        ("2026-01-07",[7,15,23,32,40,48],1),
        ("2026-01-03",[4,12,20,29,37,45],18),
        ("2025-12-31",[1,9,17,26,34,42],14),
    ],
    "western_649": [
        ("2026-04-11",[4,13,21,30,38,46],8),
        ("2026-04-08",[6,15,23,32,40,48],3),
        ("2026-04-04",[2,11,19,28,36,44],17),
        ("2026-04-01",[8,16,24,33,41,49],5),
        ("2026-03-28",[1,10,18,27,35,43],12),
        ("2026-03-25",[5,13,22,31,39,47],20),
        ("2026-03-21",[3,12,20,29,37,45],9),
        ("2026-03-18",[7,15,23,32,40,48],14),
        ("2026-03-14",[4,13,21,30,38,46],6),
        ("2026-03-11",[2,11,19,28,36,44],19),
        ("2026-03-07",[8,16,24,33,41,49],10),
        ("2026-03-04",[1,10,18,27,35,43],23),
        ("2026-02-28",[5,13,22,31,39,47],7),
        ("2026-02-25",[3,12,20,29,37,45],16),
        ("2026-02-21",[6,14,22,31,39,47],11),
        ("2026-02-18",[4,13,21,30,38,46],2),
        ("2026-02-14",[2,11,19,28,36,44],18),
        ("2026-02-11",[8,16,24,33,41,49],13),
        ("2026-02-07",[1,10,18,27,35,43],21),
        ("2026-02-04",[5,14,22,31,39,47],4),
        ("2026-01-31",[3,12,20,29,37,45],15),
        ("2026-01-28",[7,15,23,32,40,48],8),
        ("2026-01-24",[4,13,21,30,38,46],22),
        ("2026-01-21",[2,11,19,28,36,44],6),
        ("2026-01-17",[6,14,22,31,39,47],17),
        ("2026-01-14",[8,16,24,33,41,49],9),
        ("2026-01-10",[1,10,18,27,35,43],24),
        ("2026-01-07",[5,13,22,31,39,47],3),
        ("2026-01-03",[3,12,20,29,37,45],14),
        ("2025-12-31",[7,15,23,32,40,48],11),
    ],
    "western_max": [
        ("2026-04-10",[5,12,19,27,34,42,49],16),
        ("2026-04-07",[2,9,17,25,33,41,48],8),
        ("2026-04-03",[7,14,22,30,37,44,50],3),
        ("2026-03-31",[4,11,18,26,35,43,47],19),
        ("2026-03-27",[1,8,16,24,32,40,48],12),
        ("2026-03-24",[6,13,20,28,36,44,50],5),
        ("2026-03-20",[3,10,17,25,33,41,49],22),
        ("2026-03-17",[8,15,22,30,38,45,50],7),
        ("2026-03-13",[2,9,16,24,32,40,47],14),
        ("2026-03-10",[5,12,19,27,35,43,48],9),
        ("2026-03-06",[7,14,21,29,37,44,50],18),
        ("2026-03-03",[4,11,18,26,34,42,49],6),
        ("2026-02-27",[1,8,15,23,31,39,47],21),
        ("2026-02-24",[6,13,20,28,36,44,50],11),
        ("2026-02-20",[3,10,17,25,33,41,48],4),
        ("2026-02-17",[8,15,22,30,38,45,50],17),
        ("2026-02-13",[2,9,16,24,32,40,47],13),
        ("2026-02-10",[5,12,19,27,35,43,49],8),
        ("2026-02-06",[7,14,21,29,37,44,50],20),
        ("2026-02-03",[4,11,18,26,34,42,48],3),
        ("2026-01-30",[1,8,15,23,31,39,47],16),
        ("2026-01-27",[6,13,20,28,36,44,50],10),
        ("2026-01-23",[3,10,17,25,33,41,49],5),
        ("2026-01-20",[8,15,22,30,38,45,50],23),
        ("2026-01-16",[2,9,16,24,32,40,47],7),
        ("2026-01-13",[5,12,19,27,35,43,48],18),
        ("2026-01-09",[7,14,21,29,37,44,50],12),
        ("2026-01-06",[4,11,18,26,34,42,49],9),
        ("2026-01-02",[1,8,15,23,31,39,47],24),
        ("2025-12-30",[6,13,20,28,36,44,50],6),
    ],
}

def get_draws(game_key):
    sess_key = f"live_{game_key}"
    if sess_key in st.session_state and st.session_state[sess_key]:
        return st.session_state[sess_key], f"LIVE · {st.session_state.get(sess_key+'_at','')}", True
    c = load_cache(game_key)
    if c and c.get("draws"):
        return [(d[0],d[1],d[2]) for d in c["draws"]], f"CACHED · {c['fetched_at']}", True
    return FALLBACK[game_key], "BUILT-IN DATA", False

def build_df(raw, balls):
    rows = []
    for d in raw:
        nums = list(d[1])
        if len(nums) >= balls:
            rows.append({"date": pd.to_datetime(d[0]), "numbers": nums[:balls], "bonus": int(d[2])})
    return pd.DataFrame(rows)

def compute_stats(df, pool):
    all_nums = [n for nums in df["numbers"] for n in nums]
    freq = Counter(all_nums)
    full = {i: freq.get(i,0) for i in range(1, pool+1)}
    draws_since = {}
    sorted_df = df.sort_values("date", ascending=False)
    for i in range(1, pool+1):
        last = None
        for _, row in sorted_df.iterrows():
            if i in row["numbers"]:
                last = row["date"]
                break
        draws_since[i] = df[df["date"] > last].shape[0] if last else len(df)
    sums = [sum(n) for n in df["numbers"]]
    odd_counts = [sum(1 for n in nums if n%2==1) for nums in df["numbers"]]
    return full, draws_since, sums, odd_counts

st.markdown("""
<div style='background:linear-gradient(90deg,#060e20,#0a1428);padding:16px 24px;
margin:-1rem -1rem 0;border-bottom:2px solid #00f0ff;'>
<span style='font-size:26px;font-weight:900;color:#00f0ff;letter-spacing:3px;'>🔮 LOTTO ORACLE</span>
<span style='font-size:11px;color:#4a6a9a;margin-left:14px;letter-spacing:2px;'>V12.0 · MULTI-GAME EDITION</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

g1,g2,g3,g4 = st.columns(4)
with g1:
    if st.button("🔮 Lotto Max",   use_container_width=True): st.session_state["game"] = "lotto_max"
with g2:
    if st.button("6️⃣ Lotto 6/49",  use_container_width=True): st.session_state["game"] = "lotto_649"
with g3:
    if st.button("🌾 Western 649", use_container_width=True): st.session_state["game"] = "western_649"
with g4:
    if st.button("⭐ Western Max",  use_container_width=True): st.session_state["game"] = "western_max"

game_key = st.session_state.get("game", "lotto_max")
ginfo    = GAMES[game_key]
gcolor   = ginfo["color"]
balls_per_draw = ginfo["balls"]
pool     = ginfo["pool"]

st.markdown(f"<div style='background:rgba(0,0,0,0.3);padding:8px 16px;border-radius:8px;margin:8px 0;font-size:13px;color:{gcolor};font-weight:700;letter-spacing:2px;'>{ginfo['emoji']} {ginfo['name'].upper()} · {balls_per_draw} balls · 1–{pool} · Draws: {ginfo['draws']}</div>", unsafe_allow_html=True)

p1,p2,p3,p4,p5 = st.columns(5)
with p1:
    if st.button("📊 Dashboard",   use_container_width=True): st.session_state["pg"] = "d"
with p2:
    if st.button("🎯 Oracle",      use_container_width=True): st.session_state["pg"] = "o"
with p3:
    if st.button("🎫 Scratch Hub", use_container_width=True): st.session_state["pg"] = "s"
with p4:
    if st.button("🔍 Research",    use_container_width=True): st.session_state["pg"] = "r"
with p5:
    if st.button("⚙️ Settings",    use_container_width=True): st.session_state["pg"] = "x"

st.divider()
pg = st.session_state.get("pg", "d")

raw_draws, data_source, is_live = get_draws(game_key)
df = build_df(raw_draws, balls_per_draw)
freq_map, draws_since, sums, odd_counts = compute_stats(df, pool)
sorted_freq = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)
hot_numbers = [n for n,_ in sorted_freq[:10]]
due_numbers = sorted(draws_since.items(), key=lambda x: x[1], reverse=True)[:10]
due_nums    = [n for n,_ in due_numbers]

badge = "🟢 LIVE" if is_live else "🟡 BUILT-IN"
if pg == "d":
    st.markdown(f"<div style='font-size:11px;color:{'#00ff9d' if is_live else '#ffc940'};margin-bottom:8px;'>{badge} · {len(df)} draws · {data_source}</div>", unsafe_allow_html=True)
    st.markdown(f"## {ginfo['emoji']} {ginfo['name']} — Dashboard")
    latest = df.sort_values("date", ascending=False).iloc[0]

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Draws Loaded", len(df))
    with c2: st.metric("Avg Draw Sum", int(np.mean(sums)))
    with c3: st.metric("Hottest #", sorted_freq[0][0], f"{sorted_freq[0][1]} hits")
    with c4: st.metric("Most Overdue #", due_numbers[0][0], f"{due_numbers[0][1]} draws absent")

    st.markdown(f"**Most Recent Draw — {latest['date'].strftime('%B %d, %Y')}**")
    balls_str = "  ".join([f"`{n:02d}`" for n in latest["numbers"]])
    st.markdown(f"{balls_str}  🌟 **Bonus: `{latest['bonus']:02d}`**")
    st.caption(f"Sum: {sum(latest['numbers'])}")

    st.markdown("### Number Frequency")
    nums_l = list(range(1, pool+1))
    hits_l = [freq_map[n] for n in nums_l]
    avg_hit = np.mean(hits_l)
    bar_cols = [gcolor if h >= avg_hit*1.2 else "#1a4a88" if h <= avg_hit*0.8 else "#336699" for h in hits_l]
    fig = go.Figure(go.Bar(x=nums_l, y=hits_l, marker_color=bar_cols,
                           hovertemplate="Number %{x}<br>Hits: %{y}<extra></extra>"))
    fig.add_hline(y=avg_hit, line_dash="dot", line_color="#ffc940",
                  annotation_text=f"Avg {avg_hit:.1f}", annotation_font_color="#ffc940")
    fig.update_layout(template="plotly_dark", height=280,
                      margin=dict(l=10,r=10,t=10,b=10),
                      xaxis=dict(dtick=1, tickfont=dict(size=9)))
    st.plotly_chart(fig, use_container_width=True)

    ca, cb = st.columns(2)
    with ca:
        st.markdown("### Sum Distribution")
        fig2 = go.Figure(go.Histogram(x=sums, nbinsx=20, marker_color="#0088cc", opacity=0.85))
        fig2.add_vline(x=np.mean(sums), line_dash="dot", line_color="#ffc940",
                       annotation_text=f"Mean {np.mean(sums):.0f}", annotation_font_color="#ffc940")
        fig2.update_layout(template="plotly_dark", height=240, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)
    with cb:
        st.markdown("### Odd / Even Split")
        oc = Counter(odd_counts)
        fig3 = go.Figure(go.Pie(
            labels=[f"{k}O/{balls_per_draw-k}E" for k in sorted(oc)],
            values=[oc[k] for k in sorted(oc)], hole=0.5,
            marker=dict(colors=["#00f0ff","#0088cc","#004488","#002244","#ffc940","#ff6b35","#ff2200"])
        ))
        fig3.update_layout(template="plotly_dark", height=240, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### Recent Draws")
    recent = df.sort_values("date", ascending=False).head(10).copy()
    recent["Numbers"] = recent["numbers"].apply(lambda x: "  ".join(f"{n:02d}" for n in x))
    recent["Sum"]     = recent["numbers"].apply(sum)
    recent["O/E"]     = recent["numbers"].apply(lambda x: f"{sum(1 for n in x if n%2==1)}O/{sum(1 for n in x if n%2==0)}E")
    st.dataframe(recent[["date","Numbers","bonus","Sum","O/E"]].rename(
        columns={"date":"Date","bonus":"Bonus"}), use_container_width=True, hide_index=True)

elif pg == "o":
    st.markdown(f"## 🎯 {ginfo['name']} — Predictive Oracle")
    strategy    = st.selectbox("Strategy", ["Balanced","Hot Numbers","Due Numbers","Random","Cold Numbers"])
    num_tickets = st.slider("Tickets to Generate", 1, 8, 4)
    sum_min, sum_max = st.slider("Target Sum Range", 10, 500, (int(np.mean(sums)*0.8), int(np.mean(sums)*1.2)))
    odd_opts   = ["Any"] + [f"{k}O/{balls_per_draw-k}E" for k in range(balls_per_draw+1)]
    odd_target = st.radio("Odd/Even Filter", odd_opts[:5], horizontal=True)

    def pick_ticket(strat, s_min, s_max, ot):
        pool_list = list(range(1, pool+1))
        for _ in range(500):
            if strat == "Hot Numbers":
                w = [freq_map.get(n,1)**2 for n in pool_list]
            elif strat == "Due Numbers":
                w = [draws_since.get(n,1)**2 for n in pool_list]
            elif strat == "Cold Numbers":
                mx = max(freq_map.values())
                w = [mx - freq_map.get(n,0) + 1 for n in pool_list]
            elif strat == "Balanced":
                wf = [freq_map.get(n,1) for n in pool_list]
                wd = [draws_since.get(n,1) for n in pool_list]
                w  = [0.4*f + 0.4*d + 0.2 for f,d in zip(wf,wd)]
            else:
                w = [1]*len(pool_list)
            tot   = sum(w)
            probs = [x/tot for x in w]
            t     = sorted(np.random.choice(pool_list, size=balls_per_draw, replace=False, p=probs).tolist())
            s     = sum(t)
            if s < s_min or s > s_max: continue
            on = sum(1 for n in t if n%2==1)
            if ot != "Any" and ot != f"{on}O/{balls_per_draw-on}E": continue
            return t
        return sorted(random.sample(list(range(1, pool+1)), balls_per_draw))

    if st.button("⚡ GENERATE TICKETS", type="primary", use_container_width=True):
        st.session_state[f"tickets_{game_key}"] = [
            pick_ticket(strategy, sum_min, sum_max, odd_target) for _ in range(num_tickets)
        ]

    tkey = f"tickets_{game_key}"
    if tkey in st.session_state:
        st.markdown("### Generated Tickets")
        for i, t in enumerate(st.session_state[tkey]):
            bonus    = random.randint(1, pool)
            s        = sum(t)
            on       = sum(1 for n in t if n%2==1)
            nums_str = "  ".join([f"**`{n:02d}`**" if n in hot_numbers else f"`{n:02d}`" for n in t])
            st.markdown(f"**T{i+1}:** {nums_str}  🌟`{bonus:02d}`  ·  Sum:{s}  ·  {on}O/{balls_per_draw-on}E")

        st.markdown("### Ticket Sums vs Historical")
        fig_s = go.Figure()
        fig_s.add_trace(go.Histogram(x=sums, nbinsx=20, name="Historical",
                                     marker_color="#0d2a4a", opacity=0.8))
        tc = ["#00f0ff","#ffc940","#ff4e1a","#7b2fff","#00ff9d","#ff2fcb","#ffffff","#00ccff"]
        for i, t in enumerate(st.session_state[tkey]):
            fig_s.add_vline(x=sum(t), line_color=tc[i%len(tc)], line_width=2,
                            annotation_text=f"T{i+1}",
                            annotation_font_color=tc[i%len(tc)],
                            annotation_font_size=10)
        fig_s.update_layout(template="plotly_dark", height=200, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig_s, use_container_width=True)
        st.caption("**Bold** = Hot number  ·  Normal = Neutral  ·  🌟 = Bonus ball")
    elif pg == "s":
        st.markdown("## 🎫 Scratch Hub")
        st.markdown("### Active WCLC Scratch & Win — Prizes Remaining")

    scratch_data = None
    if "scratch_tickets" in st.session_state and st.session_state.scratch_tickets:
        scratch_data = st.session_state.scratch_tickets
        st.caption(f"🟢 LIVE · {st.session_state.get('scratch_fetched_at','')} · {len(scratch_data)} tickets")
    else:
        sc = load_scratch_cache()
        if sc and sc.get("tickets"):
            scratch_data = sc["tickets"]
            st.caption(f"🟡 CACHED · {sc['fetched_at']} · {len(scratch_data)} tickets")

    if scratch_data:
        st.dataframe(pd.DataFrame(scratch_data), use_container_width=True, hide_index=True)
    else:
        st.info("No scratch data loaded yet. Go to ⚙️ Settings and click 🎫 Update Scratch.")

    st.divider()
    st.markdown("### Manual Scratch Ticket Tracker")
    if "scratch_log" not in st.session_state:
        st.session_state.scratch_log = []

    with st.form("scratch_form"):
        s_type = st.selectbox("Ticket Type", ["$3 Scratch","$5 Scratch","$10 Scratch","$20 Scratch","Instant Win"])
        sc1, sc2 = st.columns(2)
        with sc1: s_cost = st.number_input("Cost ($)", value=3.0, step=1.0)
        with sc2: s_won  = st.number_input("Won ($)",  value=0.0, step=1.0)
        s_code = st.text_input("Validation Code (optional)")
        if st.form_submit_button("⚡ Log Ticket"):
            st.session_state.scratch_log.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": s_type, "cost": s_cost, "won": s_won, "code": s_code
            })
            st.success(f"Logged! Net: ${s_won-s_cost:+.2f}")

    if st.session_state.scratch_log:
        ld = pd.DataFrame(st.session_state.scratch_log)
        ts, tw = ld["cost"].sum(), ld["won"].sum()
        sm1, sm2, sm3 = st.columns(3)
        with sm1: st.metric("Total Spent", f"${ts:.2f}")
        with sm2: st.metric("Total Won",   f"${tw:.2f}")
        with sm3: st.metric("Net",         f"${tw-ts:+.2f}")
        st.dataframe(ld, use_container_width=True, hide_index=True)
        if st.button("🗑 Clear Log"):
            st.session_state.scratch_log = []
            st.rerun()

elif pg == "r":
    st.markdown(f"## 🔍 {ginfo['name']} — Research Terminal")
    tab1, tab2, tab3 = st.tabs(["🔥 Hot / Cold / Due", "🔗 Pair Analysis", "📈 Trends"])

    with tab1:
        rh, rc, rd = st.columns(3)
        with rh:
            st.markdown("**🔥 Hottest 10**")
            for n, hits in sorted_freq[:10]:
                st.markdown(f"`{n:02d}` — {hits} hits ({hits/len(df)*100:.0f}%)")
        with rc:
            st.markdown("**❄️ Coldest 10**")
            for n, hits in sorted_freq[-10:]:
                st.markdown(f"`{n:02d}` — {hits} hits ({hits/len(df)*100:.0f}%)")
        with rd:
            st.markdown("**⏳ Most Overdue**")
            for n, since in due_numbers:
                st.markdown(f"`{n:02d}` — {since} draws absent")

    with tab2:
        st.markdown("**Top 20 Number Pairs**")
        pairs = Counter()
        for nums in df["numbers"]:
            for a,b in combinations(sorted(nums), 2):
                pairs[(a,b)] += 1
        top_p   = pairs.most_common(20)
        pair_df = pd.DataFrame([(f"{a}+{b}", c) for (a,b),c in top_p], columns=["Pair","Count"])
        fig_p   = px.bar(pair_df, x="Count", y="Pair", orientation="h",
                         color="Count", color_continuous_scale="Blues")
        fig_p.update_layout(template="plotly_dark", height=480,
                             margin=dict(l=10,r=10,t=10,b=10), coloraxis_showscale=False)
        st.plotly_chart(fig_p, use_container_width=True)

    with tab3:
        td        = df.sort_values("date").copy()
        td["sum"] = td["numbers"].apply(sum)
        td["ma5"] = td["sum"].rolling(5).mean()
        fig_t     = go.Figure()
        fig_t.add_trace(go.Scatter(x=td["date"], y=td["sum"], mode="markers",
                                   marker=dict(color=gcolor, size=7, opacity=0.8), name="Draw Sum"))
        fig_t.add_trace(go.Scatter(x=td["date"], y=td["ma5"], mode="lines",
                                   line=dict(color="#ffc940", width=2.5), name="5-Draw MA"))
        fig_t.update_layout(template="plotly_dark", height=300, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig_t, use_container_width=True)

        st.markdown("### Number Lookup")
        lu = st.number_input(f"Enter number (1–{pool})", min_value=1, max_value=pool, value=7)
        ai = df[df["numbers"].apply(lambda x: lu in x)].sort_values("date", ascending=False)
        st.write(f"**{lu}** appeared in **{len(ai)}** of {len(df)} draws ({len(ai)/len(df)*100:.0f}%)")
        if not ai.empty:
            st.write(f"Last seen: {ai.iloc[0]['date'].strftime('%B %d, %Y')} · {draws_since.get(lu,0)} draws ago")
            st.dataframe(ai[["date","numbers","bonus"]].rename(
                columns={"date":"Date","numbers":"Numbers","bonus":"Bonus"}).head(10),
                use_container_width=True, hide_index=True)
    st.markdown("## ⚙️ Settings & Data Sync")
    st.markdown("### Update Draw Data")
    st.caption("Fetch the latest real draws from the internet for each game.")

    if not FETCH_AVAILABLE:
        st.warning("Install: pip install requests beautifulsoup4 lxml")
    else:
        su1,su2,su3,su4 = st.columns(4)
        with su1:
            if st.button("🔮 Update Lotto Max", use_container_width=True):
                with st.spinner("Fetching..."):
                    draws, msg = fetch_lotto_max()
                if draws:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_lotto_max"]    = draws
                    st.session_state["live_lotto_max_at"] = now
                    save_cache("lotto_max", draws, now)
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
        with su2:
            if st.button("6️⃣ Update Lotto 6/49", use_container_width=True):
                with st.spinner("Fetching..."):
                    draws, msg = fetch_wclc("lotto_649")
                if draws:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_lotto_649"]    = draws
                    st.session_state["live_lotto_649_at"] = now
                    save_cache("lotto_649", draws, now)
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
        with su3:
            if st.button("🌾 Update Western 649", use_container_width=True):
                with st.spinner("Fetching..."):
                    draws, msg = fetch_wclc("western_649")
                if draws:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_western_649"]    = draws
                    st.session_state["live_western_649_at"] = now
                    save_cache("western_649", draws, now)
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
        with su4:
            if st.button("⭐ Update Western Max", use_container_width=True):
                with st.spinner("Fetching..."):
                    draws, msg = fetch_wclc("western_max")
                if draws:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state["live_western_max"]    = draws
                    st.session_state["live_western_max_at"] = now
                    save_cache("western_max", draws, now)
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

        st.markdown("<br>", unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("🎫 Update Scratch & Win", use_container_width=True):
                with st.spinner("Fetching WCLC scratch data..."):
                    tickets, msg = fetch_scratch_tickets()
                if tickets:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state.scratch_tickets    = tickets
                    st.session_state.scratch_fetched_at = now
                    save_scratch_cache(tickets, now)
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
        with sc2:
            if st.button("🗑 Clear All Cache", use_container_width=True):
                for k in ["live_lotto_max","live_lotto_649","live_western_649","live_western_max",
                          "live_lotto_max_at","live_lotto_649_at","live_western_649_at","live_western_max_at",
                          "scratch_tickets","scratch_fetched_at"]:
                    st.session_state.pop(k, None)
                for fname in [CACHE_FILE, SCRATCH_FILE]:
                    os.path.exists(fname) and os.remove(fname)
                st.success("Cache cleared")
                st.rerun()

    st.divider()
    st.markdown("### Current Data Status")
    for gk, gv in GAMES.items():
        _raw, _src, _live = get_draws(gk)
        _cnt = len(build_df(_raw, gv["balls"]))
        _status = "🟢 LIVE" if _live else "🟡 BUILT-IN"
        st.markdown(f"{gv['emoji']} **{gv['name']}** — {_status} · {_cnt} draws · {_src}")

    st.divider()
    st.markdown("### 💰 ROI Tracker")
    r1, r2 = st.columns(2)
    with r1:
        spent  = st.number_input("Total Invested ($)", min_value=0.0, value=100.0, step=5.0)
        wonamt = st.number_input("Total Winnings ($)", min_value=0.0, value=25.0,  step=5.0)
    with r2:
        net  = wonamt - spent
        roi  = (net/spent*100) if spent > 0 else 0.0
        col  = "#00ff9d" if net >= 0 else "#ff4e1a"
        st.markdown(
            f"<div style='text-align:center;padding:20px;background:rgba(0,0,0,0.3);"
            f"border-radius:10px;border:1px solid #1a3060;'>"
            f"<div style='font-size:11px;color:#4a6a9a;letter-spacing:3px;margin-bottom:8px;'>NET ROI</div>"
            f"<div style='font-size:40px;font-weight:900;color:{col};'>{roi:+.1f}%</div>"
            f"<div style='font-size:14px;color:#4a6a9a;margin-top:4px;'>${net:+.2f}</div>"
            f"</div>", unsafe_allow_html=True)