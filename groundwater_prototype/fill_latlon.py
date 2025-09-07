import json
from geopy.geocoders import Nominatim
from time import sleep
from tqdm import tqdm

# Load your JSON with null lat/lon
input_file = "indian_states_cities_with_latlon.json"
output_file = "indian_states_cities_with_latlon_completed.json"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

geolocator = Nominatim(user_agent="india-geocoder")

for state, cities in data.items():
    for city in tqdm(cities, desc=f"Processing {state}"):
        if city["lat"] is None or city["lon"] is None:
            query = f"{city['name']}, {state}, India"
            try:
                location = geolocator.geocode(query, timeout=10)
                if location:
                    city["lat"] = location.latitude
                    city["lon"] = location.longitude
                else:
                    print(f"⚠️ Could not find {query}")
                sleep(1)  # avoid hitting rate limits
            except Exception as e:
                print(f"Error for {query}: {e}")

# Save updated JSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Completed file saved as {output_file}")
