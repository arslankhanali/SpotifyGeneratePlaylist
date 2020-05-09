import json
import os
import requests


from secrets import spotify_token, spotify_user_id


#         #"https://api.spotify.com/v1/search?q=Muse&type=track%2Cartist&market=US&limit=10&offset=5"
# query = "https://api.spotify.com/v1/search?q={}&type=track&limit=1".format(
# #query = "https://api.spotify.com/v1/search?q=track:{}%20artist:{}&type=track&limit=1".format(
      
#             "band of funeral"
          
#         )
# response = requests.get(
#     query,
#     headers={
#         "Content-Type": "application/json",
#         "Authorization": "Bearer {}".format(spotify_token)
#     }
# )
# response_json = response.json()



# request_body = json.dumps({
#     "name": "Youtube",
# })

# query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
# response = requests.post(
#     query,
#     data=request_body,
#     headers={
#         "Content-Type": "application/json",
#         "Authorization": "Bearer {}".format(spotify_token)
#     }
# )
# response_json = response.json()
# print(response, response_json)

# playlist id
#ans= response_json["id"]
my_playlist_name="test"

"""Create A New Playlist"""
request_body = json.dumps({
    "name": "{} from Youtube".format(my_playlist_name),
    "description": "{} from Youtube".format(my_playlist_name),
    "public": True
})

query = "https://api.spotify.com/v1/users/{}/playlists".format(
    spotify_user_id)
response = requests.post(
    query,
    data=request_body,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(spotify_token)
    }
)
response_json = response.json()