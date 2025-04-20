import polyline
import folium

# Encoded polyline from the JSON response
encoded_polyline = "_rnwFbfubMDLBLJt@BH@@B?@ALECMACCKCKKi@AMCK?MAM?K@M@M@KBMDMFKPa@FMDMDOBIJg@Le@FSJSDKFMJSX_@fKkNl@y@zi@{t@xAmB^e@rAgB`@i@`@m@VWJMFGFGHEFEDAHCHAH?J?H?J@JDJDDBBFDF@FBFBJ?J?LAHAHCJCFEFGDEBIDI@QEOKMIq@WCACCCEEGCK?c@@aA?I@S?QDkD?Q?OBmA@oA?O?MB_BBgA?I?O?C@GJGx@a@LG`@SDABADAD?@i@Hk@Fc@F_@H]H[HYLYJUNYNWJSrA{B^o@PYR_@P_@vEgF\\a@HKTUXa@Ta@LWLWFSHUJ]H]F_@F]De@De@Bk@@i@BkABiBBcBFyBzAkiA?o@E_A]iCQs@IYKWO_@S]Yc@]a@[]]Y]S]QaAa@yAY_ASeEy@iB_@}@Y_EsAoB{@cAc@_FgC}BeAmFgC{JuE_By@uG}CIEaAe@MIaDkBqAu@_B_As@c@aH_EaAo@aAs@y@u@_@_@oDsDeBwBoBkCiBuCaBoCsFuJgEwHs@uBIWI[GQESEMSmAEOGOEMEIGIGIIIGGKGKGGCGCGAECIAIOsC_GIMIOc@cAMWMWKSACIQIOGKMQk@}@[i@OYk@EMJKDQBkBPoALM@K@oDZiE`@aBNK@O@wIv@M@QB_Hl@{@HkCVA?aAJw@F_CRG@aCR_AFUBQuBEa@CSCWCWG[EYGYGYIWWeAk@{B[iAIYIWKWKWQe@o@}Ae@kAUQ^g@@AjAkAJK`AaAnBqBh@g@XY^_@n@q@n@o@FIFIFIpCuELNfBvB"

# Decode the polyline to get a list of latitude/longitude points
route_coordinates = polyline.decode(encoded_polyline)

# Define the start and end waypoints
start_location = [40.712156, -74.005615]  # Centre Street
end_location = [40.730451, -73.935001]  # Railroad Avenue

# Create a map centered at the start location
route_map = folium.Map(location=start_location, zoom_start=13)

# Add the route to the map
folium.PolyLine(route_coordinates, color="blue", weight=5, opacity=0.7).add_to(route_map)

# Add markers for start and end points
folium.Marker(start_location, popup="Start: Centre Street", icon=folium.Icon(color="green")).add_to(route_map)
folium.Marker(end_location, popup="End: Railroad Avenue", icon=folium.Icon(color="red")).add_to(route_map)

# Save map to an HTML file
route_map.save("route_map.html")
print("Map saved as route_map.html. Open it in your browser.")
