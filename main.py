from flask import Flask, render_template, jsonify, request
import os
import requests
import json

app = Flask(__name__)
API_KEY = '162f9144b0a945b4a790f1e68cff7d30'
BASE_URL_autocomplete = 'https://api.geoapify.com/v1/geocode/autocomplete'
BASE_URL_reverse_geocode = "https://api.geoapify.com/v1/geocode/reverse"
BASE_URL_ROUTING = 'https://api.geoapify.com/v1/routing'


@app.route('/')
def index():
    return render_template("home.html")


@app.route('/routing')
def routing():
    return render_template('routing.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/reverse-geocode', methods=['GET'])
def reverse_geocode():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    url = f"{BASE_URL_reverse_geocode}?lat={lat}&lon={lon}&apiKey={API_KEY}"
    headers = {'Accept': 'application/json'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Optionally, you could extract and format specific details if needed
        if data.get('features'):
            return jsonify(data)
        else:
            return jsonify(
                {'error': 'No address found for the given coordinates'}), 404

    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    text = request.args.get('text')
    url = f"{BASE_URL_autocomplete}?text={text}&apiKey={API_KEY}"

    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500


def calculate_elevation_profile_data(route_data):
    leg_elevations = []

    # Extract elevation data from the API response
    for leg in route_data['features'][0]['properties']['legs']:
        if 'elevation_range' in leg:
            leg_elevations.append(leg['elevation_range'])
        else:
            leg_elevations.append([])

    labels = []
    data = []

    for index, leg_elevation in enumerate(leg_elevations):
        previous_legs_distance = 0
        for i in range(index):
            previous_legs_distance += leg_elevations[i][-1][
                0]  # Sum up the distance of previous legs

        labels.extend([
            elevation_data[0] + previous_legs_distance
            for elevation_data in leg_elevation
        ])
        data.extend([elevation_data[1] for elevation_data in leg_elevation])

    # Optimize array size to avoid performance problems
    labels_optimized = []
    data_optimized = []
    min_dist = 5  # 5 meters
    min_height = 10  # ~10 meters

    for i, dist in enumerate(labels):
        if (i == 0 or i == len(labels) - 1
                or (dist - labels_optimized[-1]) > min_dist
                or abs(data[i] - data_optimized[-1]) > min_height):
            labels_optimized.append(dist)
            data_optimized.append(data[i])
    return {'data': data_optimized, 'labels': labels_optimized}


@app.route('/route', methods=['GET'])
def get_route():
    start_lat = request.args.get('start_lat')
    start_lon = request.args.get('start_lon')
    end_lat = request.args.get('end_lat')
    end_lon = request.args.get('end_lon')

    if not all([start_lat, start_lon, end_lat, end_lon]):
        return jsonify({'error':
                        'Start and end coordinates are required'}), 400

    url = f"{BASE_URL_ROUTING}?waypoints={start_lat},{start_lon}|{end_lat},{end_lon}&mode=bicycle&details=elevation&apiKey={API_KEY}"
    headers = {'Accept': 'application/json'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract coordinates and instructions
        coordinates = data['features'][0]['geometry']['coordinates'][0]
        instructions = [
            step['instruction']['text']
            for step in data['features'][0]['properties']['legs'][0]['steps']
        ]
        elevation_data = calculate_elevation_profile_data(data)

        return jsonify({
            'coordinates': coordinates,
            'instructions': instructions,
            'elevations': elevation_data,
        })
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500


@app.route('/data')
def data():
    json_path = 'data/accident_prone.json'
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            data = data['locations']
            return jsonify(data)
    return jsonify({"error": "File not found"}), 404

@app.route('/datageo')
def data_geo():
    geojson_path = 'data/Victoria_crash_road.geojson'
    if os.path.exists(geojson_path):
        with open(geojson_path) as f:
            print('f', f)
            data = f.read()
        return data, 200, {'Content-Type': 'application/geo+json'}
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
