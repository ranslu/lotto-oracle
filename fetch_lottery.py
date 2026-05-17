#!/usr/bin/env python3
"""
Runs in GitHub Actions to scrape lottery results and save to lottery_data.json.
GitHub's servers are not blocked by lottery sites.
"""
import json, requests, re
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}

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

def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r

def _parse_lottomaxnumbers(soup):
    found = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2: continue
        lnk = cells[0].find("a")
        raw = lnk.get_text(strip=True) if lnk else cells[0].get_text(strip=True)
        d = _date(raw)
        if not d: continue
        nums, bonus = [], 0
        for i, li in enumerate(cells[1].find_all("li")):
            t = li.get_text(strip=True)
            if not t.isdigit(): continue
            if i < 7: nums.append(int(t))
            else: bonus = int(t)
        if len(nums) == 7:
            found.append([d, sorted(nums), bonus])
    return found

def fetch_lotto_max():
    sources = [
        "https://www.lottomaxnumbers.com/past-numbers",
        "https://ca.lottonumbers.com/lotto-max/past-numbers",
        "https://www.lotterycanada.com/lotto-max",
    ]
    for url in sources:
        try:
            print(f"  trying {url}")
            soup = _bs(_get(url).text)
            draws = _parse_lottomaxnumbers(soup)
            if draws:
                print(f"  got {len(draws)} draws from {url}")
                return draws
        except Exception as e:
            print(f"  {url} failed: {e}")
    return []

def fetch_wclc(game_key):
    ball_count = {"lotto_649": 6, "western_649": 6, "western_max": 7}[game_key]
    urls = {
        "lotto_649":  "https://www.wclc.com/winning-numbers/lotto-649-extra.htm?channel=print&printMode=true&printFile=/lotto-649-extra.htm",
        "western_649":"https://www.wclc.com/winning-numbers/western-649-extra.htm?channel=print&printMode=true&printFile=/western-649-extra.htm",
        "western_max":"https://www.wclc.com/winning-numbers/western-max-extra.htm?channel=print&printMode=true&printFile=/western-max-extra.htm",
    }
    draws = []
    try:
        soup = _bs(_get(urls[game_key]).text)
        for strong in soup.find_all("strong"):
            d = _date(strong.get_text(strip=True))
            if not d: continue
            ul = strong.find_next("ul")
            if not ul: continue
            items = [li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True).isdigit()]
            if len(items) < ball_count: continue
            nums = sorted([int(x) for x in items[:ball_count]])
            bonus = int(items[ball_count]) if len(items) > ball_count else 0
            draws.append([d, nums, bonus])
    except Exception as e:
        print(f"  {game_key} error: {e}")
    return draws

def fetch_daily_grand():
    draws = []
    try:
        soup = _bs(_get("https://www.lotteryextreme.com/canada/dailygrand-winningnumbers").text)
        for td in soup.find_all("td"):
            txt = td.get_text(" ", strip=True)
            m = re.search(r"\((\d{4}-\d{2}-\d{2})", txt)
            if m:
                lis = td.find_all("li")
                nums = [int(li.get_text(strip=True)) for li in lis if li.get_text(strip=True).isdigit()]
                if len(nums) >= 6:
                    draws.append([m.group(1), sorted(nums[:5]), nums[5]])
    except Exception as e:
        print(f"  daily_grand error: {e}")
    return draws

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"Fetching lottery data — {now}")
    data = {}

    fetchers = {
        "lotto_max":   fetch_lotto_max,
        "lotto_649":   lambda: fetch_wclc("lotto_649"),
        "western_649": lambda: fetch_wclc("western_649"),
        "western_max": lambda: fetch_wclc("western_max"),
        "daily_grand": fetch_daily_grand,
    }

    for key, fn in fetchers.items():
        print(f"Fetching {key}...")
        draws = fn()
        # Deduplicate by date
        seen, clean = set(), []
        for d in draws:
            if d[0] not in seen:
                seen.add(d[0]); clean.append(d)
        clean.sort(key=lambda x: x[0], reverse=True)
        data[key] = {"fetched_at": now, "draws": clean}
        print(f"  {len(clean)} draws · latest: {clean[0][0] if clean else 'none'}")

    with open("lottery_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved lottery_data.json")

if __name__ == "__main__":
    main()
