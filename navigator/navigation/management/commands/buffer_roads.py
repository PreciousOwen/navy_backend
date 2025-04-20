from django.core.management.base import BaseCommand
from navigation.models import Road, BufferedRoad

class Command(BaseCommand):
    help = "Buffer road centerlines to create road polygons"

    def handle(self, *args, **kwargs):
        buffer_size = 0.005  # Increase buffer size for better visibility

        # Clear existing buffered roads
        BufferedRoad.objects.all().delete()

        # Buffer each road and save as a polygon
        for road in Road.objects.all():
            if road.geom:
                buffered_geom = road.geom.buffer(buffer_size)  # Create a buffer around the centerline
                buffered_geom.srid = 3857  # Assume the data is in EPSG:3857 (Web Mercator)
                buffered_geom_4326 = buffered_geom.transform(4326, clone=True)  # Transform to WGS84
                BufferedRoad.objects.create(name=road.name, geom=buffered_geom_4326)
                self.stdout.write(f"Buffered road: {road.name}, Geometry: {buffered_geom_4326.wkt}")

        self.stdout.write("Road buffering completed.")
