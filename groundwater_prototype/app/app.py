from flask import Flask, jsonify, request
from flask_cors import CORS

# Import endpoints
from routes import stations, readings, forecast, recommend, faq

app = Flask(__name__)
CORS(app)

# Register routes
app.register_blueprint(stations.bp)
app.register_blueprint(readings.bp)
app.register_blueprint(forecast.bp)
app.register_blueprint(recommend.bp)
app.register_blueprint(faq.bp)

@app.route("/")
def home():
    return jsonify({"message": "Groundwater Prototype API Running"})

@app.route('/api/forecast')
def forecast():
    station_id = request.args.get("station_id")
    horizon = int(request.args.get("horizon", 7))

    # Mock: generate a simple decreasing water level
    forecast_data = []
    base_level = 10.0  # starting level
    for day in range(horizon):
        forecast_data.append({
            "day": day + 1,
            "predicted_level": round(base_level - 0.1 * day, 2)
        })

    return jsonify({
        "station_id": station_id,
        "horizon": horizon,
        "forecast": forecast_data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
