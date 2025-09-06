from flask import Blueprint, jsonify

bp = Blueprint("stations", __name__, url_prefix="/api/stations")

@bp.route("/", methods=["GET"])
def get_stations():
    stations = [
        {"id": 1, "name": "Station A", "location": "District X"},
        {"id": 2, "name": "Station B", "location": "District Y"},
    ]
    return jsonify(stations)
