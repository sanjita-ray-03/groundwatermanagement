from flask import Blueprint, jsonify, request

bp = Blueprint("faq", __name__, url_prefix="/api/faq")

faq_data = [
    {"q": "How to save water?", "a": "Use drip irrigation and rainwater harvesting."},
    {"q": "What is groundwater recharge?", "a": "Process where water moves downward to replenish aquifers."},
]

# Simple FAQ (list all)
@bp.route("/", methods=["GET"])
def get_faq():
    return jsonify(faq_data)

# FAQ Ask - supports GET and POST
@bp.route("/ask", methods=["GET", "POST"])
def ask_faq():
    if request.method == "POST":
        query = request.json.get("query", "").lower()
    else:  # GET
        query = request.args.get("q", "").lower()

    if not query:
        return jsonify({"a": "No question provided."}), 400

    for faq in faq_data:
        if query in faq["q"].lower():
            return jsonify(faq)
    return jsonify({"a": "Sorry, I don’t know the answer."})

# BERT Semantic Search
@bp.route("/bert", methods=["POST"])
def faq_bert():
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        return jsonify({"error": "sentence-transformers not installed. Run pip install sentence-transformers"})

    model = SentenceTransformer("all-MiniLM-L6-v2")
    query = request.json.get("query", "")
    corpus = [faq["q"] for faq in faq_data]

    corpus_emb = model.encode(corpus, convert_to_tensor=True)
    query_emb = model.encode(query, convert_to_tensor=True)

    scores = util.pytorch_cos_sim(query_emb, corpus_emb)[0]
    best_idx = int(scores.argmax())

    return jsonify(faq_data[best_idx])
