#!/usr/bin/env python3
"""
Builds docs/brief.html: the mobile-first Lotto Oracle morning brief served by
GitHub Pages (https://ranslu.github.io/lotto-oracle/brief.html).

Reads lottery_data.json, so it must run after fetch_lottery.py in GitHub Actions.
Standard library only, no pip installs.
"""
import html
import json
import os
import random
from collections import Counter
from datetime import datetime, timedelta, timezone

GAMES = {
    "lotto_max":   {"name": "Lotto Max",   "balls": 7, "max_num": 50},
    "lotto_649":   {"name": "Lotto 6/49",  "balls": 6, "max_num": 49},
    "western_649": {"name": "Western 649", "balls": 6, "max_num": 49},
    "western_max": {"name": "Western Max", "balls": 7, "max_num": 50},
    "daily_grand": {"name": "Daily Grand", "balls": 5, "max_num": 49},
}

WINDOW_DAYS = 30      # "hot / cold" are measured over this many days
MIN_WINDOW_DRAWS = 4  # if fewer draws than this fall in the window, use the latest 10
STALE_DAYS = 3        # warn on the page if the newest draw is older than this
OUT_PATH = os.path.join("docs", "brief.html")


# -- data ---------------------------------------------------------------------

def load_data():
    try:
        with open("lottery_data.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def clean_draws(raw):
    """Return [(date, [numbers], bonus)] newest first, skipping malformed rows."""
    out = []
    for d in raw or []:
        try:
            date = str(d[0])
            nums = [int(n) for n in d[1]]
            bonus = d[2] if len(d) > 2 else None
            out.append((date, nums, bonus))
        except Exception:
            continue
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def analyse(draws, cfg, rng):
    balls, max_num = cfg["balls"], cfg["max_num"]
    universe = list(range(1, max_num + 1))

    cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    recent = [d for d in draws if d[0] >= cutoff]
    if len(recent) < MIN_WINDOW_DRAWS:
        recent = draws[:10]
    freq = Counter(n for d in recent for n in d[1])

    # gap = how many draws ago a number last appeared (len(draws) if never seen)
    gap = {n: len(draws) for n in universe}
    for idx, d in enumerate(draws):
        for n in d[1]:
            if n in gap and gap[n] == len(draws):
                gap[n] = idx

    hot_rank = sorted(universe, key=lambda n: (-freq[n], n))
    cold_rank = sorted(universe, key=lambda n: (freq[n], n))
    overdue_rank = sorted(universe, key=lambda n: (-gap[n], n))

    hot = sorted(hot_rank[:balls])
    cold = sorted(cold_rank[:balls])
    overdue = sorted(overdue_rank[:balls])

    hot_pool = hot_rank[: balls + 3]
    overdue_pool = overdue_rank[: balls + 3]

    def fill(nums):
        nums = list(dict.fromkeys(nums))
        if len(nums) < balls:
            spare = [n for n in universe if n not in nums]
            nums += rng.sample(spare, balls - len(nums))
        return sorted(nums[:balls])

    set_hot = fill(rng.sample(hot_pool, balls))
    half = balls // 2
    set_bal = fill(rng.sample(hot_pool, half) + rng.sample(overdue_pool, balls - half))
    set_over = fill(rng.sample(overdue_pool, balls))

    return {
        "window_draws": len(recent),
        "hot": hot, "cold": cold, "overdue": overdue,
        "picks": [("Hot", set_hot), ("Balanced", set_bal), ("Overdue", set_over)],
        "hot_set": set(hot), "cold_set": set(cold), "overdue_set": set(overdue),
    }


# -- html ---------------------------------------------------------------------

CSS = """
:root{--bg:#070b14;--panel:#0d1424;--line:#1c2b45;--cyan:#00f0ff;--orange:#ff8a1f;
--yellow:#ffe44d;--text:#d7e3f4;--dim:#7d90ad}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Rajdhani',Arial,sans-serif;
font-size:17px;line-height:1.35}
.wrap{max-width:480px;margin:0 auto;padding:0 14px 40px}
header{padding:22px 0 12px;text-align:center;border-bottom:1px solid var(--line)}
h1{margin:0;font-family:'Orbitron',Arial,sans-serif;font-size:22px;letter-spacing:3px;color:var(--cyan)}
.date{color:var(--yellow);font-size:15px;margin-top:4px}
.warn{margin:14px 0 0;padding:10px 12px;border:1px solid var(--orange);color:var(--orange);
border-radius:8px;font-size:15px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-top:16px}
.card h2{margin:0;font-family:'Orbitron',Arial,sans-serif;font-size:16px;color:var(--orange);letter-spacing:1px}
.sub{color:var(--dim);font-size:14px;margin:2px 0 8px}
.label{color:var(--cyan);font-size:13px;letter-spacing:1px;text-transform:uppercase;margin:10px 0 4px}
.row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.ball{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;
border-radius:50%;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:15px;
background:#16233b;color:var(--text);border:1px solid var(--line)}
.ball.hot{background:#3a1d08;border-color:var(--orange);color:var(--orange)}
.ball.cold{background:#06303a;border-color:var(--cyan);color:var(--cyan)}
.ball.over{background:#3a3408;border-color:var(--yellow);color:var(--yellow)}
.ball.bonus{border-style:dashed}
.pick{display:flex;gap:8px;align-items:center;margin-top:6px}
.pick b{min-width:78px;color:var(--text)}
footer{margin-top:22px;text-align:center;color:var(--dim);font-size:13px}
"""


def balls_html(nums, game_sets=None, plain=False, force=""):
    out = []
    for n in nums:
        cls = "ball"
        if force:
            cls += " " + force
        elif not plain and game_sets:
            if n in game_sets["hot_set"]:
                cls += " hot"
            elif n in game_sets["overdue_set"]:
                cls += " over"
            elif n in game_sets["cold_set"]:
                cls += " cold"
        out.append(f'<span class="{cls}">{n:02d}</span>')
    return "".join(out)


def game_card(cfg, draws, rng):
    name = html.escape(cfg["name"])
    if not draws:
        return (f'<section class="card"><h2>{name}</h2>'
                f'<p class="sub">No draw data available yet.</p></section>')

    a = analyse(draws, cfg, rng)
    last_date, last_nums, last_bonus = draws[0]
    bonus_html = ""
    if last_bonus not in (None, "", 0):
        try:
            bonus_html = f'<span class="ball bonus">{int(last_bonus):02d}</span>'
        except Exception:
            bonus_html = ""

    picks = "".join(
        f'<div class="pick"><b>{html.escape(label)}</b>'
        f'<div class="row">{balls_html(nums, plain=True)}</div></div>'
        for label, nums in a["picks"]
    )
    return f"""
<section class="card">
  <h2>{name}</h2>
  <p class="sub">Last draw {html.escape(last_date)} &middot; {a['window_draws']} draws analysed</p>
  <div class="label">Last numbers</div>
  <div class="row">{balls_html(last_nums, a)}{bonus_html}</div>
  <div class="label">Hot (most drawn)</div>
  <div class="row">{balls_html(a['hot'], force='hot')}</div>
  <div class="label">Cold (least drawn)</div>
  <div class="row">{balls_html(a['cold'], force='cold')}</div>
  <div class="label">Overdue (longest wait)</div>
  <div class="row">{balls_html(a['overdue'], force='over')}</div>
  <div class="label">Oracle picks</div>
  {picks}
</section>"""


def build_page(data):
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    cards = []
    newest = ""
    for key, cfg in GAMES.items():
        draws = clean_draws(data.get(key, {}).get("draws"))
        if draws and draws[0][0] > newest:
            newest = draws[0][0]
        rng = random.Random(f"{key}-{today_str}")  # same picks all day, new picks tomorrow
        cards.append(game_card(cfg, draws, rng))

    warning = ""
    if not newest:
        warning = '<div class="warn">No lottery data found. The next scheduled run will fill this in.</div>'
    else:
        age = (now.date() - datetime.strptime(newest, "%Y-%m-%d").date()).days
        if age > STALE_DAYS:
            warning = (f'<div class="warn">Data looks stale: newest draw is {age} days old '
                       f'({html.escape(newest)}). Check the daily GitHub Action.</div>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#070b14">
<title>Lotto Oracle Brief</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600&family=Rajdhani:wght@500;600&family=JetBrains+Mono:wght@700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>LOTTO ORACLE</h1>
    <div class="date">Morning Brief &middot; {now.strftime('%A, %B %d, %Y')}</div>
  </header>
  {warning}
  {''.join(cards)}
  <footer>Generated {now.strftime('%Y-%m-%d %H:%M UTC')} &middot; For entertainment only</footer>
</div>
</body>
</html>
"""


def main():
    data = load_data()
    page = build_page(data)
    os.makedirs("docs", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {OUT_PATH} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
