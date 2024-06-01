import h3
import requests
import folium
from collections import defaultdict
import numpy as np
import streamlit as st
from streamlit_folium import st_folium

# Dictionary of cities with their bounding box coordinates
cities = {
    "San Francisco": [37.7045, -122.527, 37.8122, -122.3493],
    "New York": [40.4774, -74.2591, 40.9176, -73.7004],
    "Los Angeles": [33.7036, -118.6682, 34.3373, -118.1553],
    "Chicago": [41.6445, -87.9401, 42.0230, -87.5237],
    "Houston": [29.5223, -95.7975, 30.1547, -95.0148],
    "Phoenix": [33.2903, -112.3241, 33.7490, -111.9286],
    "Philadelphia": [39.8670, -75.2803, 40.1377, -74.9558],
    "San Antonio": [29.2072, -98.7364, 29.6632, -98.2955],
    "San Diego": [32.5343, -117.2898, 33.1140, -116.9583],
    "Dallas": [32.6200, -96.9982, 32.9957, -96.4635],
}

# Streamlit UI for user inputs
st.title("Hexagon Amenity Type Visualizer")
city = st.selectbox("Select a city", list(cities.keys()))
n = st.slider("Minimum number of unique amenity types to highlight hexagons", 1, 50, 3)

# Get the bounding box for the selected city
bbox = cities[city]

# Define H3 resolution
resolution = 7

# Print the bounding box coordinates for debugging
print(f"Bounding box coordinates: {bbox}")

# Generate a grid of points within the bounding box
lat_min, lon_min, lat_max, lon_max = bbox
lat_grid = np.linspace(lat_min, lat_max, 100)
lon_grid = np.linspace(lon_min, lon_max, 100)

# Convert grid points to H3 hexagons
hexagons = set()
for lat in lat_grid:
    for lon in lon_grid:
        hex_id = h3.geo_to_h3(lat, lon, resolution)
        hexagons.add(hex_id)

# Debug: Print the number of hexagons generated
print(f"Number of hexagons generated: {len(hexagons)}")

# Query OSM Turbo for amenity data within the bounding box
overpass_url = "http://overpass-api.de/api/interpreter"
query = f"""
[out:json];
(
  node["amenity"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
);
out geom;
"""

response = requests.get(overpass_url, params={'data': query})

# Check if the response is valid and contains JSON data
if response.status_code == 200 and 'json' in response.headers.get('Content-Type', ''):
    data = response.json()
    # Debug: Print the number of elements retrieved
    print(f"Number of elements retrieved: {len(data['elements'])}")
else:
    st.error("Error: Unable to retrieve data from the Overpass API.")
    st.error(f"Status Code: {response.status_code}")
    st.error(f"Response Content: {response.text}")
    data = {'elements': []}  # Define data to avoid NameError

# Count the variety of amenity types within each hexagon
amenity_counts = defaultdict(lambda: defaultdict(int))
for element in data['elements']:
    hex_id = h3.geo_to_h3(element['lat'], element['lon'], resolution)
    if hex_id in hexagons:
        amenity_type = element['tags'].get('amenity')
        if amenity_type:
            amenity_counts[hex_id][amenity_type] += 1

# Debug: Print the amenity counts for each hexagon
for hex_id, counts in amenity_counts.items():
    print(f"Hex ID: {hex_id}, Amenity counts: {counts}")

# Visualize the results on a map
map_center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
map_zoom = 12

m = folium.Map(location=map_center, zoom_start=map_zoom)

for hex_id in hexagons:
    try:
        boundary = h3.h3_to_geo_boundary(hex_id, geo_json=True)
        geojson_boundary = {
            "type": "Polygon",
            "coordinates": [boundary]
        }
        unique_amenity_types = len(amenity_counts[hex_id])

        # Prepare the tooltip content
        tooltip_content = '<br>'.join([f"{amenity}: {count}" for amenity, count in amenity_counts[hex_id].items()])

        # Add the GeoJSON layer with the tooltip
        folium.GeoJson(
            geojson_boundary,
            style_function=lambda x, unique_amenity_types=unique_amenity_types: {
                'fillColor': 'red' if unique_amenity_types >= n else 'blue',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7 if unique_amenity_types >= n else 0.1
            },
            tooltip=folium.Tooltip(tooltip_content, sticky=True)
        ).add_to(m)
    except ValueError as e:
        st.error(f"Error rendering hexagon {hex_id}: {e}")

# Display the map in Streamlit with increased size
st_folium(m, width=1200, height=800)
