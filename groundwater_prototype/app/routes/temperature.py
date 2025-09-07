
import time
from datetime import date
import requests
BASE_URL = "https://indiawris.gov.in/Dataset/Temperature"
HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}
PAGE_SIZE = 1000
START_DATE="2000-11-01"
END_DATE=date.today().strftime("%Y-%m-%d")
def fetch_groundwater_data(state, district):
    """Fetch all groundwater level records for a given state & district from India-WRIS API"""
    page = 0
    all_data = []

    while True:
        params = {
            "stateName": state,
            "districtName": district,
            "agencyName": state,   
            "startdate": START_DATE,
            "enddate": END_DATE,
            "download": "true",
            "page": page,
            "size": PAGE_SIZE
        }

        try:
            # Use data instead of params
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
