from flask import Blueprint, jsonify
import numpy as np

bp = Blueprint("recommend", __name__, url_prefix="/api/recommend")

# Rule-based
@bp.route("/", methods=["GET"])
def recommend_rules():
    return jsonify({
        "recommendations": [
            "Use drip irrigation",
            "Harvest rainwater",
            "Monitor groundwater usage"
        ]
    })

# KMeans ML
@bp.route("/ml", methods=["GET"])
def recommend_ml():
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        return jsonify({"error": "scikit-learn not installed. Run pip install scikit-learn"})
    
    X = np.random.rand(10, 2)
    kmeans = KMeans(n_clusters=2, random_state=0).fit(X)
    labels = kmeans.labels_.tolist()

    return jsonify({"method": "kmeans", "labels": labels})
