import requests
import json

BASE_URL = "https://navigator.silicon4forge.org/navigation"  # Replace with your server's base URL

def add_path(coordinates, name="Unnamed Path"):
    """
    Sends a POST request to add a path to the server.
    
    :param coordinates: List of [longitude, latitude] pairs.
    :param name: Name of the path (optional).
    """
    url = f"{BASE_URL}/add_path/"
    data = {
        "coordinates": coordinates,
        "name": name
    }
    try:
        response = requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        if response.status_code == 201:
            print("Path added successfully:", response.json())
        else:
            print("Failed to add path:", response.json())
    except Exception as e:
        print(f"Error while adding path: {e}")


def remove_paths(osm_id=None):
    """
    Sends a POST request to remove paths from the server.
    
    :param osm_id: Optional. The osm_id of the path to delete. If not provided, all paths will be deleted.
    """
    url = f"{BASE_URL}/remove_paths/"
    data = {"osm_id": osm_id} if osm_id else {}
    try:
        response = requests.post(url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            print(f"Path(s) removed successfully: {response.json()}")
        else:
            print(f"Failed to remove path(s): {response.json()}")
    except Exception as e:
        print(f"Error while removing path(s): {e}")


if __name__ == "__main__":
    # Example usage
    # Add a path
    coordinates = [[39.2793, -6.8147775], [39.279369, -6.814663]]
    # add_path(coordinates, name="Example Path")

    # Remove a specific path by osm_id
    #remove_paths(osm_id=1372660163)

    # Remove all paths
    # remove_paths()
