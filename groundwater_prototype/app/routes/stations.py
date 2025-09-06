import requests
import os
import time
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Example state-district mapping; expand for all Indian states
states_districts = {
    "West Bengal": ["Kolkata", "Howrah", "Darjeeling"],
    "Odisha": ["Baleshwar", "Cuttack", "Khordha"],
}

BASE_URL = "https://indiawris.gov.in/Dataset/Ground Water Level"
HEADERS = {"accept": "application/json"}
PAGE_SIZE = 1000
START_DATE = "2000-11-01"
END_DATE = "2024-11-01"

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    database="groundwater_db",
    user="your_username",
    password="your_password"
)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS groundwater_readings (
    state_name VARCHAR(50),
    district_name VARCHAR(50),
    station_id VARCHAR(50),
    reading_date DATE,
    groundwater_level FLOAT,
    agency_name VARCHAR(50)
);
""")
conn.commit()


def fetch_groundwater_data(state, district):
    page = 0
    all_data = []

    while True:
        params = {
            "stateName": state,
            "districtName": district,
            "agencyName": "CGWB",
            "startdate": START_DATE,
            "enddate": END_DATE,
            "download": "true",
            "page": page,
            "size": PAGE_SIZE
        }

        try:
            response = requests.post(BASE_URL, params=params, headers=HEADERS)
            response.raise_for_status()
            response_data = response.json()

            if isinstance(response_data, dict):
                data = response_data.get("data", [])
            elif isinstance(response_data, list):
                data = response_data
            else:
                data = []

            if not data:
                break

            all_data.extend(data)
            page += 1
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"Request failed for {district}, {state}: {e}")
            break

    return all_data


for state, districts in states_districts.items():
    os.makedirs(state, exist_ok=True)  # folder for state

    for district in districts:
        print(f"Fetching data for {district}, {state}")
        data = fetch_groundwater_data(state, district)

        if data:
            # Convert to DataFrame
            df = pd.json_normalize(data)

            # Save CSV
            csv_path = os.path.join(state, f"{district}.csv")
            df.to_csv(csv_path, index=False)
            print(f"Saved {len(df)} records to {csv_path}")

            # Insert into PostgreSQL
            # Ensure columns exist in your API response
            records = []
            for row in df.itertuples(index=False):
                records.append((
                    getattr(row, 'stateName', state),
                    getattr(row, 'districtName', district),
                    getattr(row, 'stationID', None),
                    getattr(row, 'date', None),
                    getattr(row, 'groundWaterLevel', None),
                    getattr(row, 'agencyName', 'CGWB')
                ))

            if records:
                execute_values(
                    cursor,
                    """
                    INSERT INTO groundwater_readings
                    (state_name, district_name, station_id, reading_date, groundwater_level, agency_name)
                    VALUES %s
                    """,
                    records
                )
                conn.commit()
                print(f"Inserted {len(records)} records into PostgreSQL")
        else:
            print(f"No data found for {district}, {state}")

cursor.close()
conn.close()
