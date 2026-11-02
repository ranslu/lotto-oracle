"""Shared blended scoring for all ticket generators (app + email).

Score per number = weighted mix of:
  pop   - how often it was drawn recently ("most popular")
  due   - how many draws since it last appeared ("overdue")
  lucky - member of this month's zodiac lucky list
  astro - numerology master number or multiple of 7/9
"""
import random
from datetime import datetime

ASTRO_LUCKY = {
    1: {"sign":"Capricorn",   "nums":[4,8,13,17,22,26,31,35,40,44,49]},
    2: {"sign":"Aquarius",    "nums":[7,11,16,20,25,29,34,38,43,47,2]},
    3: {"sign":"Pisces",      "nums":[3,7,12,16,21,25,30,34,39,43,48]},
    4: {"sign":"Aries",       "nums":[9,14,18,23,27,32,36,41,45,5,19]},
    5: {"sign":"Taurus",      "nums":[6,10,15,19,24,28,33,37,42,46,1]},
    6: {"sign":"Gemini",      "nums":[5,9,14,18,23,27,32,36,41,45,50]},
    7: {"sign":"Cancer",      "nums":[2,7,11,16,20,25,29,34,38,43,47]},
    8: {"sign":"Leo",         "nums":[1,6,10,15,19,24,28,33,37,42,46]},
    9: {"sign":"Virgo",       "nums":[8,13,17,22,26,31,35,40,44,49,4]},
   10: {"sign":"Libra",       "nums":[6,11,15,20,24,29,33,38,42,47,3]},
   11: {"sign":"Scorpio",     "nums":[9,13,18,22,27,31,36,40,45,49,8]},
   12: {"sign":"Sagittarius", "nums":[3,8,12,17,21,26,30,35,39,44,48]},
}
NUMEROLOGY_MASTER = [11,22,33]

DEFAULT_WEIGHTS = {"pop": 0.35, "due": 0.25, "lucky": 0.25, "astro": 0.15}
ASTRO_WEIGHTS   = {"pop": 0.15, "due": 0.15, "lucky": 0.40, "astro": 0.30}


def blend_scores(freq, draws_since, pool, month=None, weights=None):
    w = weights or DEFAULT_WEIGHTS
    lucky = set(ASTRO_LUCKY[month or datetime.now().month]["nums"])
    rng = range(1, pool + 1)
    mx_f = max((freq.get(n, 0) for n in rng), default=0) or 1
    mx_d = max((draws_since.get(n, 0) for n in rng), default=0) or 1
    out = {}
    for n in rng:
        astro = n in NUMEROLOGY_MASTER or n % 7 == 0 or n % 9 == 0
        out[n] = (w["pop"] * freq.get(n, 0) / mx_f + w["due"] * draws_since.get(n, 0) / mx_d
                  + w["lucky"] * (n in lucky) + w["astro"] * astro)
    return out


def top_blended(scores, k):
    return [n for n, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:k]]


def weighted_pick(scores, balls, floor=0.05):
    nums = list(scores)
    wts = [scores[n] + floor for n in nums]
    picked = []
    for _ in range(min(balls, len(nums))):
        i = random.choices(range(len(nums)), weights=wts)[0]
        picked.append(nums.pop(i))
        wts.pop(i)
    return sorted(picked)
