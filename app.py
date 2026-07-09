"""
Validatore di Codici Fiscali Italiani — Server Flask

API:
  POST /api/valida
    Body JSON: {"cf": "RSSMRA80A01H501X"}
    Risposta: validazione, decodifica, comune di nascita
"""

import os
from flask import Flask, request, jsonify, send_from_directory

from cf_engine import valida_cf, decodifica_cf
from comuni_data import COMUNI

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/valida", methods=["POST"])
def api_valida():
    data = request.get_json(silent=True)
    if not data or "cf" not in data:
        return jsonify({"errore": "Richiesta non valida: campo 'cf' mancante."}), 400

    cf = data["cf"].strip()

    if not cf:
        return jsonify({"errore": "Inserisci un codice fiscale."}), 400

    valido, errori, cf_norm = valida_cf(cf)

    if not valido:
        return jsonify({
            "valido": False,
            "errori": errori,
        }), 200  # 200 anche per CF invalidi — è una risposta di business

    # Decodifica
    dati = decodifica_cf(cf_norm)

    # Cerca il comune
    codice_catastale = dati["codice_catastale"]
    comune = COMUNI.get(codice_catastale)

    return jsonify({
        "valido": True,
        "dati": dati,
        "comune": comune,
        "comune_trovato": comune is not None,
    })


@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4599))
    app.run(host="0.0.0.0", port=port, debug=False)
