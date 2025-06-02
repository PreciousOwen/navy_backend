import os
import requests
import polyline
import folium
import json
import time
import networkx as nx
from decimal import Decimal # Used for potential float conversions from DB

# Django imports
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.gis.geos import GEOSGeometry, Point as DjangoPoint, LineString as DjangoLineString # Renamed to avoid clash with Shapely
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.db import connection
from django.db.models import Max
from django import forms

# Shapely imports for geometric operations (crucial for graph building and nearest_points)
from shapely.geometry import LineString as ShapelyLineString, Point as ShapelyPoint, MultiPoint as ShapelyMultiPoint
from shapely.ops import nearest_points

# Your models (ensure these are correctly defined in your models.py)
from .models import Road, BufferedRoad, CachedRoad, DITCachedBuildings

# Your forms (ensure this is correctly defined in your forms.py)
from .forms import RouteForm

# ---
# General Utility Functions (Optional, but good practice for reusability)
# ---

def _get_geojson_from_db_result(geojson_string_or_dict):
    """
    Helper to ensure geometry is a Python dictionary, parsing if it's a string.
    Handles potential malformed JSON by returning None.
    """
    if isinstance(geojson_string_or_dict, dict):
        return geojson_string_or_dict
    elif isinstance(geojson_string_or_dict, str):
        try:
            return json.loads(geojson_string_or_dict)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON geometry: {e}")
            return None
    return None # For unexpected types

def _build_networkx_graph_from_cached_roads(cached_road_queryset):
    """
    Builds a NetworkX graph from a queryset of CachedRoad objects.
    Returns the graph and a list of successfully processed road data (as dicts).
    """
    G = nx.Graph()
    processed_road_data = []

    for road_obj in cached_road_queryset:
        try:
            geometry_dict = _get_geojson_from_db_result(road_obj.geometry)
            if not geometry_dict or "coordinates" not in geometry_dict:
                print(f"Warning: CachedRoad {road_obj.osm_id} geometry is invalid or missing 'coordinates'. Skipping.")
                continue

            # Add to processed road data list
            processed_road_data.append({
                "osm_id": road_obj.osm_id,
                "name": road_obj.name,
                "geometry": geometry_dict # Keep as dict for template
            })

            # Build NetworkX graph using Shapely geometries
            linestring = ShapelyLineString(geometry_dict["coordinates"])
            
            # Iterate through points of the linestring to add edges
            for i in range(len(linestring.coords) - 1):
                # Use tuple(point) for NetworkX nodes to ensure hashability
                start_node = tuple(linestring.coords[i])
                end_node = tuple(linestring.coords[i + 1])
                
                # Calculate distance between Shapely Points
                distance = ShapelyPoint(start_node).distance(ShapelyPoint(end_node))
                G.add_edge(start_node, end_node, weight=distance)

        except Exception as e:
            print(f"An error occurred processing CachedRoad {road_obj.osm_id} for graph: {e}. Skipping this road.")
            # Optionally, delete the malformed entry: road_obj.delete()
            continue
    return G, processed_road_data

# ---
# 1. map_view (Basic Road Display)
# ---

def map_view(request):
    """
    Renders a map displaying roads from the Road model.
    This view uses Django's GIS features for direct geometry handling.
    """
    roads = Road.objects.annotate(geojson=AsGeoJSON("geom"))
    road_data = []
    for road in roads:
        try:
            # AsGeoJSON returns a string, parse it to a dictionary for JS
            geojson_dict = json.loads(road.geojson)
            road_data.append({"name": road.name, "geojson": geojson_dict})
        except json.JSONDecodeError as e:
            print(f"Error parsing GeoJSON for Road {road.id}: {e}. Skipping.")
            continue

    first_road = roads.first()
    marker = None
    if first_road:
        # GEOSGeometry can parse GeoJSON string directly
        geom = GEOSGeometry(first_road.geom.geojson)
        if geom and geom.num_coords > 0:
            # Assuming first point of linestring for marker
            marker = {"lat": geom.coords[0][1], "lng": geom.coords[0][0]}

    return render(request, "map.html", {"road_data": json.dumps(road_data), "marker": marker})

# ---
# 2. generate_route (Folium Based with OSRM)
# ---

def generate_route(request):
    """
    Generates a route using the OSRM API (external service) and displays it on a Folium map.
    This is a separate routing mechanism from the internal graph-based one.
    """
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            start_lat = form.cleaned_data['start_lat']
            start_lng = form.cleaned_data['start_lng']
            end_lat = form.cleaned_data['end_lat']
            end_lng = form.cleaned_data['end_lng']

            osrm_url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full"
            try:
                response = requests.get(osrm_url)
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                data = response.json()

                if not data.get('routes'):
                    return render(request, 'error.html', {"message": "No route found by OSRM for the given points."})

                encoded_polyline = data['routes'][0]['geometry']
                route_coordinates = polyline.decode(encoded_polyline)

                route_map = folium.Map(location=[start_lat, start_lng], zoom_start=13)
                folium.PolyLine(route_coordinates, color="blue", weight=5, opacity=0.7).add_to(route_map)
                folium.Marker([start_lat, start_lng], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
                folium.Marker([end_lat, end_lng], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

                map_html = route_map._repr_html_()
                return render(request, 'navigation/map_view.html', {'form': form, 'map_html': map_html})

            except requests.exceptions.RequestException as e:
                print(f"Error connecting to OSRM: {e}")
                return render(request, 'error.html', {"message": f"Error connecting to routing service: {e}"})
            except Exception as e:
                print(f"Error processing OSRM response: {e}")
                return render(request, 'error.html', {"message": f"An unexpected error occurred during routing: {e}"})

    else:
        form = RouteForm()

    return render(request, 'navigation/map_view.html', {'form': form, 'map_html': None}) # Pass None if no map yet

# ---
# 3. map_new_polygons (Buildings and Roads from raw OSM tables)
# ---

def map_new_polygons(request):
    """
    Fetches and displays building polygons and road data directly from raw OSM tables
    (planet_osm_polygon and planet_osm_ways) within a defined bounding box.
    """
    case_study_bbox = (39.271655, -6.816286, 39.284623, -6.797216) # (min_lng, min_lat, max_lng, max_lat)

    building_data = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT osm_id, name, landuse, building, ST_AsGeoJSON(ST_Transform(way, 4326)) AS geometry
                FROM planet_osm_polygon
                WHERE building IS NOT NULL
                AND ST_Intersects(
                    ST_Transform(way, 4326),
                    ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                )
                LIMIT 1000;
            """)
            building_rows = cursor.fetchall()
            for row in building_rows:
                geom_dict = _get_geojson_from_db_result(row[4])
                if geom_dict:
                    building_data.append({
                        "osm_id": row[0],
                        "name": row[1] or None,
                        "landuse": row[2] or None,
                        "building": row[3] or None,
                        "geometry": geom_dict
                    })
    except Exception as e:
        print(f"Error fetching building data for map_new_polygons: {e}")
        return render(request, "error.html", {"message": f"Error fetching building data: {e}"})

    road_data = []
    try:
        with connection.cursor() as cursor:
            # Note: The original query for roads from planet_osm_ways was complex and might be slow.
            # This version uses a simpler approach if 'nodes' column is directly available or
            # assumes 'way' column for LineString geometry like planet_osm_line.
            # If planet_osm_ways stores nodes as an array of IDs, the original query might be necessary.
            # For this rewrite, I'm adapting to a common case where 'way' is a geometry column.
            # If your 'planet_osm_ways' table has a 'way' column of type geometry, this should work.
            # Otherwise, you'll need to re-insert your original complex query for 'planet_osm_ways'.
            cursor.execute(f"""
                SELECT osm_id, name, highway, ST_AsGeoJSON(ST_Transform(way, 4326)) AS geometry
                FROM planet_osm_line
                WHERE highway IS NOT NULL
                AND ST_Intersects(
                    ST_Transform(way, 4326),
                    ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                )
                LIMIT 1000;
            """)
            road_rows = cursor.fetchall()
            for row in road_rows:
                geom_dict = _get_geojson_from_db_result(row[3])
                if geom_dict:
                    road_data.append({
                        "osm_id": row[0],
                        "name": row[1] or None,
                        "highway": row[2] or None,
                        "geometry": geom_dict
                    })
    except Exception as e:
        print(f"Error fetching road data for map_new_polygons: {e}")
        return render(request, "error.html", {"message": f"Error fetching road data: {e}"})

    building_data_json = json.dumps(building_data)
    road_data_json = json.dumps(road_data)

    print("Serialized Building Data JSON (first 500 chars):", building_data_json[:500])
    print("Serialized Road Data JSON (first 500 chars):", road_data_json[:500])

    return render(request, "map_new_polygons.html", {
        "building_data_json": building_data_json,
        "road_data_json": road_data_json
    })

# ---
# 4. map_view_polygons (Buffered Roads)
# ---

def map_view_polygons(request):
    """
    View to render road polygons on the map from BufferedRoad model.
    Assumes BufferedRoad.geom is a PolygonField.
    """
    buffered_roads = BufferedRoad.objects.annotate(geojson=AsGeoJSON("geom"))
    road_data = []
    for road in buffered_roads:
        try:
            # AsGeoJSON returns a string, parse it to a dictionary for JS
            geometry_dict = json.loads(road.geojson)
            road_data.append({
                "name": road.name or "Unnamed Road",
                "geojson": geometry_dict
            })
        except json.JSONDecodeError as e:
            print(f"Error decoding GeoJSON for BufferedRoad {road.id}: {e}. Skipping.")
            continue # Skip this road if its GeoJSON is malformed
        except Exception as e:
            print(f"An unexpected error occurred processing BufferedRoad {road.id}: {e}. Skipping.")
            continue

    return render(request, "map_polygons.html", {"road_data": json.dumps(road_data)})

# ---
# 5. map_roads (Cached Road Data)
# ---

def map_roads(request):
    """
    Fetches and displays road data from the CachedRoad model.
    Populates CachedRoad from raw OSM data if the cache is empty.
    Ensures geometry is stored as a JSON string in CachedRoad.
    """
    print("Starting map_roads view...")
    start_time = time.time()

    case_study_bbox = (39.271655, -6.816286, 39.284623, -6.797216)

    road_data = []
    cached_roads_count = CachedRoad.objects.count()

    if cached_roads_count > 0:
        print("Using cached road data...")
        for road_obj in CachedRoad.objects.all():
            geom_dict = _get_geojson_from_db_result(road_obj.geometry)
            if geom_dict:
                road_data.append({
                    "osm_id": road_obj.osm_id,
                    "name": road_obj.name,
                    "geometry": geom_dict # Keep as dict for template
                })
            else:
                print(f"Warning: Malformed geometry in CachedRoad {road_obj.osm_id}. Skipping.")
                # Option to delete malformed data: road_obj.delete()
    else:
        print("Executing SQL query to fetch road data and populate cache...")
        query_start_time = time.time()
        try:
            with connection.cursor() as cursor:
                # Re-inserting your original complex query for planet_osm_ways
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
                    LIMIT 2000;
                """)
                road_rows = cursor.fetchall()

            print(f"SQL query executed. Time taken: {time.time() - query_start_time:.2f} seconds")
            print(f"Number of roads fetched: {len(road_rows)}")

            print("Saving queried roads to the database cache...")
            for row in road_rows:
                geometry_string = row[2] # ST_AsGeoJSON returns a string
                geom_dict = _get_geojson_from_db_result(geometry_string)
                if geom_dict:
                    CachedRoad.objects.update_or_create(
                        osm_id=row[0],
                        defaults={"name": row[1] or "Unnamed Road", "geometry": geometry_string}
                    )
                    road_data.append({
                        "osm_id": row[0],
                        "name": row[1] or "Unnamed Road",
                        "geometry": geom_dict # Convert back to dict for template
                    })
                else:
                    print(f"Warning: Geometry for OSM ID {row[0]} is malformed after DB fetch. Skipping save.")

        except Exception as e:
            print(f"Error during SQL query execution for map_roads: {e}")
            return render(request, "error.html", {"message": "Error fetching road data."})

    try:
        road_data_json = json.dumps(road_data)
    except Exception as e:
        print(f"Error during JSON serialization in map_roads: {e}")
        return render(request, "error.html", {"message": "Error serializing road data."})

    print(f"map_roads view completed. Total time: {time.time() - start_time:.2f} seconds")
    return render(request, "map_roads.html", {"road_data_json": road_data_json})

# ---
# 6. map_nodes (OSM Nodes)
# ---

def map_nodes(request):
    """
    Fetches and displays individual OSM nodes within a defined bounding box.
    """
    print("Starting map_nodes view...")
    start_time = time.time()

    case_study_bbox = (39.271655, -6.816286, 39.284623, -6.797216)

    node_data = []
    try:
        print("Executing SQL query to fetch nodes...")
        query_start_time = time.time()

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT id, lat / 1e7 AS latitude, lon / 1e7 AS longitude, tags
                FROM planet_osm_nodes
                WHERE ST_Intersects(
                    ST_SetSRID(ST_MakePoint(lon / 1e7, lat / 1e7), 4326),
                    ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                )
                LIMIT 2000;
            """)
            node_rows = cursor.fetchall()

        print(f"SQL query executed. Time: {time.time() - query_start_time:.2f} seconds")
        print(f"Number of nodes fetched: {len(node_rows)}")

        print("Processing node data...")
        for row in node_rows:
            tags = row[3]
            # Ensure tags is a dict. If it's a JSON string, parse it.
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except json.JSONDecodeError:
                    tags = {} # Default to empty dict if malformed
            elif not isinstance(tags, dict):
                tags = {} # Default to empty dict if not a string or dict

            node_data.append({
                "id": row[0],
                "latitude": float(row[1]),
                "longitude": float(row[2]),
                "tags": tags
            })

    except Exception as e:
        print(f"Error fetching or processing node data in map_nodes: {e}")
        return JsonResponse({"error": f"Error fetching node data: {e}"}, status=500)

    try:
        node_data_json = json.dumps(node_data)
    except Exception as e:
        print(f"Error during JSON serialization in map_nodes: {e}")
        return JsonResponse({"error": "Error serializing node data."}, status=500)

    print(f"map_nodes view completed. Total time: {time.time() - start_time:.2f} seconds")
    return render(request, "map_nodes.html", {"node_data_json": node_data_json})

# ---
# 7. ShortestPathForm and university_roads (Internal Pathfinding)
# ---

class ShortestPathForm(forms.Form):
    start_lat = forms.FloatField(label="Start Latitude")
    start_lng = forms.FloatField(label="Start Longitude")
    end_lat = forms.FloatField(label="End Latitude")
    end_lng = forms.FloatField(label="End Longitude")

def university_roads(request):
    """
    Displays cached university roads and calculates the shortest path between
    user-provided start and end coordinates using NetworkX.
    """
    print("Starting university_roads view...")
    start_time = time.time()

    # Build graph from CachedRoads
    G, road_data = _build_networkx_graph_from_cached_roads(CachedRoad.objects.all())
    print(f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

    shortest_path_geojson = None
    form = ShortestPathForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        start_lat = form.cleaned_data["start_lat"]
        start_lng = form.cleaned_data["start_lng"]
        end_lat = form.cleaned_data["end_lat"]
        end_lng = form.cleaned_data["end_lng"]

        try:
            if not G.nodes():
                return render(request, "error.html", {"message": "No road data available to calculate path. Graph is empty."})

            start_point = ShapelyPoint(start_lng, start_lat)
            end_point = ShapelyPoint(end_lng, end_lat)
            
            graph_nodes_shapely = ShapelyMultiPoint([ShapelyPoint(node) for node in G.nodes()])

            # Find the nearest nodes in the graph to the start and end points
            _, nearest_start_shapely = nearest_points(start_point, graph_nodes_shapely)
            _, nearest_end_shapely = nearest_points(end_point, graph_nodes_shapely)

            nearest_start_node_tuple = tuple(nearest_start_shapely.coords[0])
            nearest_end_node_tuple = tuple(nearest_end_shapely.coords[0])

            # Ensure found nearest nodes are actually in the graph
            if nearest_start_node_tuple not in G:
                print(f"Warning: Nearest start node {nearest_start_node_tuple} not found in graph nodes after nearest_points.")
                return render(request, "error.html", {"message": "Could not find a valid start point on the map."})
            if nearest_end_node_tuple not in G:
                print(f"Warning: Nearest end node {nearest_end_node_tuple} not found in graph nodes after nearest_points.")
                return render(request, "error.html", {"message": "Could not find a valid end point on the map."})

            path = nx.shortest_path(G, source=nearest_start_node_tuple, target=nearest_end_node_tuple, weight="weight")
            path_coords = [list(coord) for coord in path]
            print(f"Shortest path calculated with {len(path_coords)} points.")

            shortest_path_geojson = {
                "type": "LineString",
                "coordinates": path_coords
            }

        except nx.NetworkXNoPath:
            print("No path found between the given points.")
            return render(request, "error.html", {"message": "No path found between the given points."})
        except Exception as e:
            print(f"Error calculating shortest path in university_roads: {e}")
            return render(request, "error.html", {"message": f"Error calculating shortest path: {e}"})

    try:
        road_data_json = json.dumps(road_data)
        shortest_path_json_str = json.dumps(shortest_path_geojson) if shortest_path_geojson else "null"
    except Exception as e:
        print(f"Error serializing data for template in university_roads: {e}")
        return render(request, "error.html", {"message": "Error preparing map data."})

    print(f"university_roads view completed. Total time: {time.time() - start_time:.2f} seconds")
    return render(request, "university_roads.html", {
        "road_data_json": road_data_json,
        "shortest_path_json": shortest_path_json_str,
        "form": form
    })

# ---
# 8. add_path (User Drawn Paths)
# ---

@csrf_exempt
def add_path(request):
    """
    View to add a new path (drawn by user) to the CachedRoad model.
    Ensures geometry is stored as a JSON string.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            coordinates = data.get('coordinates')
            name = data.get('name', 'Unnamed Path')

            if not coordinates or len(coordinates) < 2:
                return JsonResponse({'error': 'Invalid coordinates. At least two points are required.'}, status=400)

            max_osm_id = CachedRoad.objects.aggregate(Max('osm_id'))['osm_id__max'] or 0
            osm_id = max_osm_id + 1

            geojson_geometry_dict = {
                "type": "LineString",
                "coordinates": coordinates
            }
            
            # Store it as a JSON string in the database
            geojson_geometry_string = json.dumps(geojson_geometry_dict)

            CachedRoad.objects.create(osm_id=osm_id, name=name, geometry=geojson_geometry_string)
            return JsonResponse({'message': 'Path added successfully.', 'osm_id': osm_id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            print(f"Error adding path: {e}")
            return JsonResponse({'error': f'Error adding path: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

# ---
# 9. remove_paths (Clear Cached Paths)
# ---

@csrf_exempt
def remove_paths(request):
    """
    View to remove paths from the CachedRoad model.
    Can remove a specific path by osm_id or all paths.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            osm_id = data.get('osm_id')

            if osm_id:
                deleted_count, _ = CachedRoad.objects.filter(osm_id=osm_id).delete()
                if deleted_count > 0:
                    return JsonResponse({'message': f'Path with osm_id {osm_id} removed successfully.'}, status=200)
                else:
                    return JsonResponse({'error': f'No path found with osm_id {osm_id}.'}, status=404)
            else:
                CachedRoad.objects.all().delete()
                return JsonResponse({'message': 'All paths removed successfully.'}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            print(f"Error removing paths: {e}")
            return JsonResponse({'error': f'Error removing paths: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=405)

# ---
# 10. university_blocks (Cached Buildings)
# ---

@csrf_exempt
def university_blocks(request):
    """
    Fetches and saves building blocks within the specified bounding box into DITCachedBuildings.
    Uses cached data if available. Ensures geometry is stored as a JSON string.
    """
    print("Starting university_blocks view...")
    case_study_bbox = (39.273264, -6.817276, 39.288407, -6.807517)

    block_data = []
    cached_blocks_count = DITCachedBuildings.objects.count()

    if cached_blocks_count >= 2000: # Use cached data if enough blocks are present
        print("Using cached building blocks...")
        for block_obj in DITCachedBuildings.objects.all():
            geom_dict = _get_geojson_from_db_result(block_obj.geometry)
            if geom_dict:
                block_data.append({
                    "osm_id": block_obj.osm_id,
                    "name": block_obj.name,
                    "geometry": geom_dict # Keep as dict for template
                })
            else:
                print(f"Warning: Malformed geometry in DITCachedBuildings {block_obj.osm_id}. Skipping.")
                # Option to delete malformed entry: block_obj.delete()
    else:
        print("Executing SQL query to fetch building blocks and populate cache...")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT osm_id, name, landuse, building, ST_AsGeoJSON(ST_Transform(way, 4326)) AS geometry
                    FROM planet_osm_polygon
                    WHERE building IS NOT NULL
                    AND ST_Intersects(
                        ST_Transform(way, 4326),
                        ST_MakeEnvelope({case_study_bbox[0]}, {case_study_bbox[1]}, {case_study_bbox[2]}, {case_study_bbox[3]}, 4326)
                    )
                    LIMIT 5000;
                """)
                block_rows = cursor.fetchall()

            print(f"Number of blocks fetched: {len(block_rows)}")
            print("Saving queried blocks to the database cache...")

            for row in block_rows:
                geometry_string = row[4] # ST_AsGeoJSON returns a string
                geom_dict = _get_geojson_from_db_result(geometry_string)
                if geom_dict:
                    DITCachedBuildings.objects.update_or_create(
                        osm_id=row[0],
                        defaults={"name": row[1], "geometry": geometry_string}
                    )
                    block_data.append({
                        "osm_id": row[0],
                        "name": row[1] or "Unnamed Block",
                        "geometry": geom_dict # Convert back to dict for template
                    })
                else:
                    print(f"Warning: Geometry for OSM ID {row[0]} is malformed after DB fetch. Skipping save.")

        except Exception as e:
            print(f"Error during SQL query execution for university_blocks: {e}")
            return render(request, "error.html", {"message": "Error fetching building blocks."})

    try:
        block_data_json = json.dumps(block_data)
        print("Block data serialized successfully.")
    except Exception as e:
        print(f"Error during JSON serialization in university_blocks: {e}")
        return render(request, "error.html", {"message": "Error serializing block data."})

    return render(request, "university_blocks.html", {"block_data_json": block_data_json})

# ---
# 11. university_blocks_roads (Combined View with Pathfinding)
# ---

def university_blocks_roads(request):
    """
    Fetches cached buildings and roads, and calculates a shortest path if coordinates are provided.
    This view is robust to malformed geometry data.
    """
    print("Starting university_blocks_roads view...")

    # Fetch buildings
    buildings = DITCachedBuildings.objects.all()
    building_data = []
    for b in buildings:
        geom_dict = _get_geojson_from_db_result(b.geometry)
        if geom_dict:
            building_data.append({"osm_id": b.osm_id, "name": b.name, "geometry": geom_dict})
        else:
            print(f"Warning: Malformed geometry in DITCachedBuildings {b.osm_id}. Skipping.")
            # Option to delete: b.delete()

    # Fetch roads and build graph
    G, road_data = _build_networkx_graph_from_cached_roads(CachedRoad.objects.all())
    print(f"Graph in university_blocks_roads built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

    # Get start and end coordinates from query parameters
    start_lat = request.GET.get("start_lat")
    start_lng = request.GET.get("start_lng")
    end_lat = request.GET.get("end_lat")
    end_lng = request.GET.get("end_lng")

    shortest_path_geojson = None

    if start_lat and start_lng and end_lat and end_lng:
        try:
            if not G.nodes():
                print("Error calculating shortest path: Graph is empty (no valid roads processed).")
            else:
                start_point = ShapelyPoint(float(start_lng), float(start_lat))
                end_point = ShapelyPoint(float(end_lng), float(end_lat))
                
                graph_nodes_shapely = ShapelyMultiPoint([ShapelyPoint(node) for node in G.nodes()])

                _, nearest_start_shapely = nearest_points(start_point, graph_nodes_shapely)
                _, nearest_end_shapely = nearest_points(end_point, graph_nodes_shapely)

                nearest_start_node_tuple = tuple(nearest_start_shapely.coords[0])
                nearest_end_node_tuple = tuple(nearest_end_shapely.coords[0])

                if nearest_start_node_tuple not in G or nearest_end_node_tuple not in G:
                    print(f"Warning: One or both nearest nodes not found in graph. Start: {nearest_start_node_tuple}, End: {nearest_end_node_tuple}")
                    # This implies the points are too far from the existing graph or graph is too sparse.
                    # No path can be found in this scenario.
                else:
                    path = nx.shortest_path(G, source=nearest_start_node_tuple, target=nearest_end_node_tuple, weight="weight")
                    path_coords = [list(coord) for coord in path]
                    shortest_path_geojson = {"type": "LineString", "coordinates": path_coords}
                    print(f"Shortest path calculated with {len(path_coords)} points.")

        except nx.NetworkXNoPath:
            print("Error calculating shortest path: No path found between the given points.")
        except Exception as e:
            print(f"Error calculating shortest path in university_blocks_roads: {e}")
    
    try:
        road_data_json = json.dumps(road_data)
        building_data_json = json.dumps(building_data)
        shortest_path_json_str = json.dumps(shortest_path_geojson) if shortest_path_geojson else "null"
    except Exception as e:
        print(f"Error serializing data for template in university_blocks_roads: {e}")
        return render(request, "error.html", {"message": "Error preparing map data for display."})

    return render(request, "university_blocks_roads.html", {
        "road_data_json": road_data_json,
        "building_data_json": building_data_json,
        "shortest_path_json": shortest_path_json_str
    })


def index(request):
    """
    View to render the index page for QR code scanning.
    """
    return render(request, "index.html")