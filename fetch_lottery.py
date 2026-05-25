#!/usr/bin/env python3
"""
Runs in GitHub Actions to scrape lottery results and save to lottery_data.json.
Incremental: loads existing data first, only fetches new draws, never loses history.
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
MAX_BONUS_FETCHES = 15   # max individual draw-page requests per run


# ── helpers ──────────────────────────────────────────────────────────────────

def _bs(html):
    for p in ["lxml", "html.parser"]:
        try: return BeautifulSoup(html, p)
        except: pass
    return BeautifulSoup(html, "html.parser")

def _date(txt):
    for fmt in ["%B %d %Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d",
                "%A, %B %d, %Y", "%b %d %Y"]:
        try: return datetime.strptime(txt.strip(), fmt).strftime("%Y-%m-%d")
        except: pass
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

def _tail_nums(text, n):
    """
    Extract the last `n` (or n+1) integers from `text`, ignoring month/day words.
    Returns list of ints (length n or n+1 when a bonus digit follows).
    """
    tokens = re.findall(r"\d+", text)
    nums = [int(t) for t in tokens if 1 <= int(t) <= 99]
    # Take from the right — lottery numbers always appear after the date text
    return nums[-n-1:] if len(nums) >= n else []


# ── lotterycanada.com generic list scraper ───────────────────────────────────

def _lc_past_draws(game_slug, ball_count):
    """
    Scrape https://www.lotterycanada.com/{game_slug}/past-draws.
    Returns [(date, sorted_main_nums, bonus_or_grand)] with bonus=0 when absent.
    """
    url = f"https://www.lotterycanada.com/{game_slug}/past-draws"
    draws = []
    try:
        soup = _bs(_get(url).text)
        pat = re.compile(rf"/{re.escape(game_slug)}/(\d{{4}}-\d{{2}}-\d{{2}})")
        for a in soup.find_all("a", href=pat):
            date = pat.search(a["href"]).group(1)
            nums = _tail_nums(a.get_text(" ", strip=True), ball_count)
            if len(nums) >= ball_count:
                main   = sorted(nums[-ball_count-1:-1] if len(nums) > ball_count else nums[-ball_count:])
                bonus  = nums[-1] if len(nums) > ball_count else 0
                # For games where bonus IS in the link text (daily-grand), keep it;
                # for others it will be 0 and fetched separately.
                draws.append([date, main, bonus])
        print(f"  {len(draws)} draws from {url}")
    except Exception as e:
        print(f"  ERROR {url}: {e}")
    return draws


def _lc_draw_page(game_slug, date, ball_count):
    """
    Fetch one individual draw page and return (sorted_main, bonus).
    Looks for a tight cluster of ball_count+1 unique numbers all in 1-50.
    """
    url = f"https://www.lotterycanada.com/{game_slug}/{date}"
    try:
        text = _bs(_get(url).text).get_text(" ", strip=True)
        tokens = [int(t) for t in re.findall(r"\b(\d{1,2})\b", text) if 1 <= int(t) <= 50]
        # Slide a window of (ball_count+1) looking for all-unique group
        for i in range(len(tokens) - ball_count):
            w = tokens[i:i + ball_count + 1]
            if len(set(w)) == ball_count + 1:
                return sorted(w[:ball_count]), w[ball_count]
    except Exception as e:
        print(f"    could not get bonus for {date}: {e}")
    return None, None


# ── per-game fetchers ─────────────────────────────────────────────────────────

def fetch_lotto_max(existing):
    existing_map = {d[0]: d for d in existing}

    list_draws = _lc_past_draws("lotto-max", 7)
    if not list_draws:
        print("  WARNING: no Lotto Max data from lotterycanada — keeping existing")
        return existing

    fetches = 0
    result = []
    for date, main, bonus in list_draws:
        if date in existing_map:
            result.append(existing_map[date])   # already stored (with correct bonus)
            continue
        # New draw — fetch individual page for bonus
        if fetches < MAX_BONUS_FETCHES:
            m, b = _lc_draw_page("lotto-max", date, 7)
            if m:
                result.append([date, m, b or 0])
                fetches += 1
                time.sleep(0.4)
                continue
        result.append([date, main, bonus])

    # Preserve any existing draws not on the list page (very old history)
    list_dates = {d[0] for d in list_draws}
    for date, draw in existing_map.items():
        if date not in list_dates:
            result.append(draw)

    return result


def fetch_lotto_649(existing):
    existing_map = {d[0]: d for d in existing}

    list_draws = _lc_past_draws("lotto-649", 6)
    if not list_draws:
        print("  WARNING: no Lotto 649 data from lotterycanada — keeping existing")
        return existing

    fetches = 0
    result = []
    for date, main, bonus in list_draws:
        if date in existing_map:
            result.append(existing_map[date])
            continue
        if fetches < MAX_BONUS_FETCHES:
            m, b = _lc_draw_page("lotto-649", date, 6)
            if m:
                result.append([date, m, b or 0])
                fetches += 1
                time.sleep(0.4)
                continue
        result.append([date, main, bonus])

    list_dates = {d[0] for d in list_draws}
    for date, draw in existing_map.items():
        if date not in list_dates:
            result.append(draw)

    return result


def fetch_daily_grand(existing):
    """Daily Grand: 5 main numbers + 1 Grand Number — both appear in list links."""
    existing_map = {d[0]: d for d in existing}
    list_draws = _lc_past_draws("daily-grand", 5)
    if not list_draws:
        return existing

    result = []
    for date, main, grand in list_draws:
        if date in existing_map:
            result.append(existing_map[date])
        else:
            result.append([date, main, grand])

    list_dates = {d[0] for d in list_draws}
    for date, draw in existing_map.items():
        if date not in list_dates:
            result.append(draw)

    return result


def fetch_wclc(game_key, existing):
    """Western Canada Lottery — scrape WCLC print pages, merge with existing history."""
    ball_count = {"lotto_649": 6, "western_649": 6, "western_max": 7}[game_key]
    urls = {
        "lotto_649":   "https://www.wclc.com/winning-numbers/lotto-649-extra.htm"
                       "?channel=print&printMode=true&printFile=/lotto-649-extra.htm",
        "western_649": "https://www.wclc.com/winning-numbers/western-649-extra.htm"
                       "?channel=print&printMode=true&printFile=/western-649-extra.htm",
        "western_max": "https://www.wclc.com/winning-numbers/western-max-extra.htm"
                       "?channel=print&printMode=true&printFile=/western-max-extra.htm",
    }
    new_draws = []
    try:
        soup = _bs(_get(urls[game_key]).text)
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
            new_draws.append([d, nums, bonus])
        print(f"  {len(new_draws)} fresh draws from WCLC for {game_key}")
    except Exception as e:
        print(f"  {game_key} WCLC error: {e}")

    # Merge: start with fresh draws, then append any existing draws not already present
    merged_dates = {d[0] for d in new_draws}
    for draw in existing:
        if draw[0] not in merged_dates:
            new_draws.append(draw)

    return new_draws if new_draws else existing


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"Fetching lottery data — {now}")

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
        print(f"\nFetching {key}...")
        draws = fn()
        # Deduplicate by date, sort newest first
        seen, clean = set(), []
        for d in draws:
            if d[0] not in seen:
                seen.add(d[0]); clean.append(d)
        clean.sort(key=lambda x: x[0], reverse=True)
        data[key] = {"fetched_at": now, "draws": clean}
        print(f"  => {len(clean)} draws · latest: {clean[0][0] if clean else 'none'}")

    with open("lottery_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("\nSaved lottery_data.json ✓")


if __name__ == "__main__":
    main()
