#!/usr/bin/env python3
"""
Daily lottery picks emailer — uses last 30 days of draw data.
Run after fetch_lottery.py in GitHub Actions.
"""
import json, os, smtplib, random
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import Counter

GMAIL_ADDRESS    = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASS   = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT        = os.environ["RECIPIENT_EMAIL"]

GAMES = {
    "lotto_max":   {"name": "Lotto Max",   "balls": 7,  "max_num": 50, "color": "#7c3aed"},
    "lotto_649":   {"name": "Lotto 6/49",  "balls": 6,  "max_num": 49, "color": "#1d4ed8"},
    "daily_grand": {"name": "Daily Grand", "balls": 5,  "max_num": 49, "color": "#065f46"},
    "western_max": {"name": "Western Max", "balls": 7,  "max_num": 50, "color": "#92400e"},
    "western_649": {"name": "Western 649", "balls": 6,  "max_num": 49, "color": "#9d174d"},
}


# ── data loading ──────────────────────────────────────────────────────────────

def load_draws(game_key, days=30):
    """Return draws from the last `days` days for a game."""
    try:
        with open("lottery_data.json") as f:
            data = json.load(f)
        draws = data.get(game_key, {}).get("draws", [])
    except Exception:
        return []

    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [d for d in draws if d[0] >= cutoff]


# ── pick generation ───────────────────────────────────────────────────────────

def generate_picks(draws, balls, max_num):
    """
    Generate 3 sets of picks based on last-30-days frequency:
      Set 1 — Hot:      top-frequency numbers
      Set 2 — Balanced: mix of hot + cold
      Set 3 — Lucky:    lightly weighted random
    """
    all_nums = [n for draw in draws for n in draw[1]]
    freq = Counter(all_nums)
    universe = list(range(1, max_num + 1))

    # Hot: most frequent
    hot = [n for n, _ in freq.most_common(balls * 2)]
    set1 = sorted(random.sample(hot[:max(balls, len(hot))], min(balls, len(hot))))
    if len(set1) < balls:                              # pad if not enough data
        pad = [n for n in universe if n not in set1]
        set1 += random.sample(pad, balls - len(set1))
        set1 = sorted(set1)

    # Balanced: half hot, half cold/unseen
    cold = [n for n in universe if n not in freq or freq[n] == min(freq.values())]
    if not cold:
        cold = [n for n in universe if n not in hot[:balls]]
    half = balls // 2
    hot_part  = sorted(random.sample(hot[:balls], min(half, len(hot[:balls]))))
    cold_part = sorted(random.sample(cold, min(balls - half, len(cold))))
    set2 = sorted(hot_part + cold_part)
    if len(set2) < balls:
        pad = [n for n in universe if n not in set2]
        set2 += random.sample(pad, balls - len(set2))
        set2 = sorted(set2)

    # Lucky: weighted random (higher freq = slightly higher weight)
    weights = [freq.get(n, 0) + 1 for n in universe]
    set3 = sorted(random.sample(
        random.choices(universe, weights=weights, k=balls * 4)[:balls * 2],
        min(balls, balls * 2)
    ))
    set3 = sorted(list(dict.fromkeys(set3)))[:balls]
    if len(set3) < balls:
        pad = [n for n in universe if n not in set3]
        set3 += random.sample(pad, balls - len(set3))
        set3 = sorted(set3)

    return set1, set2, set3


# ── HTML builder ──────────────────────────────────────────────────────────────

def ball_html(num, color):
    # Table-based circle: div/span border-radius circles collapse in some email
    # clients (Outlook desktop). A fixed-size table cell renders reliably everywhere.
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="display:inline-table;margin:4px;">'
        f'<tr><td width="48" height="48" align="center" valign="middle" '
        f'style="width:48px;height:48px;border-radius:50%;background:{color};'
        f'color:#ffffff;font-weight:800;font-size:19px;font-family:Arial,sans-serif;'
        f'line-height:48px;text-align:center;">{num:02d}</td></tr>'
        f'</table>'
    )

def picks_row(label, nums, color):
    balls = "".join(ball_html(n, color) for n in nums)
    return (
        f'<tr><td style="padding:8px 10px;color:#374151;font-size:15px;'
        f'font-weight:700;white-space:nowrap;">{label}</td>'
        f'<td style="padding:4px 0;">{balls}</td></tr>'
    )

def game_section(game_key, cfg, draws):
    if not draws:
        return f'<p style="color:#888;">No draw data available for {cfg["name"]} in the last 30 days.</p>'

    s1, s2, s3 = generate_picks(draws, cfg["balls"], cfg["max_num"])
    color = cfg["color"]

    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;
                padding:20px;margin-bottom:20px;">
      <h2 style="margin:0 0 4px;color:{color};font-size:18px;">{cfg['name']}</h2>
      <p style="margin:0 0 12px;color:#6b7280;font-size:12px;">
        Based on {len(draws)} draws in the last 30 days
      </p>
      <table style="border-collapse:collapse;">
        {picks_row('🔥 Hot',      s1, color)}
        {picks_row('⚖️ Balanced', s2, color)}
        {picks_row('🍀 Lucky',    s3, color)}
      </table>
    </div>"""

def build_html(sections):
    today = datetime.utcnow().strftime("%A, %B %d, %Y")
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:30px auto;background:#f3f4f6;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0a1f3c,#0d2a50);
                border-radius:12px 12px 0 0;padding:28px;text-align:center;">
      <div style="font-size:36px;margin-bottom:8px;">🔮</div>
      <h1 style="margin:0;color:#00f0ff;font-size:22px;letter-spacing:2px;">LOTTO ORACLE</h1>
      <p style="margin:6px 0 0;color:#ffe44d;font-size:13px;">Daily Picks — {today}</p>
    </div>

    <!-- Body -->
    <div style="background:#f9fafb;padding:24px;">
      <p style="color:#374151;font-size:13px;margin:0 0 20px;">
        Here are today's picks, generated from the <strong>last 30 days</strong> of draw history.
        Good luck! 🎱
      </p>
      {''.join(sections)}
    </div>

    <!-- Footer -->
    <div style="background:#1f2937;border-radius:0 0 12px 12px;
                padding:16px;text-align:center;">
      <p style="margin:0;color:#9ca3af;font-size:11px;">
        Generated by Lotto Oracle &nbsp;·&nbsp; For entertainment purposes only
      </p>
    </div>

  </div>
</body>
</html>"""


# ── send email ────────────────────────────────────────────────────────────────

def send_email(html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔮 Lotto Oracle Picks — {datetime.utcnow().strftime('%b %d, %Y')}"
    msg["From"]    = f"Lotto Oracle <{GMAIL_ADDRESS}>"
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT, msg.as_string())

    print(f"Email sent to {RECIPIENT}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Generating picks — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    sections = []
    for key, cfg in GAMES.items():
        draws = load_draws(key, days=30)
        print(f"  {cfg['name']}: {len(draws)} draws in last 30 days")
        sections.append(game_section(key, cfg, draws))

    html = build_html(sections)
    send_email(html)
    print("Done ✓")


if __name__ == "__main__":
    main()
