#!/usr/bin/env python3
"""
Runs in GitHub Actions daily at 4:30 AM UTC.
Fetches only draws from the past 24 hours and merges into lottery_data.json.
"""
import json, requests, re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}

LC_BASE   = "https://ca.lottonumbers.com"
LCCA_BASE = "https://www.lotterycanada.com"
WCLC_BASE = "https://www.wclc.com/winning-numbers"

WEEKDAYS = {"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _bs(html):
    for p in ["lxml", "html.parser"]:
        try: return BeautifulSoup(html, p)
        except: pass
    return BeautifulSoup(html, "html.parser")

def _date(txt):
    txt = txt.strip()
    parts = txt.split(None, 1)
    if parts and parts[0] in WEEKDAYS:
        txt = parts[1].strip() if len(parts) > 1 else ""
    for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y",
                "%Y-%m-%d", "%A, %B %d, %Y"]:
        try:
            return datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def _get(url, timeout=20):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r

def load_existing():
    try:
        with open("lottery_data.json") as f:
            data = json.load(f)
        return {k: v.get("draws", []) for k, v in data.items()}
    except Exception:
        return {}

def _merge(new_draws, existing):
    merged = {d[0]: d for d in existing}
    for d in new_draws:
        merged[d[0]] = d
    return sorted(merged.values(), key=lambda x: x[0], reverse=True)

def recent_dates(days=2):
    """Return date strings for the past `days` days (to catch any timezone drift)."""
    today = datetime.utcnow().date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days + 1)]


# ── ca.lottonumbers.com single draw page ──────────────────────────────────────

def _draw_page(game_slug, date_str, ball_count):
    """Fetch one draw results page, return (sorted_main, bonus) or (None, None)."""
    url = f"{LC_BASE}/{game_slug}/numbers/{date_str}"
    try:
        soup = _bs(_get(url).text)
        # Find "Winning Numbers" heading then next <ul>
        for h in soup.find_all(["h2", "h3", "h4"]):
            if "winning" in h.get_text(strip=True).lower():
                ul = h.find_next("ul")
                if ul:
                    items = [li.get_text(strip=True) for li in ul.find_all("li")
                             if li.get_text(strip=True).isdigit()]
                    nums = [int(x) for x in items if 1 <= int(x) <= 50]
                    if len(nums) >= ball_count:
                        return sorted(nums[:ball_count]), (nums[ball_count] if len(nums) > ball_count else 0)
        # Fallback: any <ul> with the right count
        for ul in soup.find_all("ul"):
            items = [li.get_text(strip=True) for li in ul.find_all("li")
                     if li.get_text(strip=True).isdigit()]
            nums = [int(x) for x in items if 1 <= int(x) <= 50]
            if len(nums) >= ball_count:
                return sorted(nums[:ball_count]), (nums[ball_count] if len(nums) > ball_count else 0)
    except Exception as e:
        print(f"    {date_str}: {e}")
    return None, None


# ── WCLC parser ───────────────────────────────────────────────────────────────

def _parse_strong_ul(soup, ball_count):
    draws = []
    for strong in soup.find_all("strong"):
        d = _date(strong.get_text(strip=True))
        if not d:
            continue
        ul = strong.find_next("ul")
        if not ul:
            continue
        items = [li.get_text(strip=True) for li in ul.find_all("li")
                 if li.get_text(strip=True).isdigit()]
        if len(items) < ball_count:
            continue
        nums  = sorted(int(x) for x in items[:ball_count])
        bonus = int(items[ball_count]) if len(items) > ball_count else 0
        draws.append([d, nums, bonus])
    return draws


# ── per-game fetchers (24-hour focused) ──────────────────────────────────────

def fetch_lc_game(game_slug, ball_count, existing):
    """Try to fetch draw pages for the past 2 days; add any new results."""
    existing_dates = {d[0] for d in existing}
    new_draws = []
    for date_str in recent_dates(days=2):
        if date_str in existing_dates:
            print(f"    {date_str}: already stored")
            continue
        main, bonus = _draw_page(game_slug, date_str, ball_count)
        if main:
            new_draws.append([date_str, main, bonus or 0])
            print(f"    {date_str}: ✓ {main} bonus={bonus}")
        else:
            print(f"    {date_str}: no draw")
    return _merge(new_draws, existing)

def fetch_wclc(game_key, existing):
    """Fetch WCLC print page and add any draws from past 2 days."""
    ball_count = {"western_649": 6, "western_max": 7}[game_key]
    url_map = {
        "western_649": f"{WCLC_BASE}/western-649-extra.htm"
                       "?channel=print&printMode=true&printFile=/western-649-extra.htm",
        "western_max": f"{WCLC_BASE}/western-max-extra.htm"
                       "?channel=print&printMode=true&printFile=/western-max-extra.htm",
    }
    new_draws = []
    target_dates = set(recent_dates(days=2))
    try:
        soup = _bs(_get(url_map[game_key]).text)
        for draw in _parse_strong_ul(soup, ball_count):
            if draw[0] in target_dates:
                new_draws.append(draw)
                print(f"    {draw[0]}: ✓ {draw[1]} bonus={draw[2]}")
    except Exception as e:
        print(f"    WCLC error: {e}")
    return _merge(new_draws, existing)

def fetch_daily_grand(existing):
    """Daily Grand via lotterycanada.com and ca.lottonumbers.com."""
    existing_dates = {d[0] for d in existing}
    new_draws = []
    target_dates = set(recent_dates(days=2))

    # Try lotterycanada.com anchor links
    try:
        soup = _bs(_get(f"{LCCA_BASE}/daily-grand/past-draws").text)
        pat = re.compile(r"/daily-grand/(\d{4}-\d{2}-\d{2})")
        for a in soup.find_all("a", href=pat):
            date = pat.search(a["href"]).group(1)
            if date not in target_dates or date in existing_dates:
                continue
            raw = re.findall(r"\d+", a.get_text(" ", strip=True))
            nums = [int(n) for n in raw if 1 <= int(n) <= 99]
            if len(nums) >= 6:
                new_draws.append([date, sorted(nums[-6:-1]), nums[-1]])
                print(f"    {date}: ✓ via lotterycanada.com")
    except Exception as e:
        print(f"    lotterycanada.com error: {e}")

    # Fallback: ca.lottonumbers.com draw page
    for date_str in target_dates:
        if date_str in existing_dates or any(d[0] == date_str for d in new_draws):
            continue
        main, bonus = _draw_page("daily-grand", date_str, 5)
        if main:
            new_draws.append([date_str, main, bonus or 0])
            print(f"    {date_str}: ✓ via ca.lottonumbers.com")

    return _merge(new_draws, existing)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"Fetching last 24h lottery draws — {now}")
    print(f"Checking dates: {', '.join(recent_dates(days=2))}\n")

    existing = load_existing()
    data = {}

    jobs = {
        "lotto_max":   lambda: fetch_lc_game("lotto-max",   7, existing.get("lotto_max",   [])),
        "lotto_649":   lambda: fetch_lc_game("lotto-649",   6, existing.get("lotto_649",   [])),
        "western_649": lambda: fetch_wclc("western_649",       existing.get("western_649", [])),
        "western_max": lambda: fetch_wclc("western_max",       existing.get("western_max", [])),
        "daily_grand": lambda: fetch_daily_grand(              existing.get("daily_grand", [])),
    }

    for key, fn in jobs.items():
        print(f"── {key} ──")
        draws = fn()
        seen, clean = set(), []
        for d in draws:
            if d[0] not in seen:
                seen.add(d[0]); clean.append(d)
        clean.sort(key=lambda x: x[0], reverse=True)
        data[key] = {"fetched_at": now, "draws": clean}
        print(f"  => {len(clean)} total draws stored · latest: {clean[0][0] if clean else 'none'}\n")

    with open("lottery_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved lottery_data.json ✓")


if __name__ == "__main__":
    main()
