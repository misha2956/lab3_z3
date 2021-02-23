import sys
import folium
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from flask import Flask, render_template, request

app = Flask(__name__)

def get_user_friends_locations_list(
        bearer_token: str, screen_name: str, friends_num: int=50
    ) -> list:
    """
    This function gets user's friends list consisting of name-location pairs.
    """
    base_url = 'https://api.twitter.com/'
    search_headers = {
        'Authorization': f'Bearer {bearer_token}'
    }
    search_params = {
        'screen_name': f'{screen_name}',
        'count': friends_num
    }
    search_url = f'{base_url}1.1/friends/list.json'
    response = requests.get(
        search_url, headers=search_headers, params=search_params
    )

    data = response.json()

    return [
        (user['name'], user['location'])
        for user in data['users']
        if len(user['location']) != 0
    ]


def get_friends_coordinates(friends_locations_list: list, geocode) -> list:
    """
    This function returns a modified list with coordinates
    instead of places' names.
    """
    friends_coordinates_list = []
    for user, location_str in friends_locations_list:
        match_location = geocode(location_str)
        if match_location is not None:
            friends_coordinates_list.append((user, (
                match_location.latitude, match_location.longitude
            )))
    return friends_coordinates_list


def generate_html(
        friends_coordinates_list: list, out_file: str='map.html',
        render_into_str: bool=False
    ):
    """
    This function generates the html file of a map or puts it into a str.
    """
    page_map = folium.Map(titles="OpenStreetMap")
    friends_featuregroup = folium.FeatureGroup(name="Twitter friends")

    for friend_str, (match_lat, match_lon) in friends_coordinates_list:
        friends_featuregroup.add_child(folium.Marker(
            location=[match_lat, match_lon],
            popup=folium.Popup(folium.Html(
                friend_str
            ), min_width=100, max_width=100),
            icon=folium.Icon(color="red")
        ))
    
    page_map.add_child(friends_featuregroup)
    if not render_into_str:
        page_map.save(out_file)
        return None
    else:
        return page_map.get_root().render()


def main():
    """
    This function runs the map generator in the terminal.
    """

    if len(sys.argv) != 2:
        print(f'Usage:\n {sys.argv[0]} BEARER_TOKEN')

    geolocator = Nominatim(user_agent="Twitter friends locator.")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    bearer_token = sys.argv[1]
    username = input("Please enter user's @tag: @")  # liverpooloneluv
    friends_num = ''
    while not friends_num.isnumeric():
        friends_num = input('Please enter the number of friends: ')
    friends_num = int(friends_num)

    generate_html(get_friends_coordinates(get_user_friends_locations_list(
        bearer_token, username, friends_num=friends_num
    ), geocode))


@app.route("/")
def main_page():
    """
    This function renders the main page
    """
    return render_template("main_page.html")


@app.route("/map", methods=["POST"])
def map_page():
    """
    This function renders the map.
    """
    try:
        username = request.form.get("username")
        bearer_token = request.form.get("bearer_token")
        friends_num = request.form.get("friends_num")

        if any([not token for token in [
            username, bearer_token
        ]]):
            return render_template("failure.html")
        if not friends_num:
            friends_num = 50

        geolocator = Nominatim(user_agent="Twitter friends locator.")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

        # generate map html
        page_str = generate_html(
            get_friends_coordinates(get_user_friends_locations_list(
                bearer_token, username, friends_num=friends_num
            ), geocode),
            render_into_str=True
        )

        return page_str
    except KeyError:
        return render_template("failure.html")


if __name__ == "__main__":
    app.run(debug=False)
