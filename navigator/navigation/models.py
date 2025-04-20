from django.db import models

class Location(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name
    


from django.contrib.gis.db import models

class Road(models.Model):
    name = models.CharField(max_length=255, null=True)
    geom = models.LineStringField(srid=4326)  # SRID 4326 for OSM coordinates

    def __str__(self):
        return self.name or "Unnamed Road"
    

class BufferedRoad(models.Model):
    name = models.CharField(max_length=255, null=True)
    geom = models.PolygonField(srid=4326)  # Store road polygons

    def __str__(self):
        return self.name or "Unnamed Buffered Road"


class OSMPoint(models.Model):
    name = models.CharField(max_length=255)
    location = models.PointField()
    
    def __str__(self):
        return self.name


class PlanetOSMPolygon(models.Model):
    osm_id = models.BigIntegerField()
    name = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    way = models.PolygonField(srid=4326)  # Ensure SRID matches your database

    def __str__(self):
        return self.name or f"OSM Polygon {self.osm_id}"


class CachedRoad(models.Model):
    osm_id = models.BigIntegerField(unique=True)  # Unique identifier for the road
    name = models.CharField(max_length=255, null=True, blank=True)
    geometry = models.JSONField()  # Store the GeoJSON geometry as JSON

    def __str__(self):
        return self.name or f"Cached Road {self.osm_id}"



# Create your models here.

# Example of adding initial data using Django fixtures
# Create a file named initial_data.json in the navigation app directory with the following content:
# [
#     {
#         "model": "navigation.location",
#         "pk": 1,
#         "fields": {
#             "name": "Example Location",
#             "latitude": -6.166585,
#             "longitude": 39.33596
#         }
#     }
# ]

class DITCachedBuildings(models.Model):
    osm_id = models.BigIntegerField(unique=True)  # Unique identifier for the block
    name = models.CharField(max_length=255, null=True, blank=True)
    geometry = models.JSONField()  # Store the GeoJSON geometry as JSON

    def __str__(self):
        return self.name or f"Cached Block {self.osm_id}"
