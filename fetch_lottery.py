#!/usr/bin/env python3
"""
Runs in GitHub Actions to scrape lottery results and save to lottery_data.json.
Incremental: loads existing data, only fetches new draws, never loses history.

Sources:
  ca.lottonumbers.com  — Lotto Max, Lotto 649 (year-archive for dates + per-draw for numbers)
  lotterycanada.com    — Daily Grand
  wclc.com             — Western 649, Western Max
"""
import json, requests, re, time
from datetime import datetime
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

# Max individual draw-page fetches per game per run (builds history incrementally)
MAX_FETCHES_PER_GAME = 50


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
    """Merge new into existing; new wins on same date. Return sorted newest-first."""
    merged = {d[0]: d for d in existing}
    for d in new_draws:
        merged[d[0]] = d
    return sorted(merged.values(), key=lambda x: x[0], reverse=True)


# ── ca.lottonumbers.com scrapers ──────────────────────────────────────────────

def _year_dates(game_slug, year):
    """
    Fetch the year archive page and return all draw dates found in hrefs.
    Fast: only regex on raw HTML, no full parse.
    URL: https://ca.lottonumbers.com/{game_slug}/numbers/{year}
    """
    url = f"{LC_BASE}/{game_slug}/numbers/{year}"
    try:
        r = _get(url)
        pat = re.compile(rf"/{re.escape(game_slug)}/numbers/(\d{{4}}-\d{{2}}-\d{{2}})")
        dates = list(dict.fromkeys(pat.findall(r.text)))   # unique, order-preserved
        print(f"    {year}: {len(dates)} draw dates found")
        return dates
    except Exception as e:
        print(f"    {year}: error — {e}")
        return []

def _draw_page(game_slug, date_str, ball_count):
    """
    Fetch one draw page and return (sorted_main_nums, bonus) or (None, None).
    URL: https://ca.lottonumbers.com/{game_slug}/numbers/YYYY-MM-DD
    Page has <h2>Winning Numbers</h2> followed by <ul><li>number</li>…
    """
    url = f"{LC_BASE}/{game_slug}/numbers/{date_str}"
    try:
        soup = _bs(_get(url).text)

        # Primary: find "Winning Numbers" heading then next <ul>
        for h in soup.find_all(["h2", "h3", "h4"]):
            if "winning" in h.get_text(strip=True).lower():
                ul = h.find_next("ul")
                if ul:
                    items = [li.get_text(strip=True) for li in ul.find_all("li")
                             if li.get_text(strip=True).isdigit()]
                    nums = [int(x) for x in items if 1 <= int(x) <= 50]
                    if len(nums) >= ball_count:
                        return sorted(nums[:ball_count]), (nums[ball_count] if len(nums) > ball_count else 0)

        # Fallback: find any <ul> with the right count of lottery numbers
        for ul in soup.find_all("ul"):
            items = [li.get_text(strip=True) for li in ul.find_all("li")
                     if li.get_text(strip=True).isdigit()]
            nums = [int(x) for x in items if 1 <= int(x) <= 50]
            if len(nums) >= ball_count:
                return sorted(nums[:ball_count]), (nums[ball_count] if len(nums) > ball_count else 0)

    except Exception as e:
        print(f"      {date_str} error: {e}")
    return None, None

def _fetch_lc_game(game_slug, ball_count, existing, num_years=3):
    """
    Main incremental fetcher for ca.lottonumbers.com games.
    1. Collects draw dates from year-archive pages (fast, no JS needed).
    2. Fetches individual draw pages only for dates not already in `existing`.
    3. Caps new fetches at MAX_FETCHES_PER_GAME per run.
    """
    existing_map = {d[0]: d for d in existing}
    current_year = datetime.utcnow().year

    # Gather all known draw dates across the requested years
    all_dates = []
    for year in range(current_year, current_year - num_years, -1):
        dates = _year_dates(game_slug, year)
        all_dates.extend(dates)
        if dates:
            time.sleep(0.3)

    if not all_dates:
        print(f"  WARNING: no dates found for {game_slug} — keeping existing")
        return existing

    # Determine which dates are new (not in existing)
    new_dates = [d for d in all_dates if d not in existing_map]
    print(f"  {len(all_dates)} total dates, {len(new_dates)} new")

    # Fetch individual draw pages for new dates (capped)
    fetched = []
    for date_str in new_dates[:MAX_FETCHES_PER_GAME]:
        main, bonus = _draw_page(game_slug, date_str, ball_count)
        if main:
            fetched.append([date_str, main, bonus or 0])
        time.sleep(0.35)

    if len(new_dates) > MAX_FETCHES_PER_GAME:
        remaining = len(new_dates) - MAX_FETCHES_PER_GAME
        print(f"  {remaining} dates still pending (will fetch on next runs)")

    print(f"  fetched {len(fetched)} new draws this run")
    return _merge(fetched, existing)


# ── WCLC parser (unchanged — static HTML, strong+ul structure) ───────────────

def _parse_strong_ul(soup, ball_count):
    """Parse pages using <strong>date</strong> … <ul><li>num</li>… structure."""
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


# ── per-game fetchers ─────────────────────────────────────────────────────────

def fetch_lotto_max(existing):
    print(f"  existing: {len(existing)} draws")
    num_years = 3 if len(existing) < 80 else 2
    return _fetch_lc_game("lotto-max", 7, existing, num_years)

def fetch_lotto_649(existing):
    print(f"  existing: {len(existing)} draws")
    num_years = 3 if len(existing) < 80 else 2
    return _fetch_lc_game("lotto-649", 6, existing, num_years)

def fetch_daily_grand(existing):
    """
    Scrape lotterycanada.com/daily-grand/past-draws (server-side rendered links).
    Also try ca.lottonumbers.com year archives.
    """
    new_draws = []

    # lotterycanada.com: recent draws in server-side-rendered anchor tags
    try:
        url = f"{LCCA_BASE}/daily-grand/past-draws"
        soup = _bs(_get(url).text)
        pat = re.compile(r"/daily-grand/(\d{4}-\d{2}-\d{2})")
        for a in soup.find_all("a", href=pat):
            date = pat.search(a["href"]).group(1)
            raw = re.findall(r"\d+", a.get_text(" ", strip=True))
            nums = [int(n) for n in raw if 1 <= int(n) <= 99]
            if len(nums) >= 6:
                new_draws.append([date, sorted(nums[-6:-1]), nums[-1]])
        print(f"  {len(new_draws)} draws from lotterycanada.com")
    except Exception as e:
        print(f"  lotterycanada.com error: {e}")

    # Also try ca.lottonumbers.com daily-grand year archive
    existing_map = {d[0]: d for d in existing}
    current_year = datetime.utcnow().year
    for year in [current_year, current_year - 1]:
        try:
            dates = _year_dates("daily-grand", year)
            new_dates = [d for d in dates if d not in existing_map][:20]
            for date_str in new_dates:
                main, bonus = _draw_page("daily-grand", date_str, 5)
                if main:
                    new_draws.append([date_str, main, bonus or 0])
                time.sleep(0.35)
        except Exception as e:
            print(f"  daily-grand {year} error: {e}")

    if not new_draws:
        return existing
    return _merge(new_draws, existing)

def fetch_wclc(game_key, existing):
    """WCLC print-mode pages for western games. Merges with existing history."""
    ball_count = {"western_649": 6, "western_max": 7}[game_key]
    url_map = {
        "western_649": f"{WCLC_BASE}/western-649-extra.htm"
                       "?channel=print&printMode=true&printFile=/western-649-extra.htm",
        "western_max": f"{WCLC_BASE}/western-max-extra.htm"
                       "?channel=print&printMode=true&printFile=/western-max-extra.htm",
    }
    new_draws = []
    try:
        soup = _bs(_get(url_map[game_key]).text)
        new_draws = _parse_strong_ul(soup, ball_count)
        print(f"  {len(new_draws)} fresh draws from WCLC")
    except Exception as e:
        print(f"  WCLC {game_key} error: {e}")

    return _merge(new_draws, existing)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"Fetching lottery data — {now}\n")

    existing = load_existing()
    data = {}

    jobs = {
        "lotto_max":   lambda: fetch_lotto_max(existing.get("lotto_max",   [])),
        "lotto_649":   lambda: fetch_lotto_649(existing.get("lotto_649",   [])),
        "western_649": lambda: fetch_wclc("western_649", existing.get("western_649", [])),
        "western_max": lambda: fetch_wclc("western_max", existing.get("western_max", [])),
        "daily_grand": lambda: fetch_daily_grand(existing.get("daily_grand", [])),
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
        print(f"  => {len(clean)} draws · latest: {clean[0][0] if clean else 'none'}\n")

    with open("lottery_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved lottery_data.json ✓")


if __name__ == "__main__":
    main()
