import os
import requests
import polyline
import folium
from django.shortcuts import render, redirect
from .forms import RouteForm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def generate_route(request):
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            start_lat = form.cleaned_data['start_lat']
            start_lng = form.cleaned_data['start_lng']
            end_lat = form.cleaned_data['end_lat']
            end_lng = form.cleaned_data['end_lng']

            # Configure retries with exponential backoff
            session = requests.Session()
            retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retries)
            session.mount('https://', adapter)
            session.mount('http://', adapter)

            # Send a request to the OSRM API
            osrm_url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full"
            try:
                response = session.get(osrm_url, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                return render(request, 'navigation/error.html', {'error': str(e)})

            # Extract the geometry (polyline)
            data = response.json()
            encoded_polyline = data['routes'][0]['geometry']
            route_coordinates = polyline.decode(encoded_polyline)

            # Create the map with satellite tiles
            route_map = folium.Map(
                location=[start_lat, start_lng],
                zoom_start=13,
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Tiles &copy; Esri'
            )
            folium.PolyLine(route_coordinates, color="blue", weight=5, opacity=0.7).add_to(route_map)
            folium.Marker([start_lat, start_lng], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
            folium.Marker([end_lat, end_lng], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

            # Define the static folder path
            static_map_dir = os.path.join(os.getcwd(), 'static', 'navigation')

            # Ensure the directory exists
            if not os.path.exists(static_map_dir):
                os.makedirs(static_map_dir)

            # Define the file path
            map_path = os.path.join(static_map_dir, 'route_map.html')

            # Save the map
            route_map.save(map_path)

            # Redirect to the generated map file
            return redirect(f'/static/navigation/route_map.html')

    else:
        form = RouteForm()

    return render(request, 'navigation/map_view.html', {'form': form})


