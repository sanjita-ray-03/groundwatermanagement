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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
