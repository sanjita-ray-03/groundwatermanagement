from flask import Flask, jsonify, request,render_template
from flask_cors import CORS
from recommendation import groundwater_recommendation

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()

    water_level = data.get("water_level", 20)
    rainfall = data.get("rainfall", 100)
    usage_rate = data.get("usage_rate", 150)

    result = groundwater_recommendation(water_level, rainfall, usage_rate)
    return jsonify(result)

