# recommendation.py

def groundwater_recommendation(water_level, rainfall, usage_rate):
    """
    Simple rule-based groundwater recommendation system.
    Args:
        water_level (float): current groundwater level (meters below ground)
        rainfall (float): recent rainfall (mm/month)
        usage_rate (float): groundwater usage rate (liters/day per capita)
    Returns:
        dict: recommendations
    """
    recommendations = []

    # Rule 1: Critical water level
    if water_level > 30:  # deeper water → scarcity
        recommendations.append("⚠️ Groundwater levels are critical. Limit pumping and prioritize recharge.")
    elif 15 < water_level <= 30:
        recommendations.append("Moderate levels. Promote water-saving irrigation and regulated usage.")
    else:
        recommendations.append("Good groundwater availability. Still use sustainable practices.")

    # Rule 2: Rainfall-based recharge advice
    if rainfall < 50:
        recommendations.append("Low rainfall. Implement rainwater harvesting and artificial recharge.")
    elif 50 <= rainfall < 150:
        recommendations.append("Moderate rainfall. Encourage check-dams and recharge pits.")
    else:
        recommendations.append("High rainfall. Capture surplus water for storage and recharge.")

    # Rule 3: Usage intensity
    if usage_rate > 200:
        recommendations.append("High usage detected. Encourage crop shifting to low water-demand crops.")
    elif 100 < usage_rate <= 200:
        recommendations.append("Moderate usage. Promote drip/sprinkler irrigation.")
    else:
        recommendations.append("Sustainable usage. Maintain current practices.")

    return {"status": "success", "recommendations": recommendations}
