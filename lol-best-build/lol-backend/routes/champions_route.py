
from flask import Blueprint, jsonify, request, Response, stream_with_context
from riot_client import RiotClient
from build_aggregator import BuildAggregator
import json

riot = RiotClient()
aggregator = BuildAggregator()


build_champions_bp = Blueprint("best build pour un champion", __name__)
@build_champions_bp.route("/api/champion/<champion_name>/best-build", methods=["GET"])
def get_best_build(champion_name):
    """
    Retourne le meilleur build pour un champion donné,
    basé sur les 3 meilleurs joueurs en ladder.

    Query params:
      - region: (optionnel) euw1, na1, kr... (défaut: euw1)
      - queue: (optionnel) ranked_solo, ranked_flex (défaut: ranked_solo)
    """
    region = request.args.get("region", "euw1").lower()
    queue = request.args.get("queue", "ranked_solo").lower()

    champion_data = riot.get_champion_data(champion_name)
    if not champion_data:
        return jsonify({"error": f"Champion '{champion_name}' introuvable."}), 404

    champion_id = champion_data["id"]
    champion_key = champion_data["key"]

    def generate():
        print("=== generate() démarré ===")
        def send(data):
            yield f"data: {json.dumps(data)}\n\n"

        # Étape 1 : ladder
        progress_events = []
        def on_progress(p):
            progress_events.append(p)

        # Envoyer le début
        yield f"data: {json.dumps({'type': 'progress', 'step': 'start', 'message': 'Récupération du ladder...'})}\n\n"

        top_players = []
        all_matches = []
        players_info = []

        def progress_callback(p):
            pass  # sera remplacé ci-dessous

        # Wrapper pour streamer la progression
        import queue as q
        event_queue = q.Queue()

        def real_callback(p):
            event_queue.put(p)

        import threading

        result_holder = {}

        def run_analysis():
            print("=== run_analysis() démarré ===")
            try:
                players = riot.get_top_players_for_champion(
                    champion_key, region, queue, top_n=3,
                    progress_callback=real_callback
                )
                print(f"=== Joueurs trouvés : {len(players)} ===")
                result_holder["players"] = players
            except Exception as e:
                result_holder["error"] = str(e)
            finally:
                event_queue.put(None)  # signal de fin

        thread = threading.Thread(target=run_analysis)
        thread.start()

        # Streamer les événements pendant l'analyse
        while True:
            try:
                event = event_queue.get(timeout=30)
                if event is None:
                    break
                yield f"data: {json.dumps({'type': 'progress', **event})}\n\n"
            except q.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        if "error" in result_holder:
            yield f"data: {json.dumps({'type': 'error', 'message': result_holder['error']})}\n\n"
            return

        top_players = result_holder["players"]
        if not top_players:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Aucun main trouvé pour ce champion.'})}\n\n"
            return

        # Étape 2 : matches
        for i, player in enumerate(top_players):
            summoner_name = player.get("summonerName", "Inconnu")
            yield f"data: {json.dumps({'type': 'progress', 'step': 'matches', 'message': f'Analyse des parties de {summoner_name} ({i+1}/3)...'})}\n\n"
            matches = riot.get_recent_matches_for_player(
                puuid=player["puuid"],
                champion_key=champion_key,
                region=region,
                count=20,
            )
            all_matches.extend(matches)
            players_info.append({
                "summonerName": summoner_name,
                "rank": player["rank"],
                "lp": player["lp"],
                "masteryPoints": player["masteryPoints"],
                "matchesAnalyzed": len(matches),
            })

        # Étape 3 : agrégation
        yield f"data: {json.dumps({'type': 'progress', 'step': 'aggregation', 'message': 'Calcul du build optimal...'})}\n\n"

        best_build = aggregator.compute_best_build(all_matches, champion_key)
        runes_data = riot.get_runes_data()

        # Résultat final
        result = {
            "type": "result",
            "champion": {
                "name": champion_data["name"],
                "id": champion_id,
                "imageUrl": f"https://ddragon.leagueoflegends.com/cdn/{riot.patch}/img/champion/{champion_id}.png",
            },
            "runesData": runes_data,
            "region": region,
            "queue": queue,
            "topPlayers": players_info,
            "totalMatchesAnalyzed": len(all_matches),
            "bestBuild": best_build,
        }
        yield f"data: {json.dumps(result)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

all_champions_bp = Blueprint("requete tous les champions", __name__)
@all_champions_bp.route("/api/champions", methods=["GET"])
def list_champions():
    """Retourne la liste de tous les champions (nom + id) pour l'autocomplétion."""
    champions = riot.get_all_champions()
    return jsonify({"champions": champions})
