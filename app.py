from flask import Flask, jsonify, render_template
import requests
import geopandas as gpd
from shapely.geometry import shape, mapping, box
import zipfile
import os
import logging
import json
import pandas as pd
import numpy as np

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load cached shapefiles' geometries and metadata
with open('shapefiles_cache_all.json', 'r') as f:
    shapefiles_cache = json.load(f)

forecast_urls = {
    "Day1": "https://www.wpc.ncep.noaa.gov/kml/qpf/QPF24hr_Day1_latest.kmz",
    "Day2": "https://www.wpc.ncep.noaa.gov/kml/qpf/QPF24hr_Day2_latest.kmz",
    "Day3": "https://www.wpc.ncep.noaa.gov/kml/qpf/QPF24hr_Day3_latest.kmz"
}

def download_and_extract_kmz(url, day):
    logging.debug(f"Downloading KMZ file for {day}...")
    response = requests.get(url)
    kmz_path = f"forecast_{day}.kmz"
    with open(kmz_path, "wb") as file:
        file.write(response.content)
    logging.debug(f"KMZ file for {day} downloaded. Extracting...")
    with zipfile.ZipFile(kmz_path, "r") as zip_ref:
        zip_ref.extractall(f"forecast_{day}")
    os.remove(kmz_path)
    logging.debug(f"KMZ file for {day} extracted.")

def get_forecast_geojson(day):
    kml_file = f"forecast_{day}/doc.kml"
    if not os.path.exists(kml_file):
        logging.error(f"KML file not found at {kml_file}.")
        return None
    
    gdf = gpd.read_file(kml_file, driver='KML')
    gdf = gdf.to_crs(epsg=4326)  # Ensure the CRS is WGS84

    def get_color(value):
        if value > 20:
            return '#FFC0CB'  # Pink
        elif value > 15:
            return '#FFFF00'  # Yellow
        elif value > 10:
            return '#DAA520'  # Goldenrod
        elif value > 7:
            return '#D2B48C'  # Light Brown
        elif value > 5:
            return '#FFA500'  # Orange
        elif value > 4:
            return '#FF0000'  # Red
        elif value > 3:
            return '#8B0000'  # Dark Red
        elif value > 2.5:
            return '#800000'  # Mahogany
        elif value > 2:
            return '#4B0082'  # Dark Purple
        elif value > 1.75:
            return '#800080'  # Purple
        elif value > 1.5:
            return '#E6E6FA'  # Lavender
        elif value > 1.25:
            return '#00FFFF'  # Cyan
        elif value > 1:
            return '#008080'  # Teal
        elif value > 0.75:
            return '#0000FF'  # Blue
        elif value > 0.5:
            return '#006400'  # Dark Green
        elif value > 0.25:
            return '#228B22'  # Forest Green
        elif value > 0.1:
            return '#00FF00'  # Green
        else:
            return '#00FF7F'  # Lime (or no color)


    field_name = 'Name'  # Adjust this based on your actual field name
    gdf['color'] = gdf[field_name].astype(float).apply(get_color)
    gdf['qpf'] = gdf[field_name].astype(float)  # Add QPF value to properties

    geojson = json.loads(gdf.to_json())
    for feature, color in zip(geojson['features'], gdf['color']):
        feature['properties']['style'] = {'color': color, 'weight': 0, 'opacity': 1}
        feature['properties']['qpf'] = feature['properties'][field_name]

    return geojson

def calculate_average_qpf(kml_file, polygon, cell_size=0.01):
    #logging.debug(f"Calculating average QPF from {kml_file}...")

    # Load and process KML file
    gdf = gpd.read_file(kml_file, driver='KML')
    gdf = gdf.to_crs(epsg=4326)  # Ensure the CRS is WGS84

    # Extract QPF values and geometries
    gdf['QPF'] = gdf['Name'].astype(float)  # Ensure QPF values are float

    # Clip the QPF data to the preset polygon
    clipped = gpd.clip(gdf, polygon)

    # Create a grid covering the entire polygon
    bounds = polygon.bounds
    x_min, y_min, x_max, y_max = bounds
    x_coords = np.arange(x_min, x_max, cell_size)
    y_coords = np.arange(y_min, y_max, cell_size)

    cells = []
    for x in x_coords:
        for y in y_coords:
            cells.append(box(x, y, x + cell_size, y + cell_size))

    grid = gpd.GeoDataFrame({'geometry': cells}, crs="EPSG:4326")
    grid = grid[grid.intersects(polygon)]

    # Initialize QPF values in the grid to 0
    grid['QPF'] = 0

    # Perform spatial join between the clipped data and the grid, taking the max QPF value
    for index, row in clipped.iterrows():
        intersected_cells = grid[grid.intersects(row.geometry)]
        grid.loc[intersected_cells.index, 'QPF'] = np.maximum(
            grid.loc[intersected_cells.index, 'QPF'], row['QPF'])

    # Calculate the average QPF
    avg_qpf = grid['QPF'].mean()
    #logging.debug(f"Average QPF calculated: {avg_qpf}")

    return avg_qpf

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/watershed_data')
def watershed_data():
    results = {}
    for installation_name, shapefiles in shapefiles_cache.items():
        installation_results = {}
        for shapefile_name, polygons in shapefiles.items():
            location_results = []
            for item in polygons:
                polygon = shape(item['polygon'])
                avg_qpf_day1 = calculate_average_qpf("forecast_Day1/doc.kml", polygon)
                avg_qpf_day2 = calculate_average_qpf("forecast_Day2/doc.kml", polygon)
                avg_qpf_day3 = calculate_average_qpf("forecast_Day3/doc.kml", polygon)
                location_data = {
                    'polygon': mapping(polygon),
                    'name': item['properties'].get('name', 'Unknown'),
                    'installation': installation_name,
                    'shapefile': shapefile_name,
                    'avg_qpf_day1': avg_qpf_day1,
                    'avg_qpf_day2': avg_qpf_day2,
                    'avg_qpf_day3': avg_qpf_day3
                }
                location_results.append(location_data)
            installation_results[shapefile_name] = location_results
        results[installation_name] = installation_results
    return jsonify(results)

@app.route('/geojsonQPF')
def geojsonQPF():
    all_forecast_data = {}
    for day, url in forecast_urls.items():
        download_and_extract_kmz(url, day)
        geojson = get_forecast_geojson(day)
        if geojson:
            all_forecast_data[day] = geojson
    return jsonify(all_forecast_data)

if __name__ == '__main__':
    app.run(debug=True)
