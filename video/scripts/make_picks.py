"""Build src/picks.json for the video from ../lottery_data.json (Lotto Max)."""
import json, os
from collections import Counter

here = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(here, "..", "..", "lottery_data.json")))
draws = data["lotto_max"]["draws"]  # newest first: [date, nums, bonus]
POOL, BALLS, WINDOW = 50, 7, 50

recent = draws[:WINDOW]
freq = Counter(n for _, nums, _ in recent for n in nums)
hot = sorted(n for n, _ in freq.most_common(BALLS))

since = {}
for i, (_, nums, _) in enumerate(draws):
    for n in nums:
        since.setdefault(n, i)
overdue = sorted(sorted(range(1, POOL + 1), key=lambda n: since.get(n, len(draws)), reverse=True)[:BALLS])

out = {
    "game": "Lotto Max",
    "lastDraw": {"date": draws[0][0], "nums": draws[0][1], "bonus": draws[0][2]},
    "tickets": [
        {"label": "Hot Streak", "sub": f"Most drawn in last {WINDOW} draws", "nums": hot, "color": "#ffc940"},
        {"label": "Overdue Oracle", "sub": "Absent the longest", "nums": overdue, "color": "#00f0ff"},
    ],
}
json.dump(out, open(os.path.join(here, "..", "src", "picks.json"), "w"), indent=2)
print(json.dumps(out))
