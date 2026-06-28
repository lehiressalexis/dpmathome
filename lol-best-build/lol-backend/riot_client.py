"""
Client Riot Games API.
Gère : Data Dragon (champions/items), Ladder, Summoner, Match v5.
"""

import os
import requests
from functools import lru_cache
from dotenv import load_dotenv
import json
import time
from datetime import datetime,timedelta

load_dotenv()

# Routing par région → cluster continental (pour Match v5)
REGIONAL_ROUTING = {
    "euw1": "europe",
    "eun1": "europe",
    "tr1":  "europe",
    "ru":   "europe",
    "na1":  "americas",
    "br1":  "americas",
    "la1":  "americas",
    "la2":  "americas",
    "kr":   "asia",
    "jp1":  "asia",
    "oc1":  "sea",
}

QUEUE_IDS = {
    "ranked_solo": 420,
    "ranked_flex": 440,
}

QUEUE_TYPE_PARAM = {
    "ranked_solo": "RANKED_SOLO_5x5",
    "ranked_flex": "RANKED_FLEX_SR",
}

CACHE_FILE = os.path.join(os.path.dirname(__file__), "mastery_cache.json")
CACHE_TTL_HOURS = 24

class RiotClient:
    def __init__(self):
        self.api_key = os.getenv("RIOT_API_KEY")
        if not self.api_key:
            raise EnvironmentError("RIOT_API_KEY manquante dans le fichier .env")
        self.patch = self._fetch_latest_patch()
        self._champion_map: dict = {}   # key (str int) → champion info
        self._champion_by_name: dict = {}  # lowername → champion info

    def _load_cache(self) -> dict:
        if not os.path.exists(CACHE_FILE):
            return {}
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    def _save_cache(self, cache: dict):
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    # ------------------------------------------------------------------
    # Data Dragon
    # ------------------------------------------------------------------

    def _fetch_latest_patch(self) -> str:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10)
        r.raise_for_status()
        return r.json()[0]

    def _load_champion_map(self):
        if self._champion_map:
            return
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch}/data/fr_FR/champion.json"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]
        for champ_id, info in data.items():
            entry = {
                "id": champ_id,           # ex: "Ahri"
                "key": info["key"],        # ex: "103" (int as str)
                "name": info["name"],      # ex: "Ahri"
            }
            self._champion_map[info["key"]] = entry
            self._champion_by_name[champ_id.lower()] = entry
            self._champion_by_name[info["name"].lower()] = entry

    def get_champion_data(self, name: str) -> dict | None:
        self._load_champion_map()
        return self._champion_by_name.get(name.lower())

    def get_all_champions(self) -> list[dict]:
        self._load_champion_map()
        return sorted(self._champion_map.values(), key=lambda c: c["name"])

    @lru_cache(maxsize=1)
    def _get_items_data(self) -> dict:
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch}/data/fr_FR/item.json"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    def get_item_info(self, item_id: int) -> dict:
        items = self._get_items_data()
        key = str(item_id)
        if key not in items:
            return {"id": item_id, "name": "Inconnu", "imageUrl": None}
        item = items[key]
        return {
            "id": item_id,
            "name": item["name"],
            "imageUrl": f"https://ddragon.leagueoflegends.com/cdn/{self.patch}/img/item/{item_id}.png",
            "description": item.get("plaintext", ""),
            "gold": item.get("gold", {}).get("total", 0),
        }
    
    @lru_cache(maxsize=1)
    def get_runes_data(self) -> list:
        url = f"https://ddragon.leagueoflegends.com/cdn/{self.patch}/data/fr_FR/runesReforged.json"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Ladder (Challenger → GrandMaster → Master)
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {"X-Riot-Token": self.api_key}

    def _platform_url(self, region: str) -> str:
        return f"https://{region}.api.riotgames.com"

    def _cluster_url(self, region: str) -> str:
        cluster = REGIONAL_ROUTING.get(region, "europe")
        return f"https://{cluster}.api.riotgames.com"

    def _get_ladder_entries(self, region: str, queue_type: str) -> list[dict]:
        """Récupère les entrées Challenger, puis GrandMaster si pas assez."""
        base = self._platform_url(region)
        entries = []
        for league in ("challengerleagues", "grandmasterleagues", "masterleagues"):
            league_name = league.replace("leagues", "")
            url = f"{base}/lol/league/v4/{league}/by-queue/{queue_type}"
            r = requests.get(url, headers=self._headers(), timeout=10)
            player = r.json().get("entries", [])
            for entry in player:
                entry["tier"] = league_name
            entries.extend(player)
        return entries

    def _get_summoner_name(self, region: str, summoner_puuid: str) -> str | None:
        url = f"{self._cluster_url(region)}/riot/account/v1/accounts/by-puuid/{summoner_puuid}"
        r = requests.get(url, headers=self._headers(), timeout=10)
        print(f"Status: {r.status_code} - Réponse: {r.text[:200]}")
        if r.status_code != 200:
            print(f"Summoner name error: {r.status_code} - {r.text}")
            return None
        data = r.json()
        game_name = data.get("gameName", "")
        tag_line = data.get("tagLine", "")
        print(f"Data: {data}")
        return f"{game_name}#{tag_line}" if game_name else "Inconnu"

    def _get_champion_mastery_cached(self, region: str, puuid: str, champion_id: str) -> int:
        cache = self._load_cache()
        cache_key = f"{region}:{puuid}:{champion_id}"
        
        # Vérifier si la valeur est en cache et encore valide
        if cache_key in cache:
            entry = cache[cache_key]
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
                return entry["mastery"]
        
        # Sinon appel API + mise en cache
        time.sleep(0.05)  # respect du quota 20 req/s
        mastery = self._get_champion_mastery_score(region, puuid, champion_id)
        cache[cache_key] = {
            "mastery": mastery,
            "cached_at": datetime.now().isoformat()
        }
        self._save_cache(cache)
        return mastery

    def _get_champion_mastery_score(self, region: str, puuid: str, champion_id: str) -> int:
        url = f"{self._platform_url(region)}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}"
        r = requests.get(url, headers=self._headers(), timeout=10)
        if r.status_code != 200:
            return 0
        return r.json().get("championPoints", 0)

    def get_top_players_for_champion(self, champion_id, region, queue, top_n=3, progress_callback=None):
        queue_type = QUEUE_TYPE_PARAM[queue]
        entries = self._get_ladder_entries(region, queue_type)
        total = len(entries)

        scored_players = []
        for i, entry in enumerate(entries):
            puuid = entry.get("puuid")
            if not puuid:
                continue

            mastery = self._get_champion_mastery_cached(region, puuid, champion_id)
            if mastery < 500_000:
                if progress_callback:
                    progress_callback({
                        "step": "ladder",
                        "current": i + 1,
                        "total": total,
                        "mains_found": len(scored_players),
                        "message": f"Inspection du joueur {i+1}/{total}..."
                    })
                continue

            lp = entry.get("leaguePoints", 0)
            combined_score = lp * 0.2 + mastery * 0.8

            scored_players.append({
                "summonerName": self._get_summoner_name(region, puuid),
                "rank": entry.get('tier', 'I'),
                "lp": lp,
                "puuid": puuid,
                "masteryPoints": mastery,
                "score": combined_score,
            })

            if progress_callback:
                progress_callback({
                    "step": "ladder",
                    "current": i + 1,
                    "total": total,
                    "mains_found": len(scored_players),
                    "message": f"Main trouvé : {entry.get('summonerName', '?')} ({mastery:,} pts)"
                })

        scored_players.sort(key=lambda p: p["score"], reverse=True)
        return scored_players[:top_n]

    # ------------------------------------------------------------------
    # Matches
    # ------------------------------------------------------------------

    def get_recent_matches_for_player(
        self,
        puuid: str,
        champion_key: str,
        region: str,
        count: int = 20,
    ) -> list[dict]:
        """
        Récupère les `count` dernières parties du joueur sur ce champion
        et retourne la liste des objets participant (données de build).
        """
        cluster = self._cluster_url(region)
        queue_id = QUEUE_IDS.get("ranked_solo", 420)

        # Liste des match IDs
        url = f"{cluster}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"queue": queue_id, "count": count, "start": 0}
        r = requests.get(url, headers=self._headers(), params=params, timeout=10)
        if r.status_code != 200:
            return []

        match_ids = r.json()
        results = []
        for match_id in match_ids:
            match_data = self._get_match_detail(cluster, match_id, puuid, champion_key)
            if match_data:
                results.append(match_data)

        return results
    
    def _get_match_timeline(self, cluster_url: str, match_id: str, puuid: str, champion_key: str) -> list[int] | None:
        """Retourne la liste ordonnée des items complétés achetés pendant la partie."""
        url = f"{cluster_url}/lol/match/v5/matches/{match_id}/timeline"
        try:
            r = requests.get(url, headers=self._headers(), timeout=30)
            if r.status_code != 200:
                return None
            data = r.json()
        except Exception as e:
            print(f"Timeline parse error pour {match_id}: {e}")
            return None

        data = r.json()
        frames = data.get("info", {}).get("frames", [])

        # Trouver le participantId du joueur
        participant_id = None
        participants_list = data.get("metadata", {}).get("participants", [])
        if puuid in participants_list:
            participant_id = participants_list.index(puuid) + 1

        if not participant_id:
            return None


        # Items considérés comme "composants" à exclure (prix < 1000g environ)
        # On récupère uniquement les ITEM_PURCHASED qui sont des items complétés
        completed_items_data = self._get_items_data()
        completed_item_ids = {
            int(item_id)
            for item_id, item in completed_items_data.items()
            if item.get("gold", {}).get("total", 0) > 1600
            and item.get("gold", {}).get("purchasable", False)
            and not item.get("consumed", False)
            and "trinket" not in item.get("tags", [])
        }

        ordered_items = []
        seen = set()

        for frame in frames:
            for event in frame.get("events", []):
                if (
                    event.get("type") == "ITEM_PURCHASED"
                    and event.get("participantId") == participant_id
                ):
                    item_id = event.get("itemId")
                    if item_id in completed_item_ids and item_id not in seen:
                        ordered_items.append(item_id)
                        seen.add(item_id)

        return ordered_items if ordered_items else None

    def _get_match_detail(self, cluster_url, match_id, puuid, champion_key) -> dict | None:
        url = f"{cluster_url}/lol/match/v5/matches/{match_id}"
        r = requests.get(url, headers=self._headers(), timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()

        participants = data.get("info", {}).get("participants", [])
        participant = next(
            (p for p in participants
            if p.get("puuid") == puuid and str(p.get("championId")) == champion_key),
            None,
        )
        if not participant:
            return None

        # Récupérer l'ordre d'achat via la timeline
        ordered_items = self._get_match_timeline(cluster_url, match_id, puuid, champion_key)

        # Fallback sur le snapshot final si timeline indisponible
        if not ordered_items:
            ordered_items = [
                participant.get(f"item{i}", 0)
                for i in range(6)
                if participant.get(f"item{i}", 0) != 0
            ]

        perks = participant.get("perks", {})
        styles = perks.get("styles", []) if perks else []
        selected_perks = [
            sel.get("perk")
            for style in styles
            for sel in style.get("selections", [])
        ]

        return {
            "matchId": match_id,
            "win": participant.get("win", False),
            "kills": participant.get("kills", 0),
            "deaths": participant.get("deaths", 0),
            "assists": participant.get("assists", 0),
            "orderedItems": ordered_items,  # ← renommé pour clarté
            "summonerSpell1": participant.get("summoner1Id"),
            "summonerSpell2": participant.get("summoner2Id"),
            "primaryRuneStyle": styles[0].get("style") if styles else None,
            "secondaryRuneStyle": styles[1].get("style") if len(styles) > 1 else None,
            "selectedPerks": selected_perks,
            "kills": participant.get("kills", 0),
            "deaths": participant.get("deaths", 0),
            "assists": participant.get("assists", 0),
        }
