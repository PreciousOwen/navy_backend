import os
import requests
import polyline
import folium
from django.shortcuts import render, redirect
from .forms import RouteForm


# def generate_route(request):
#     if request.method == 'POST':
#         form = RouteForm(request.POST)
#         if form.is_valid():
#             start_lat = form.cleaned_data['start_lat']
#             start_lng = form.cleaned_data['start_lng']
#             end_lat = form.cleaned_data['end_lat']
#             end_lng = form.cleaned_data['end_lng']

#             # Send a request to the OSRM API
#             osrm_url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full"
#             response = requests.get(osrm_url)
#             data = response.json()

#             # Extract the geometry (polyline)
#             encoded_polyline = data['routes'][0]['geometry']
#             route_coordinates = polyline.decode(encoded_polyline)

#             # Create the map
#             route_map = folium.Map(location=[start_lat, start_lng], zoom_start=13)
#             folium.PolyLine(route_coordinates, color="blue", weight=5, opacity=0.7).add_to(route_map)
#             folium.Marker([start_lat, start_lng], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
#             folium.Marker([end_lat, end_lng], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

#             # Define the static folder path
#             static_map_dir = os.path.join(os.getcwd(), 'static', 'navigation')

#             # Ensure the directory exists
#             if not os.path.exists(static_map_dir):
#                 os.makedirs(static_map_dir)

#             # Define the file path
#             map_path = os.path.join(static_map_dir, 'route_map.html')

#             # Save the map
#             route_map.save(map_path)

#             # Redirect to the generated map file
#             return redirect(f'/static/navigation/route_map.html')

#     else:
#         form = RouteForm()

#     return render(request, 'navigation/map_view.html', {'form': form})


# from django.shortcuts import render
# from .models import OSMPoint

# def map_view(request):
#     locations = OSMPoint.objects.all()
#     return render(request, 'map.html', {'locations': locations})



from django.shortcuts import render
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import AsGeoJSON
from .models import Road

def map_view(request):
    roads = Road.objects.annotate(geojson=AsGeoJSON("geom"))
    road_data = list(roads.values("name", "geojson"))

    # Get the first road and extract its starting point
    first_road = roads.first()
    marker = None  # Default value

    if first_road:
        geom = GEOSGeometry(first_road.geom.geojson)  # Convert to GEOSGeometry
        if geom and geom.num_coords > 0:
            marker = {"lat": geom.coords[0][1], "lng": geom.coords[0][0]}  # Extract first point

    return render(request, "map.html", {"road_data": road_data, "marker": marker})


######################################################################################
################################     SHORTEST PATH   #################################


from django.contrib.gis.geos import GEOSGeometry, Point
import networkx as nx
from .models import Road

def build_graph():
    G = nx.Graph()
    roads = Road.objects.all()

    for road in roads:
        geom = road.geom  # Get LineString geometry
        coords = list(geom.coords)  # Convert LineString to a list of points
        
        for i in range(len(coords) - 1):
            start = coords[i]
            end = coords[i + 1]
            distance = GEOSGeometry(Point(start)).distance(GEOSGeometry(Point(end)))  # Calculate distance
            
            G.add_edge(start, end, weight=distance)  # Add edge to graph

    return G



import networkx as nx
import folium

def find_shortest_path(start_lat, start_lng, end_lat, end_lng):
    G = build_graph()
    start = (start_lng, start_lat)
    end = (end_lng, end_lat)

    try:
        path = nx.shortest_path(G, source=start, target=end, weight="weight")
        return path
    except nx.NetworkXNoPath:
        return None



from django.shortcuts import render
from django.http import HttpResponse
import folium
from .forms import RouteForm
from .models import Road
import networkx as nx

def generate_route(request):
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            start_lat = form.cleaned_data['start_lat']
            start_lng = form.cleaned_data['start_lng']
            end_lat = form.cleaned_data['end_lat']
            end_lng = form.cleaned_data['end_lng']

            # Find the shortest path based on the coordinates
            path = find_shortest_path(start_lat, start_lng, end_lat, end_lng)
            if path is None:
                return render(request, 'error.html', {"message": "No path found"})

            # Create a folium map with the route
            route_map = folium.Map(location=[start_lat, start_lng], zoom_start=13)
            folium.PolyLine(path, color="blue", weight=5, opacity=0.7).add_to(route_map)
            folium.Marker([start_lat, start_lng], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
            folium.Marker([end_lat, end_lng], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

            # Render the map to an HTML string
            map_html = route_map._repr_html_()

            # Pass the HTML map string to the template
            return render(request, 'navigation/map_view.html', {'form': form, 'map_html': map_html})

    else:
        form = RouteForm()

    return render(request, 'navigation/map_view.html', {'form': form})


from django.db import connection  # Ensure this import is present
import json  # Ensure this import is present

def map_new_polygons(request):
    # Define the bounding box for the specific area (centered around -6.814328, 39.281655)
    case_study_bbox = (39.271655, -6.816286, 39.284623, -6.797216)  # (min_lng, min_lat, max_lng, max_lat)

    # Query to transform and fetch up to 1000 building polygons in WGS84 within the bounding box
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT osm_id, name, landuse, building, ST_AsGeoJSON(ST_Transform(way, 4326)) AS geometry
            FROM planet_osm_polygon
            WHERE building IS NOT NULL  -- Filter for building polygons
            AND ST_Intersects(
                ST_Transform(way, 4326),
                ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
            )
            LIMIT 1000;  -- Fetch up to 1000 building polygons
        """)
        building_rows = cursor.fetchall()

    # Query to fetch road data from the planet_osm_ways table and transform to EPSG:4326
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, tags::jsonb->>'name' AS name, ST_AsGeoJSON(ST_Transform(ST_MakeLine(ARRAY(
                SELECT ST_SetSRID(ST_MakePoint(n.lon, n.lat), 4326)
                FROM unnest(nodes) AS node_id
                JOIN planet_osm_nodes n ON n.id = node_id
            )), 4326)) AS geometry
            FROM planet_osm_ways
            WHERE tags::jsonb ? 'highway'  -- Filter for roads
            LIMIT 0;  -- Fetch up to 1000 road data
        """)
        road_rows = cursor.fetchall()

    # Prepare building data for the template
    building_data = [
        {
            "osm_id": row[0],
            "name": row[1] or None,  # Replace None with null for JavaScript compatibility
            "landuse": row[2] or None,
            "building": row[3] or None,
            "geometry": row[4]
        }
        for row in building_rows
    ]

    # Prepare road data for the template
    road_data = [
        {
            "osm_id": row[0],
            "name": row[1] or None,  # Replace None with null for JavaScript compatibility
            "geometry": row[2]
        }
        for row in road_rows
    ]

    # Serialize the data to JSON
    building_data_json = json.dumps(building_data)
    road_data_json = json.dumps(road_data)

    # Debugging: Log the serialized JSON data
    print("Serialized Building Data JSON:", building_data_json[:500])  # Log only the first 500 characters for brevity
    print("Serialized Road Data JSON:", road_data_json[:500])  # Log only the first 500 characters for brevity

    return render(request, "map_new_polygons.html", {
        "building_data_json": building_data_json,
        "road_data_json": road_data_json
    })

from .models import BufferedRoad  # Ensure BufferedRoad is imported

def map_view_polygons(request):
    """
    View to render road polygons on the map.
    """
    buffered_roads = BufferedRoad.objects.annotate(geojson=AsGeoJSON("geom"))
    road_data = list(buffered_roads.values("name", "geojson"))

    # Replace None with "Unnamed Road" for JavaScript compatibility
    for road in road_data:
        road["name"] = road["name"] or "Unnamed Road"

    return render(request, "map_polygons.html", {"road_data": road_data})

from django.db import connection  # Ensure this import is present
import json  # Ensure this import is present
import time  # Import time for measuring execution time
from .models import CachedRoad  # Import the CachedRoad model

def map_roads(request):
    print("Starting map_roads view...")  # Debugging: Start of the view
    start_time = time.time()  # Record the start time

    # Define the bounding box for the specific area
    case_study_bbox = (39.271655, -6.816286, 39.284623, -6.797216)  # (min_lng, min_lat, max_lng, max_lat)

    # Check if cached roads exist
    cached_roads = CachedRoad.objects.all()
    if cached_roads.exists():
        print("Using cached road data...")
        road_data = [
            {
                "osm_id": road.osm_id,
                "name": road.name,
                "geometry": road.geometry
            }
            for road in cached_roads
        ]
    else:
        # Query to fetch road data from the planet_osm_ways table
        try:
            print("Executing SQL query to fetch road data...")  # Debugging: Before executing the query
            query_start_time = time.time()  # Record query start time

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT id, tags::jsonb->>'name' AS name, ST_AsGeoJSON(ST_Transform(ST_MakeLine(ARRAY(
                        SELECT ST_SetSRID(ST_MakePoint(n.lon / 1e7, n.lat / 1e7), 4326)
                        FROM unnest(nodes) AS node_id
                        JOIN planet_osm_nodes n ON n.id = node_id
                    ))) AS geometry
                    FROM planet_osm_ways
                    WHERE tags::jsonb ? 'highway'
                    AND ST_Intersects(
                        ST_MakeLine(ARRAY(
                            SELECT ST_SetSRID(ST_MakePoint(n.lon / 1e7, n.lat / 1e7), 4326)
                            FROM unnest(nodes) AS node_id
                            JOIN planet_osm_nodes n ON n.id = node_id
                        )),
                        ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                    )
                    LIMIT 2000;  -- Fetch up to 2000 road data
                """)
                road_rows = cursor.fetchall()

            query_end_time = time.time()  # Record query end time
            print(f"SQL query executed successfully. Time taken: {query_end_time - query_start_time:.2f} seconds")  # Debugging: Query execution time
            print(f"Number of roads fetched: {len(road_rows)}")  # Debugging: Number of rows fetched

        except Exception as e:
            print(f"Error during SQL query execution: {e}")  # Debugging: Log any SQL errors
            return render(request, "error.html", {"message": "Error fetching road data."})

        # Save the queried roads to the CachedRoad model
        print("Saving queried roads to the database...")
        road_data = []
        for row in road_rows:
            road_data.append({
                "osm_id": row[0],
                "name": row[1] or "Unnamed Road",  # Replace None with "Unnamed Road" for JavaScript compatibility
                "geometry": row[2]
            })
            CachedRoad.objects.create(osm_id=row[0], name=row[1], geometry=row[2])

    # Serialize the data to JSON
    try:
        print("Serializing road data to JSON...")  # Debugging: Before serialization
        serialization_start_time = time.time()  # Record serialization start time

        road_data_json = json.dumps(road_data)

        serialization_end_time = time.time()  # Record serialization end time
        print(f"Road data serialized successfully. Time taken: {serialization_end_time - serialization_start_time:.2f} seconds")  # Debugging: Serialization time

    except Exception as e:
        print(f"Error during JSON serialization: {e}")  # Debugging: Log any serialization errors
        return render(request, "error.html", {"message": "Error serializing road data."})

    end_time = time.time()  # Record the end time
    print(f"map_roads view completed successfully. Total time taken: {end_time - start_time:.2f} seconds")  # Debugging: Total execution time

    return render(request, "map_roads.html", {
        "road_data_json": road_data_json
    })

from django.db import connection  # Ensure this import is present
import json  # Ensure this import is present
import time  # Import time for measuring execution time
from decimal import Decimal
from django.http import JsonResponse  # Use JsonResponse for better error handling

def map_nodes(request):
    print("Starting map_nodes view...")  # Debugging: Start of the view
    start_time = time.time()  # Record the start time

    # Define the bounding box for the specific area
    case_study_bbox = (39.271655, -6.816286, 39.284623, -6.797216)  # (min_lng, min_lat, max_lng, max_lat)

    # Query to fetch nodes within the bounding box
    try:
        print("Executing SQL query to fetch nodes...")  # Debugging: Before executing the query
        query_start_time = time.time()  # Record query start time

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT id, lat / 1e7 AS latitude, lon / 1e7 AS longitude, tags
                FROM planet_osm_nodes
                WHERE ST_Intersects(
                    ST_SetSRID(ST_MakePoint(lon / 1e7, lat / 1e7), 4326),
                    ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                )
                LIMIT 2000;  -- Fetch up to 2000 nodes
            """)
            node_rows = cursor.fetchall()

        query_end_time = time.time()  # Record query end time
        print(f"SQL query executed successfully. Time taken: {query_end_time - query_start_time:.2f} seconds")  # Debugging: Query execution time
        print(f"Number of nodes fetched: {len(node_rows)}")  # Debugging: Number of rows fetched

    except Exception as e:
        print(f"Error during SQL query execution: {e}")  # Debugging: Log any SQL errors
        return JsonResponse({"error": "Error fetching node data."}, status=500)

    # Prepare node data for the template
    try:
        print("Processing node data...")  # Debugging: Before processing node data
        processing_start_time = time.time()  # Record processing start time

        node_data = [
            {
                "id": row[0],
                "latitude": float(row[1]),  # Convert Decimal to float
                "longitude": float(row[2]),  # Convert Decimal to float
                "tags": row[3]
            }
            for row in node_rows
        ]

        processing_end_time = time.time()  # Record processing end time
        print(f"Node data processed successfully. Time taken: {processing_end_time - processing_start_time:.2f} seconds")  # Debugging: Processing time

    except Exception as e:
        print(f"Error during node data processing: {e}")  # Debugging: Log any processing errors
        return JsonResponse({"error": "Error processing node data."}, status=500)

    # Serialize the data to JSON
    try:
        print("Serializing node data to JSON...")  # Debugging: Before serialization
        serialization_start_time = time.time()  # Record serialization start time

        node_data_json = json.dumps(node_data)

        serialization_end_time = time.time()  # Record serialization end time
        print(f"Node data serialized successfully. Time taken: {serialization_end_time - serialization_start_time:.2f} seconds")  # Debugging: Serialization time

    except Exception as e:
        print(f"Error during JSON serialization: {e}")  # Debugging: Log any serialization errors
        return JsonResponse({"error": "Error serializing node data."}, status=500)

    end_time = time.time()  # Record the end time
    print(f"map_nodes view completed successfully. Total time taken: {end_time - start_time:.2f} seconds")  # Debugging: Total execution time

    return render(request, "map_nodes.html", {
        "node_data_json": node_data_json
    })

from .models import CachedRoad  # Ensure CachedRoad is imported
from django.http import JsonResponse
from django import forms
import networkx as nx
from shapely.geometry import LineString, Point, MultiPoint  # Ensure MultiPoint is imported
import json  # Ensure json is imported
from shapely.ops import nearest_points  # Ensure nearest_points is imported

class ShortestPathForm(forms.Form):
    start_lat = forms.FloatField(label="Start Latitude")
    start_lng = forms.FloatField(label="Start Longitude")
    end_lat = forms.FloatField(label="End Latitude")
    end_lng = forms.FloatField(label="End Longitude")

def university_roads(request):
    print("Fetching roads from CachedRoad table...")  # Debugging: Start of the view
    start_time = time.time()  # Record the start time

    # Fetch all roads from the CachedRoad table
    try:
        cached_roads = CachedRoad.objects.all()
        road_data = [
            {
                "osm_id": road.osm_id,
                "name": road.name,
                "geometry": road.geometry  # Use the geometry directly
            }
            for road in cached_roads
        ]
        print(f"Number of roads fetched: {len(road_data)}")  # Debugging: Number of roads fetched
    except Exception as e:
        print(f"Error fetching roads from CachedRoad: {e}")  # Debugging: Log any errors
        return render(request, "error.html", {"message": "Error fetching roads from CachedRoad."})

    # If the request method is POST, calculate the shortest path
    if request.method == "POST":
        form = ShortestPathForm(request.POST)
        if form.is_valid():
            start_lat = form.cleaned_data["start_lat"]
            start_lng = form.cleaned_data["start_lng"]
            end_lat = form.cleaned_data["end_lat"]
            end_lng = form.cleaned_data["end_lng"]

            # Build a graph from the CachedRoad table
            G = nx.Graph()
            for road in road_data:
                try:
                    geojson = road["geometry"]

                    # Parse the geometry if it is a string
                    if isinstance(geojson, str):
                        geojson = json.loads(geojson)

                    # Ensure the geometry is valid
                    if not geojson or "coordinates" not in geojson:
                        print(f"Invalid geometry for road {road['osm_id']}: {geojson}")
                        continue

                    linestring = LineString(geojson["coordinates"])  # Use parsed geometry
                    for i in range(len(linestring.coords) - 1):
                        start = Point(linestring.coords[i])
                        end = Point(linestring.coords[i + 1])
                        distance = start.distance(end)
                        G.add_edge(tuple(start.coords[0]), tuple(end.coords[0]), weight=distance)
                except Exception as e:
                    print(f"Error processing road {road['osm_id']}: {e}")

            # Find the nearest nodes to the start and end points
            try:
                start_point = Point(start_lng, start_lat)
                end_point = Point(end_lng, end_lat)
                graph_nodes = MultiPoint([Point(node) for node in G.nodes])  # Convert graph nodes to MultiPoint
                nearest_start = nearest_points(start_point, graph_nodes)[1]
                nearest_end = nearest_points(end_point, graph_nodes)[1]

                # Calculate the shortest path
                path = nx.shortest_path(G, source=tuple(nearest_start.coords[0]), target=tuple(nearest_end.coords[0]), weight="weight")
                path_coords = [list(coord) for coord in path]
                print(f"Shortest path: {path_coords}")
            except nx.NetworkXNoPath:
                return render(request, "error.html", {"message": "No path found between the given points."})
            except Exception as e:
                print(f"Error finding shortest path: {e}")
                return render(request, "error.html", {"message": "Error finding shortest path."})

            # Serialize the shortest path to GeoJSON
            shortest_path_geojson = {
                "type": "LineString",
                "coordinates": path_coords
            }

            # Render the map with the shortest path
            road_data_json = json.dumps(road_data)
            shortest_path_json = json.dumps(shortest_path_geojson)
            return render(request, "university_roads.html", {
                "road_data_json": road_data_json,
                "shortest_path_json": shortest_path_json
            })

    else:
        form = ShortestPathForm()

    # Serialize the road data to JSON
    try:
        road_data_json = json.dumps(road_data)
    except Exception as e:
        print(f"Error serializing road data: {e}")  # Debugging: Log any serialization errors
        return render(request, "error.html", {"message": "Error serializing road data."})

    end_time = time.time()  # Record the end time
    print(f"university_roads view completed successfully. Total time taken: {end_time - start_time:.2f} seconds")  # Debugging: Total execution time

    return render(request, "university_roads.html", {
        "road_data_json": road_data_json,
        "form": form
    })

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.gis.geos import LineString
from .models import CachedRoad  # Use CachedRoad instead of Road
import json
from django.db.models import Max  # Import Max for generating unique osm_id

@csrf_exempt
def add_path(request):
    """
    View to add a new path to the CachedRoad model.
    """
    if request.method == 'POST':
        try:
            # Parse the coordinates from the request body
            data = json.loads(request.body)
            coordinates = data.get('coordinates')
            name = data.get('name', 'Unnamed Path')  # Default name if not provided

            if not coordinates or len(coordinates) < 2:
                return JsonResponse({'error': 'Invalid coordinates. At least two points are required.'}, status=400)

            # Generate a unique osm_id
            max_osm_id = CachedRoad.objects.aggregate(Max('osm_id'))['osm_id__max'] or 0
            osm_id = max_osm_id + 1

            # Create a GeoJSON LineString geometry
            geojson_geometry = {
                "type": "LineString",
                "coordinates": coordinates
            }

            # Save the new path to the CachedRoad model
            CachedRoad.objects.create(osm_id=osm_id, name=name, geometry=geojson_geometry)
            return JsonResponse({'message': 'Path added successfully.'}, status=201)
        except Exception as e:
            return JsonResponse({'error': f'Error adding path: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)


@csrf_exempt
def remove_paths(request):
    """
    View to remove paths from the CachedRoad model.
    """
    if request.method == 'POST':
        try:
            # Parse the request body for an optional osm_id
            data = json.loads(request.body) if request.body else {}
            osm_id = data.get('osm_id')

            if osm_id:
                # Delete the path with the specified osm_id
                deleted_count, _ = CachedRoad.objects.filter(osm_id=osm_id).delete()
                if deleted_count > 0:
                    return JsonResponse({'message': f'Path with osm_id {osm_id} removed successfully.'}, status=200)
                else:
                    return JsonResponse({'error': f'No path found with osm_id {osm_id}.'}, status=404)
            else:
                # Delete all paths if no osm_id is provided
                CachedRoad.objects.all().delete()
                return JsonResponse({'message': 'All paths removed successfully.'}, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Error removing paths: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

from .models import DITCachedBuildings  # Import the CachedBlocks model

@csrf_exempt
def university_blocks(request):
    """
    View to fetch and save building blocks within the specified bounding box.
    """
    print("Fetching building blocks within the case study area...")  # Debugging: Start of the view
    case_study_bbox = (39.273264, -6.817276, 39.288407, -6.807517)  # Updated bounding box

    # Check if cached blocks exist
    cached_blocks_count = DITCachedBuildings.objects.count()
    if cached_blocks_count >= 2000:
        print("Using cached building blocks...")
        block_data = [
            {
                "osm_id": block.osm_id,
                "name": block.name,
                "geometry": block.geometry
            }
            for block in DITCachedBuildings.objects.all()
        ]
    else:
        # Query to fetch building blocks from the database
        try:
            print("Executing SQL query to fetch building blocks...")  # Debugging: Before executing the query
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT osm_id, name, landuse, building, ST_AsGeoJSON(ST_Transform(way, 4326)) AS geometry
                    FROM planet_osm_polygon
                    WHERE building IS NOT NULL  -- Filter for building polygons
                    AND ST_Intersects(
                        ST_Transform(way, 4326),
                        ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                    )
                    LIMIT 5000;  -- Fetch up to 2000 building polygons
                """)
                block_rows = cursor.fetchall()

            print(f"Number of blocks fetched: {len(block_rows)}")  # Debugging: Number of rows fetched

            # Save the queried blocks to the CachedBlocks model
            print("Saving queried blocks to the database...")
            block_data = []
            for row in block_rows:
                block_data.append({
                    "osm_id": row[0],
                    "name": row[1] or "Unnamed Block",  # Replace None with "Unnamed Block" for JavaScript compatibility
                    "geometry": row[4]
                })
                # Avoid duplicate entries
                DITCachedBuildings.objects.update_or_create(
                    osm_id=row[0],
                    defaults={"name": row[1], "geometry": row[4]}
                )

        except Exception as e:
            print(f"Error during SQL query execution: {e}")  # Debugging: Log any SQL errors
            return render(request, "error.html", {"message": "Error fetching building blocks."})

    # Serialize the block data to JSON
    try:
        print("Serializing block data to JSON...")  # Debugging: Before serialization
        block_data_json = json.dumps(block_data)
        print("Block data serialized successfully.")  # Debugging: Serialization success
    except Exception as e:
        print(f"Error during JSON serialization: {e}")  # Debugging: Log any serialization errors
        return render(request, "error.html", {"message": "Error serializing block data."})

    return render(request, "university_blocks.html", {
        "block_data_json": block_data_json
    })

from .models import DITCachedBuildings, CachedRoad  # Import the required models

def university_blocks_roads(request):
    print("Fetching buildings and roads for university_blocks_roads...")  # Debugging: Start of the view

    # Fetch buildings and roads
    buildings = DITCachedBuildings.objects.all()
    building_data = [{"osm_id": b.osm_id, "name": b.name, "geometry": b.geometry} for b in buildings]
    roads = CachedRoad.objects.all()
    road_data = [{"osm_id": r.osm_id, "name": r.name, "geometry": r.geometry} for r in roads]

    # Get start and end coordinates from query parameters
    start_lat = request.GET.get("start_lat")
    start_lng = request.GET.get("start_lng")
    end_lat = request.GET.get("end_lat")
    end_lng = request.GET.get("end_lng")

    if start_lat and start_lng and end_lat and end_lng:
        try:
            # Build a graph and calculate the shortest path
            G = nx.Graph()
            for road in road_data:
                geojson = json.loads(road["geometry"])
                linestring = LineString(geojson["coordinates"])
                for i in range(len(linestring.coords) - 1):
                    start = Point(linestring.coords[i])
                    end = Point(linestring.coords[i + 1])
                    distance = start.distance(end)
                    G.add_edge(tuple(start.coords[0]), tuple(end.coords[0]), weight=distance)

            start_point = Point(float(start_lng), float(start_lat))
            end_point = Point(float(end_lng), float(end_lat))
            graph_nodes = MultiPoint([Point(node) for node in G.nodes])
            nearest_start = nearest_points(start_point, graph_nodes)[1]
            nearest_end = nearest_points(end_point, graph_nodes)[1]

            path = nx.shortest_path(G, source=tuple(nearest_start.coords[0]), target=tuple(nearest_end.coords[0]), weight="weight")
            path_coords = [list(coord) for coord in path]

            shortest_path_geojson = {"type": "LineString", "coordinates": path_coords}
        except Exception as e:
            print(f"Error calculating shortest path: {e}")
            return render(request, "error.html", {"message": "Error calculating shortest path."})
    else:
        shortest_path_geojson = None

    return render(request, "university_blocks_roads.html", {
        "road_data_json": json.dumps(road_data),
        "building_data_json": json.dumps(building_data),
        "shortest_path_json": json.dumps(shortest_path_geojson) if shortest_path_geojson else None,
    })

from django.shortcuts import render
# ...existing code...

def index(request):
    """
    View to render the index page for QR code scanning.
    """
    return render(request, "index.html")

from django.http import JsonResponse
from .models import Location
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def fetch_destinations(request):
    """
    View to fetch all destinations from the Location model.
    """
    try:
        locations = Location.objects.all()
        data = [
            {
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
            }
            for location in locations
        ]
        logger.debug(f"Fetched destinations: {data}")  # Log the fetched data
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error fetching destinations: {str(e)}")  # Log any errors
        return JsonResponse({"error": f"Error fetching destinations: {str(e)}"}, status=500)