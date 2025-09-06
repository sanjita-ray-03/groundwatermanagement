from flask import Blueprint, jsonify
import pandas as pd
import numpy as np

bp = Blueprint("forecast", __name__, url_prefix="/api/forecast")

# Naive moving average
@bp.route("/naive", methods=["GET"])
def naive_forecast():
    data = np.random.rand(20) * 10
    forecast = np.mean(data[-5:])
    return jsonify({"method": "naive", "forecast": forecast})

# Prophet Forecast
@bp.route("/prophet", methods=["GET"])
def prophet_forecast():
    try:
        from prophet import Prophet
    except ImportError:
        return jsonify({"error": "Prophet not installed. Run pip install prophet"})
    
    dates = pd.date_range(start="2023-01-01", periods=50)
    values = np.random.rand(50) * 10
    df = pd.DataFrame({"ds": dates, "y": values})

    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=10)
    forecast = model.predict(future)

    return jsonify({"method": "prophet", "forecast": forecast[["ds","yhat"]].tail(10).to_dict(orient="records")})

# LSTM Forecast (placeholder)
@bp.route("/lstm", methods=["GET"])
def lstm_forecast():
    try:
        import tensorflow as tf
    except ImportError:
        return jsonify({"error": "TensorFlow not installed. Run pip install tensorflow"})
    
    return jsonify({"method": "lstm", "forecast": "LSTM model placeholder"})
