"""
Make sure you have added info to spotify.py
Have downloaded YOUR_CLIENT_SECRET_FILE.json
"""
import requests
import sys
import youtube_dl
import json

import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import copy
import pickle
import shelve
from spotify import spotify_token, spotify_user_id




    
def get_youtube_client():
    """
    #THIS PART IS ALL TAKEN FROM GOOGLE API DOCS
    #https://developers.google.com/youtube/v3/docs/playlists/list?apix=true#request-body
    # -*- coding: utf-8 -*-

    # Sample Python code for youtube.playlists.list
    # See instructions for running these code samples locally:
    # https://developers.google.com/explorer-help/guides/code_samples#python

    """
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)
    
    return youtube

def get_playlist_id_from_youtube(my_playlist_name,youtube):
    """
    Get id of the playlist 'my_playlist_name' from youtube

    Parameters:
    my_playlist_name(str): raw name
    youtube: youtube client see get_youtube_client function

    Returns:
    str:id

    Future:
    
    """
    playlist_id=None
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        maxResults=10,
        mine=True
    )
    response = request.execute() #Returns a dict
    #dict_keys(['kind', 'etag', 'pageInfo', 'items'])

    for item in response["items"]:
        if item['snippet']['title']==my_playlist_name:
            playlist_id=item['id']

    return  playlist_id    

def get_list_of_songs_from_youtube_playlist(my_playlist_name,youtube,playlist_id_from_youtube):
    """
    Get all the video titles and their urls and save to a json file (playlist_name.json) and
    also saves a <my_playlist_name>.json file locally to use for other purposes

    Parameters:
    my_playlist_name(str): raw name
    youtube: youtube client see get_youtube_client function

    Returns:
    video_titles_and_urls(dictionaries in list): e.g.
    [{
        "title":"Jay-Z feat. Mr Hudson Forever Young Official Music Video and Lyrics"
        "youtube_url":"https://www.youtube.com/watch?v=m1_EDno-44M"
    }]

    Future:
    """
    video_titles_and_urls=[]
    output_file_name="{}.json".format(my_playlist_name)

    #GET Songs from the first page
    request = youtube.playlistItems().list(
    part="snippet",
    maxResults=50,
    playlistId=playlist_id_from_youtube,
    )
    response = request.execute()

    print("Total Songs in \""+my_playlist_name+"\" are "+str (response["pageInfo"]["totalResults"])+"\n")
    #dict_keys(['kind', 'etag', 'nextPageToken', 'items', 'pageInfo'])
    for item in response["items"]:
        title=item['snippet']['title']
        youtube_url= "https://www.youtube.com/watch?v={}".format(item['snippet']['resourceId']['videoId'])   
        video_titles_and_urls.append({"title":title,"youtube_url":youtube_url})

    #write to a file
    with open(output_file_name,'w') as f:
        json.dump(video_titles_and_urls , f)
    
    #GET REST OF THE PAGES
    while "nextPageToken" in response.keys():
        nextPageToken=response['nextPageToken']
        
        request = youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=playlist_id_from_youtube,
        pageToken=nextPageToken
        )
        response = request.execute()

        for item in response["items"]:
            title=item['snippet']['title']
            youtube_url= "https://www.youtube.com/watch?v={}".format(item['snippet']['resourceId']['videoId'])   
            video_titles_and_urls.append({"title":title,"youtube_url":youtube_url})

    #write to a file
    with open(output_file_name,'a') as f:
            json.dump(video_titles_and_urls , f)
        

    return  video_titles_and_urls    

def get_names_from_YoutubeDL(list_of_songs_from_youtube_playlist):
    """
    Take video titles and extracts artist and song names.

    Parameters:
    list_of_songs_from_youtube_playlist(dictionaries in list):[{title:url},{},{}...] 

    Returns: Dictionaries in list
    each dictionary has
    {
                "title"=title
                "youtube_url"=youtube_url
                "song_name": song_name,
                "artist": artist,
                "spotify_uri":None,
                "all_info":None
    }

    spotify_uri and all_info, fields are initialsed to None
    If song_name and artist names are nor found than they are set to None as well

    dumps all of the info in temp_dictionary.json locally as well
    Future:
    """
    temp_dictionary = copy.deepcopy(list_of_songs_from_youtube_playlist)

    for dictionary in temp_dictionary:
        title=dictionary["title"] 
        youtube_url=dictionary["youtube_url"] 
        try :
            # use youtube_dl to collect the song name & artist name
            video = youtube_dl.YoutubeDL({}).extract_info(
                youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]
        except:
            song_name = None
            artist = None

        dictionary.update({
                "song_name": song_name,
                "artist": artist,
                "spotify_uri":None,
                "all_info":None
            })

    with open("temp_dictionary.json",'w') as f:
        json.dump(temp_dictionary , f)
    return temp_dictionary

def get_spotify_uris_to_add(names_from_YoutubeDL): 
    """
    Search songs on spotify using 'song_name' and update 'spotify_uri' & 'all_info'
    First result result is added

    Parameters:
    def get_spotify_uris_to_add(names_from_YoutubeDL): (dictionaries in list):
    each dictionary has
    {
                "title"=title
                "youtube_url"=youtube_url
                "song_name": song_name,
                "artist": artist,
                "spotify_uri":None,
                "all_info":None
    }

    Returns: Dictionaries in list
    each dictionary has
    {
                "title"=title
                "youtube_url"=youtube_url
                "song_name": song_name,
                "artist": artist,
                "spotify_uri":spotify_uri,
                "all_info":all_info
    }

    dumps all of the info in final_dictionary.json locally as well


    Future:
    """
    final_dictionary = copy.deepcopy(names_from_YoutubeDL)
    spotify_uri=None
    all_info=None 
    total=0 # total songs in YT playlits
    added=0 # total corresponding songs that are found in spotify, that will be added
    total=total+1
    
    for dictionary in final_dictionary:
        total=total+1   
        if dictionary['song_name'] is not None :
            song_name=dictionary['song_name']  
            song_info_from_spotify=get_song_info_from_spotify(song_name)
            
            try:
                all_info=song_info_from_spotify["tracks"]["items"][0] 
                spotify_uri=all_info['uri'] 
                added=added+1 
            except :
                pass
            
        # add the uri, easy to get song to put into playlist
        dictionary["spotify_uri"]=spotify_uri
        dictionary["song_info_from_spotify"]=all_info

        
    print("{} out of {} songs found on spotify".format(added,total))
    with open("final_dictionary.json",'w') as f:
        json.dump(final_dictionary , f)
    return final_dictionary

def add_song_to_playlist(spotify_playlist_id,spotify_uris_to_add):
    """
    Add songs to our playlist (spotify_playlist_id) using uris in (spotify_uris_to_add)
    We can only add 100 songs at a time, so post request well be made multiple times
    

    Parameters:
    spotify_playlist_id(str): id of playlist on spotify
    spotify_uris_to_add: we will extract all uris from it

    Returns: response_json

    Future:
    """
    
    print("Adding songs")
    
    all_uris=[dictionary['spotify_uri'] for dictionary in spotify_uris_to_add if dictionary['spotify_uri']!=None]
    # create a new playlist
    interations=len(all_uris)//100+1 #Only hundread songs can be added at a time
    # add all songs into new playlist

    all_uris=list(set(all_uris))
    print(len(all_uris))

    for i in range(5):

        start=100*i
        end=100*(i+1)
        batch_of_hundred=all_uris[start:end]
        request_data = json.dumps(batch_of_hundred)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            spotify_playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

    print("Songs added")
    response_json = response.json()
    return response_json

def get_spotify_playlist_id(my_playlist_name):
    """
    Create a new playlist in spotify named "From Youtube <my_playlist_name>"
    

    Parameters:
    my_playlist_name(str): Set name for the new playlist

    Returns: id of the new playlist 

    Future:
    """
    request_body = json.dumps({
        "name": "From Youtube {}".format(my_playlist_name),
        "description": "From Youtube {}".format(my_playlist_name),
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
    # playlist id
    return response_json['id']

def get_song_info_from_spotify(song_name):
        """
        Search "song_name" on spotify and fetch the first result
        
        Parameters:
        song_name(str): Song name to search for

        Returns:
        #dict_keys(['album', 'artists', 'available_markets', 'disc_number', 'duration_ms',
        #  'explicit', 'external_ids', 'external_urls', 'href', 'id', 'is_local', 'name',
        #  'popularity', 'preview_url', 'track_number', 'type', 'uri'])

        We will use uri to add these songs in our playlist

        Future:
        """
        query = "https://api.spotify.com/v1/search?q={}&type=track&limit=2".format(
            song_name
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        #dict_keys(['album', 'artists', 'available_markets', 'disc_number', 'duration_ms',
        #  'explicit', 'external_ids', 'external_urls', 'href', 'id', 'is_local', 'name',
        #  'popularity', 'preview_url', 'track_number', 'type', 'uri'])

        return response_json

def put_in_a_shelve(name,data):
    """
    Use to save objects during debugging so you dont have to rerun all functions each time
    key=name
    value=data
    """
    with shelve.open('shelve.db') as db:
        db[name] = data

if __name__ == '__main__':
    """
    Either give playlist name as a 1st argumnet like
    python3 add_songs.py "All time Favourite"

    or give name in except below
    default name is; my_playlist_name="All time Favourite"


    TIPS:
    To debug or modify code save previous objects using shelve function 'put_in_a_shelve(name,data)'
    Load previous data from their and just debug where ever you are stuck
    """
    try:
        my_playlist_name=sys.argv[1]
    except:
        my_playlist_name="All time Favourite"
        

    #Get Youtube client
    youtube=get_youtube_client()
    #Create playlist and get its id from spotify
    spotify_playlist_id=get_spotify_playlist_id(my_playlist_name)
    #Save these variables so we dont have to authorise permission from Google each time we run it 
    # with shelve.open('shelve.db') as db:
    #     db["youtube"] = youtube
    #     db["spotify_playlist_id"]=spotify_playlist_id
    #Get playlist id from youtube
    playlist_id_from_youtube=get_playlist_id_from_youtube(my_playlist_name,youtube)
    # List of all videos from youtube playlist
    list_of_songs_from_youtube_playlist=get_list_of_songs_from_youtube_playlist(my_playlist_name,youtube,playlist_id_from_youtube)
    # fetch song and artist names from youtube videos using their youtube urls
    names_from_YoutubeDL=get_names_from_YoutubeDL(list_of_songs_from_youtube_playlist)   
    # fetch spotify uris of the corresponding youtube songs using names
    spotify_uris_to_add=get_spotify_uris_to_add(names_from_YoutubeDL)
    # add songs to spotify playlist using song's uro
    add_song_to_playlist(spotify_playlist_id,spotify_uris_to_add)

    
 




