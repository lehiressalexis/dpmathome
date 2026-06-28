"""
BuildAggregator : calcule le build optimal à partir d'une liste de parties.

Logique :
  - Items       : fréquence d'apparition pondérée par win-rate → top 6
  - Runes       : style principal et secondaire les plus fréquents
  - Summoner spells : paire la plus fréquente
  - Stats       : moyennes K/D/A
"""

from collections import Counter, defaultdict
from typing import Any


# IDs Summoner Spells courants (pour un affichage lisible)
SUMMONER_SPELL_NAMES = {
    1:  "Cleanse",
    3:  "Exhaust",
    4:  "Flash",
    6:  "Ghost",
    7:  "Heal",
    11: "Smite",
    12: "Teleport",
    13: "Clarity",
    14: "Ignite",
    21: "Barrier",
    32: "Mark",
}

# IDs Rune Styles
RUNE_STYLE_NAMES = {
    8000: "Précision",
    8100: "Domination",
    8200: "Sorcellerie",
    8300: "Inspiration",
    8400: "Résolution",
}


class BuildAggregator:

    def compute_best_build(self, matches: list[dict], champion_key: str) -> dict:
        if not matches:
            return {}

        total = len(matches)
        wins = sum(1 for m in matches if m.get("win"))
        win_rate = round(wins / total * 100, 1)

        return {
            "winRate": win_rate,
            "sampleSize": total,
            "items": self._best_items(matches),
            "summonerSpells": self._best_summoner_spells(matches),
            "runes": self._best_runes(matches),
            "averageStats": self._average_stats(matches),
        }

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _best_items(self, matches: list[dict]) -> list[dict]:
        """
        Agrège les items en tenant compte de leur ordre d'achat.
        Score = fréquence × 0.6 + win_rate × 0.4
        L'ordre moyen de chaque item est aussi calculé."""
        item_stats: dict[int, dict] = defaultdict(lambda: {
            "count": 0, "wins": 0, "positions": []
        })

        for match in matches:
            items = match.get("orderedItems", match.get("items", []))
            for position, item_id in enumerate(items):
                item_stats[item_id]["count"] += 1
                item_stats[item_id]["positions"].append(position + 1)
                if match.get("win"):
                    item_stats[item_id]["wins"] += 1

        total = len(matches)
        scored = []
        for item_id, stats in item_stats.items():
            freq = stats["count"] / total
            wr = stats["wins"] / stats["count"] if stats["count"] else 0
            avg_position = sum(stats["positions"]) / len(stats["positions"])
            score = freq * 0.6 + wr * 0.4
            scored.append((score, avg_position, item_id, stats))

        # Trier par score décroissant, puis par position moyenne croissante
        scored.sort(key=lambda x: (-x[0], x[1]))

        top_items = []
        for score, avg_pos, item_id, stats in scored[:6]:
            top_items.append({
                "itemId": item_id,
                "imageUrl": f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/item/{item_id}.png",
                "pickRate": round(stats["count"] / total * 100, 1),
                "winRate": round(stats["wins"] / stats["count"] * 100, 1) if stats["count"] else 0,
                "averageOrder": round(avg_pos, 1),  # ← position moyenne d'achat
                "score": round(score, 3),
            })

        # Retourner dans l'ordre d'achat moyen
        top_items.sort(key=lambda x: x["averageOrder"])
        return top_items

    # ------------------------------------------------------------------
    # Summoner Spells
    # ------------------------------------------------------------------

    def _best_summoner_spells(self, matches: list[dict]) -> dict:
        pair_counter: Counter = Counter()
        for match in matches:
            s1 = match.get("summonerSpell1")
            s2 = match.get("summonerSpell2")
            if s1 and s2:
                pair = tuple(sorted([s1, s2]))
                pair_counter[pair] += 1

        if not pair_counter:
            return {}

        best_pair, count = pair_counter.most_common(1)[0]
        return {
            "spell1": {"id": best_pair[0], "name": SUMMONER_SPELL_NAMES.get(best_pair[0], str(best_pair[0]))},
            "spell2": {"id": best_pair[1], "name": SUMMONER_SPELL_NAMES.get(best_pair[1], str(best_pair[1]))},
            "pickRate": round(count / len(matches) * 100, 1),
        }

    # ------------------------------------------------------------------
    # Runes
    # ------------------------------------------------------------------

    def _best_runes(self, matches: list[dict]) -> dict:
        primary_counter: Counter = Counter()
        secondary_counter: Counter = Counter()
        perk_counter: Counter = Counter()

        for match in matches:
            ps = match.get("primaryRuneStyle")
            ss = match.get("secondaryRuneStyle")
            if ps:
                primary_counter[ps] += 1
            if ss:
                secondary_counter[ss] += 1
            for perk in match.get("selectedPerks", []):
                if perk:
                    perk_counter[perk] += 1

        total = len(matches)
        best_primary = primary_counter.most_common(1)
        best_secondary = secondary_counter.most_common(1)

        # Récupérer les 9 perks les plus joués (4 primaires + 2 secondaires + 3 stats)
        top_perks = {perk_id for perk_id, _ in perk_counter.most_common(9)}

        return {
            "primaryStyle": {
                "id": best_primary[0][0] if best_primary else None,
                "name": RUNE_STYLE_NAMES.get(best_primary[0][0], "Inconnu") if best_primary else None,
                "pickRate": round(best_primary[0][1] / total * 100, 1) if best_primary else 0,
            },
            "secondaryStyle": {
                "id": best_secondary[0][0] if best_secondary else None,
                "name": RUNE_STYLE_NAMES.get(best_secondary[0][0], "Inconnu") if best_secondary else None,
                "pickRate": round(best_secondary[0][1] / total * 100, 1) if best_secondary else 0,
            },
            "selectedPerks": list(top_perks),
            "perkPickRates": {
                perk_id: round(count / total * 100, 1)
                for perk_id, count in perk_counter.most_common(20)
            }
        }

    # ------------------------------------------------------------------
    # Stats moyennes
    # ------------------------------------------------------------------

    def _average_stats(self, matches: list[dict]) -> dict:
        total = len(matches)
        if total == 0:
            return {}
        kills = sum(m.get("kills", 0) for m in matches) / total
        deaths = sum(m.get("deaths", 0) for m in matches) / total
        assists = sum(m.get("assists", 0) for m in matches) / total
        kda = (kills + assists) / max(deaths, 1)
        return {
            "kills": round(kills, 1),
            "deaths": round(deaths, 1),
            "assists": round(assists, 1),
            "kda": round(kda, 2),
        }
