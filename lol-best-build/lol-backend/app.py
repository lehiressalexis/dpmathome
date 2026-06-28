"""
LoL Best Build API
Récupère les meilleurs joueurs d'un champion et calcule le build optimal
en agrégeant les données de leurs 20 dernières parties.
"""

from flask import Flask, jsonify, request
from riot_client import RiotClient
from build_aggregator import BuildAggregator
from routes.champions_route import build_champions_bp,all_champions_bp
app = Flask(__name__)
riot = RiotClient()
aggregator = BuildAggregator()

app.register_blueprint(build_champions_bp)
app.register_blueprint(all_champions_bp)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "patch": riot.patch})


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
