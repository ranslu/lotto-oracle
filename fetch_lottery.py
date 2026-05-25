#!/usr/bin/env python3
"""
Runs in GitHub Actions to scrape lottery results and save to lottery_data.json.
Incremental: loads existing data, only fetches what's new, never loses history.

Sources:
  ca.lottonumbers.com  — Lotto Max, Lotto 649 (static HTML + year archives)
  lotterycanada.com    — Daily Grand (static-rendered recent draws)
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

WEEKDAYS = {"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"}

LC_BASE    = "https://ca.lottonumbers.com"   # ca.lottonumbers.com
LCCA_BASE  = "https://www.lotterycanada.com" # lotterycanada.com
WCLC_BASE  = "https://www.wclc.com/winning-numbers"


# ── helpers ───────────────────────────────────────────────────────────────────

def _bs(html):
    for p in ["lxml", "html.parser"]:
        try: return BeautifulSoup(html, p)
        except: pass
    return BeautifulSoup(html, "html.parser")

def _date(txt):
    """Parse many date formats → YYYY-MM-DD string, or None."""
    txt = txt.strip()
    # Strip leading weekday if present: "Friday May 22 2026" → "May 22 2026"
    parts = txt.split(None, 1)
    if parts and parts[0] in WEEKDAYS:
        txt = parts[1].strip() if len(parts) > 1 else ""
    for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%Y-%m-%d",
                "%A, %B %d, %Y"]:
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
    """Merge new draws with existing, new overrides on same date, keeps all dates."""
    merged = {d[0]: d for d in existing}
    for draw in new_draws:
        merged[draw[0]] = draw
    return sorted(merged.values(), key=lambda x: x[0], reverse=True)


# ── ca.lottonumbers.com parser ────────────────────────────────────────────────

def _parse_strong_ul(soup, ball_count):
    """
    Parse pages that use <strong> for the draw date and <ul><li> for numbers.
    Works for both ca.lottonumbers.com and wclc.com.
    Returns [(date, sorted_main_nums, bonus)].
    """
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

def _fetch_lc_years(game_slug, ball_count, num_years=3):
    """
    Fetch year-archive pages from ca.lottonumbers.com.
    URL: /lotto-max/numbers/2025, /lotto-649/numbers/2025, etc.
    Fetches the current year plus `num_years-1` previous years.
    """
    draws = []
    current_year = datetime.utcnow().year
    for year in range(current_year, current_year - num_years, -1):
        url = f"{LC_BASE}/{game_slug}/numbers/{year}"
        try:
            soup = _bs(_get(url).text)
            year_draws = _parse_strong_ul(soup, ball_count)
            draws.extend(year_draws)
            print(f"    {year}: {len(year_draws)} draws")
            if year_draws:
                time.sleep(0.4)
        except Exception as e:
            print(f"    {year}: error — {e}")
    return draws


# ── per-game fetchers ─────────────────────────────────────────────────────────

def fetch_lotto_max(existing):
    """
    ca.lottonumbers.com/lotto-max/numbers/YYYY — static HTML, year archives.
    Fetches current + 2 prior years; merges with all existing history.
    """
    existing_map = {d[0]: d for d in existing}
    num_years = 3 if len(existing) < 80 else 2

    print(f"  fetching {num_years} year archives from ca.lottonumbers.com...")
    new_draws = _fetch_lc_years("lotto-max", 7, num_years)

    if not new_draws:
        print("  WARNING: no Lotto Max data — keeping existing")
        return existing

    print(f"  total from site: {len(new_draws)}")
    return _merge(new_draws, existing)


def fetch_lotto_649(existing):
    """
    ca.lottonumbers.com/lotto-649/numbers/YYYY — static HTML, year archives.
    """
    num_years = 3 if len(existing) < 80 else 2
    print(f"  fetching {num_years} year archives from ca.lottonumbers.com...")
    new_draws = _fetch_lc_years("lotto-649", 6, num_years)

    if not new_draws:
        print("  WARNING: no Lotto 649 data — keeping existing")
        return existing

    print(f"  total from site: {len(new_draws)}")
    return _merge(new_draws, existing)


def fetch_daily_grand(existing):
    """
    lotterycanada.com/daily-grand/past-draws — recent draws via static links.
    Also tries ca.lottonumbers.com year archives.
    """
    new_draws = []

    # Try lotterycanada.com (server-side rendered anchor tags with numbers)
    try:
        url = f"{LCCA_BASE}/daily-grand/past-draws"
        soup = _bs(_get(url).text)
        pat = re.compile(r"/daily-grand/(\d{4}-\d{2}-\d{2})")
        for a in soup.find_all("a", href=pat):
            date = pat.search(a["href"]).group(1)
            raw = re.findall(r"\d+", a.get_text(" ", strip=True))
            nums = [int(n) for n in raw if 1 <= int(n) <= 99]
            # Format: "02 10 13 26 46 04" → 5 main + 1 grand
            if len(nums) >= 6:
                new_draws.append([date, sorted(nums[-6:-1]), nums[-1]])
        print(f"  {len(new_draws)} draws from lotterycanada.com/daily-grand")
    except Exception as e:
        print(f"  lotterycanada daily-grand error: {e}")

    # Also try ca.lottonumbers.com year archives for daily-grand
    try:
        archive_draws = _fetch_lc_years("daily-grand", 5, 2)
        new_draws.extend(archive_draws)
        print(f"  total after ca.lottonumbers.com: {len(new_draws)}")
    except Exception as e:
        print(f"  ca.lottonumbers.com daily-grand error: {e}")

    if not new_draws:
        return existing

    return _merge(new_draws, existing)


def fetch_wclc(game_key, existing):
    """
    wclc.com print-mode pages — Western 649, Western Max.
    Merges with existing to preserve history the print page no longer shows.
    """
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
        # Deduplicate by date, sort newest first
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
