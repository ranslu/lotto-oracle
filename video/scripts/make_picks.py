"""Build src/picks.json for the video from ../lottery_data.json."""
import json, os
from collections import Counter

here = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(here, "..", "..", "lottery_data.json")))
WINDOW = 50
GAMES = [  # (data key, display name, pool, balls, accent color)
    ("lotto_max", "Lotto Max", 50, 7, "#9b8cff"),
    ("lotto_649", "Lotto 6/49", 49, 6, "#ff6b8b"),
]


def game_picks(key, name, pool, balls, color):
    draws = data[key]["draws"]  # newest first: [date, nums, bonus]
    freq = Counter(n for _, nums, _ in draws[:WINDOW] for n in nums)
    hot = sorted(n for n, _ in freq.most_common(balls))
    since = {}
    for i, (_, nums, _) in enumerate(draws):
        for n in nums:
            since.setdefault(n, i)
    overdue = sorted(sorted(range(1, pool + 1), key=lambda n: since.get(n, len(draws)), reverse=True)[:balls])
    return {
        "game": name,
        "color": color,
        "lastDraw": {"date": draws[0][0], "nums": draws[0][1], "bonus": draws[0][2]},
        "tickets": [
            {"label": "Hot Streak", "sub": f"Most drawn in last {WINDOW} draws", "nums": hot, "color": "#ffc940"},
            {"label": "Overdue Oracle", "sub": "Absent the longest", "nums": overdue, "color": "#00f0ff"},
        ],
    }


out = {"games": [game_picks(*g) for g in GAMES]}
json.dump(out, open(os.path.join(here, "..", "src", "picks.json"), "w"), indent=2)
print(json.dumps(out))
