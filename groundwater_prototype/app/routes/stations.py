import requests
import time
from flask import Blueprint, jsonify
import json

bp = Blueprint("stations", __name__, url_prefix="/api/stations")

# Load state-district mapping
with open('app/data/state.json', 'r') as file:
    states_districts = json.load(file)

# India-WRIS API endpoint
BASE_URL = "https://indiawris.gov.in/Dataset/Ground Water Level"
HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}
PAGE_SIZE = 1000
START_DATE = "2000-11-01"
END_DATE = "2024-11-01"


def fetch_groundwater_data(state, district):
    """Fetch all groundwater level records for a given state & district from India-WRIS API"""
    page = 0
    all_data = []

    while True:
        params = {
            "stateName": state,
            "districtName": district,
            "agencyName": "CGWB",   # Central Ground Water Board
            "startdate": START_DATE,
            "enddate": END_DATE,
            "download": "true",
            "page": page,
            "size": PAGE_SIZE
        }

        try:
            # ✅ Use data instead of params
            response = requests.post(BASE_URL, data=params, headers=HEADERS, timeout=30)
            response.raise_for_status()

            response_data = response.json()

            # Extract data safely
            if isinstance(response_data, dict):
                data = response_data.get("data", [])
            elif isinstance(response_data, list):
                data = response_data
            else:
                data = []

            # Stop if no more records
            if not data:
                break

            all_data.extend(data)
            print(f"{district}, {state} → Page {page} fetched {len(data)} records")
            page += 1
            time.sleep(1)  # avoid overloading server

        except requests.exceptions.RequestException as e:
            print(f"Request failed for {district}, {state}: {e}")
            break
        except ValueError as e:
            print(f"Invalid JSON for {district}, {state}: {e}")
            break

    print(f"{district}, {state} → Total collected: {len(all_data)}")
    return all_data


@bp.route("/", methods=["GET"])
def get_all_stations():
    """Fetch groundwater data for all states & districts in states_districts"""
    results = {}

    for state, districts in states_districts.items():
        state_data = []
        for district in districts:
            print(f"Fetching data for {district}, {state}...")
            data = fetch_groundwater_data(state, district)
            state_data.extend(data)

        results[state] = state_data
        print(f"✅ {state}: {len(state_data)} records added")

    return jsonify(results)
