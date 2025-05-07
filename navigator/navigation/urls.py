from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import fetch_destinations
from django.views.generic import TemplateView

urlpatterns = [
    # Route for the index page
    path('', views.index, name='index'),

    # Route for generating a route
    path('generate_route/', views.generate_route, name='generate_route'),

    # Route for viewing the map with roads
    path('map/', views.map_view, name='map_view'),

    # Route for viewing green roads
    # path('map_green/', views.map_view_green, name='map_view_green'),

    # Route for viewing road polygons
    path('map_polygons/', views.map_view_polygons, name='map_polygons'),

    # Route for viewing buildings and roads together
    path('map_new_polygons/', views.map_new_polygons, name='map_new_polygons'),

    # Route for viewing roads
    path('map_roads/', views.map_roads, name='map_roads'),

    # Route for viewing nodes
    path('map_nodes/', views.map_nodes, name='map_nodes'),

    # Route for viewing university roads
    path('university_roads/', views.university_roads, name='university_roads'),

    # Route for viewing university blocks
    path('university_blocks/', views.university_blocks, name='university_blocks'),

    # Route for viewing university blocks and roads
    path('university_blocks_roads/', views.university_blocks_roads, name='university_blocks_roads'),

    # URL for adding a path
    path('add_path/', views.add_path, name='add_path'),

    # URL for removing paths
    path('remove_paths/', views.remove_paths, name='remove_paths'),

    # URL for fetching destinations
    path('fetch_destinations/', fetch_destinations, name='fetch_destinations'),

    # Intro page
    path('intro/', TemplateView.as_view(template_name="intro.html"), name='intro'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
