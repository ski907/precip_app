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


import warnings
# Suppress the GeoPandas warning
warnings.filterwarnings('ignore', 'GeoSeries.notna', UserWarning)

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

def extract_qpf_value(description):
    """Extract QPF value from HTML table in description"""
    try:
        # Find the QPF row in the HTML table
        qpf_start = description.find('<td>QPF</td>')
        if qpf_start == -1:
            return 0.0
        
        # Find the next <td> with the value
        value_start = description.find('<td>', qpf_start + 12)  # 12 = len('<td>QPF</td>')
        value_end = description.find('</td>', value_start)
        
        # Extract and clean the value
        qpf_value = description[value_start + 4:value_end].strip()
        return float(qpf_value)
    except:
        return 0.0

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

    #this worked for the old QPF KML format
    # field_name = 'Name'  # Adjust this based on your actual field name
    # gdf['color'] = gdf[field_name].astype(float).apply(get_color)
    # gdf['qpf'] = gdf[field_name].astype(float)  # Add QPF value to properties

    #updated in 2025

    gdf['qpf'] = gdf['Description'].apply(extract_qpf_value)
    gdf['color'] = gdf['qpf'].apply(get_color)

    geojson = json.loads(gdf.to_json())
    for feature, color in zip(geojson['features'], gdf['color']):
        feature['properties']['style'] = {'color': color, 'weight': 0, 'opacity': 1}
        #feature['properties']['qpf'] = feature['properties'][field_name]

    return geojson

def calculate_average_qpf_from_gdf_OLD(gdf, polygon, cell_size=0.02):
    """Calculate maximum QPF using pre-loaded GeoDataFrame"""
    # Clip the QPF data to the polygon
    clipped = gpd.clip(gdf, polygon)
    
    if clipped.empty:
        return 0.0
    
    # Return the maximum QPF value (handles overlapping layers)
    max_qpf = clipped['QPF'].max()
    return max_qpf

def calculate_average_qpf_from_gdf(gdf, polygon, cell_size=0.02):
    """Calculate maximum QPF using pre-loaded GeoDataFrame - assumes geometries are already valid"""
    try:
        # Fix polygon if invalid (this is the only geometry we need to check each time)
        if not polygon.is_valid:
            logging.debug("Fixing invalid polygon geometry")
            polygon = polygon.buffer(0)
        
        # Perform the clip operation
        clipped = gpd.clip(gdf, polygon)
        
        if clipped.empty:
            logging.debug("No geometries after clipping - polygon may not intersect with data")
            return 0.0
        
        # Return the maximum QPF value (handles overlapping layers)
        max_qpf = clipped['QPF'].max()
        return max_qpf if not pd.isna(max_qpf) else 0.0
        
    except Exception as e:
        logging.error(f"Error in calculate_average_qpf_from_gdf: {e}")
        return 0.0
    
@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/watershed_data')
# def watershed_data():
#     # Load all KML files once at the start
#     forecast_data = {}
#     for day in ["Day1", "Day2", "Day3"]:
#         kml_file = f"forecast_{day}/doc.kml"
#         if os.path.exists(kml_file):
#             gdf = gpd.read_file(kml_file, driver='KML')
#             gdf = gdf.to_crs(epsg=4326)
#             gdf['QPF'] = gdf['Description'].apply(extract_qpf_value)
#             forecast_data[day] = gdf
#         else:
#             logging.error(f"KML file not found: {kml_file}")
#             forecast_data[day] = None
    
#     # Process all polygons against pre-loaded data
#     results = {}
#     for installation_name, shapefiles in shapefiles_cache.items():
#         installation_results = {}
#         for shapefile_name, polygons in shapefiles.items():
#             location_results = []
#             for item in polygons:
#                 polygon = shape(item['polygon'])
                
#                 # Calculate QPF for all days using pre-loaded data
#                 qpf_values = {}
#                 for day, gdf in forecast_data.items():
#                     if gdf is not None:
#                         qpf_values[f'avg_qpf_{day.lower()}'] = calculate_average_qpf_from_gdf(gdf, polygon)
#                     else:
#                         qpf_values[f'avg_qpf_{day.lower()}'] = 0.0
                
#                 location_data = {
#                     'polygon': mapping(polygon),
#                     'name': item['properties'].get('name', 'Unknown'),
#                     'installation': installation_name,
#                     'shapefile': shapefile_name,
#                     **qpf_values
#                 }
#                 location_results.append(location_data)
#             installation_results[shapefile_name] = location_results
#         results[installation_name] = installation_results
    
#     return jsonify(results)

@app.route('/watershed_data')
def watershed_data():
    # Load all KML files once at the start and fix geometries ONCE
    forecast_data = {}
    for day in ["Day1", "Day2", "Day3"]:
        kml_file = f"forecast_{day}/doc.kml"
        if os.path.exists(kml_file):
            try:
                gdf = gpd.read_file(kml_file, driver='KML')
                gdf = gdf.to_crs(epsg=4326)
                gdf['QPF'] = gdf['Description'].apply(extract_qpf_value)
                
                # Fix invalid geometries ONCE when loading
                invalid_mask = ~gdf.geometry.is_valid
                if invalid_mask.any():
                    logging.debug(f"Fixing {invalid_mask.sum()} invalid geometries in {day} forecast data")
                    gdf.loc[invalid_mask, 'geometry'] = gdf.loc[invalid_mask, 'geometry'].buffer(0)
                
                # Remove null and empty geometries
                gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty]
                
                forecast_data[day] = gdf
                logging.debug(f"Loaded {len(gdf)} valid geometries for {day}")
            except Exception as e:
                logging.error(f"Error loading KML file {kml_file}: {e}")
                forecast_data[day] = None
        else:
            logging.error(f"KML file not found: {kml_file}")
            forecast_data[day] = None
    
    # Process all polygons against pre-loaded data
    results = {}
    total_processed = 0
    errors = 0
    
    for installation_name, shapefiles in shapefiles_cache.items():
        installation_results = {}
        for shapefile_name, polygons in shapefiles.items():
            location_results = []
            for item in polygons:
                try:
                    polygon = shape(item['polygon'])
                    
                    # Calculate QPF for all days using pre-loaded data
                    qpf_values = {}
                    for day, gdf in forecast_data.items():
                        if gdf is not None and not gdf.empty:
                            qpf_values[f'avg_qpf_{day.lower()}'] = calculate_average_qpf_from_gdf(gdf, polygon)
                        else:
                            qpf_values[f'avg_qpf_{day.lower()}'] = 0.0
                    
                    location_data = {
                        'polygon': mapping(polygon),
                        'name': item['properties'].get('name', 'Unknown'),
                        'installation': installation_name,
                        'shapefile': shapefile_name,
                        **qpf_values
                    }
                    location_results.append(location_data)
                    total_processed += 1
                    
                except Exception as e:
                    logging.error(f"Error processing polygon in {installation_name}/{shapefile_name}: {e}")
                    errors += 1
                    continue
                    
            installation_results[shapefile_name] = location_results
        results[installation_name] = installation_results
    
    logging.info(f"Processed {total_processed} polygons with {errors} errors")
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
