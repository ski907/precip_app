# Weather Forecast QPF Application

A Flask web application that downloads and processes NOAA Weather Prediction Center (WPC) Quantitative Precipitation Forecast (QPF) data and calculates average rainfall predictions for predefined watershed polygons.

## What it does

This application:
- Downloads 3-day precipitation forecast data (KMZ files) from NOAA WPC
- Processes the forecast data and converts it to GeoJSON format with color-coded precipitation levels
- Calculates average QPF values for predefined watershed/installation polygons
- Provides a web interface to visualize the forecast data and watershed calculations

## Prerequisites

- Python 3.7+
- Required Python packages (install via pip):
  ```bash
  pip install flask requests geopandas shapely pandas numpy
  ```

## Required Files

Before running the application, ensure you have:
- `shapefiles_cache_all.json` - Contains cached watershed/installation polygon data
- `templates/index.html` - HTML template for the web interface (create this file)

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install flask requests geopandas shapely pandas numpy
   ```
3. Ensure you have the required cache file (`shapefiles_cache_all.json`) in the project directory
4. Create a `templates` folder and add an `index.html` file for the web interface

## Usage

1. Run the Flask application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

## API Endpoints

- **`/`** - Main web interface
- **`/watershed_data`** - Returns JSON data with average QPF calculations for all cached watersheds/installations
- **`/geojsonQPF`** - Downloads latest forecast data and returns GeoJSON format with color-coded precipitation levels

## Forecast Data

The application uses NOAA WPC 24-hour QPF forecasts:
- Day 1: Current day forecast
- Day 2: Next day forecast  
- Day 3: Two days ahead forecast

Precipitation levels are color-coded from green (light rain) to pink (heavy rain > 20mm).

## Output

The watershed data endpoint provides:
- Polygon geometry for each watershed
- Installation and shapefile names
- 3-day average QPF predictions for each polygon area

## Notes

- Forecast data is downloaded fresh each time the `/geojsonQPF` endpoint is called
- The application uses a grid-based approach to calculate average precipitation over polygon areas
- All geographic data uses WGS84 coordinate system (EPSG:4326)