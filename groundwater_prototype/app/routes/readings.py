from flask import Blueprint, jsonify
import random
import time

bp = Blueprint("readings", __name__, url_prefix="/api/readings")

@bp.route("/", methods=["GET"])
def get_readings():
    readings = []
    for i in range(10):
        readings.append({
            "timestamp": time.time() - i*3600,
            "water_level": round(random.uniform(2.0, 5.0), 2),
            "pressure": round(random.uniform(1.0, 2.0), 2),
            "temperature": round(random.uniform(20, 30), 2)
        })
    return jsonify(readings)
