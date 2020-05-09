import requests
import sys
import youtube_dl
import json

import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import copy

from secrets import spotify_token, spotify_user_id

class createPlaylist():

    def __init__(self,my_playlist_name):
        """
        Make a youtube client 
        Set the name of a playlist that this object will use
        """
        self.youtube = self.get_youtube_client()
        self.my_playlist_name=my_playlist_name
        
    def get_youtube_client(self):
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

    def get_playlist_id(self):
        """
        Get id of a playlist 
        We pass in the name when creating the object
        For example
        my_playlist_name="All time Favourite"
        myclass = get_Songs_From_Google_Playlist(my_playlist_name)
        """
        
        request = self.youtube.playlists().list(
            part="snippet,contentDetails",
            maxResults=10,
            mine=True
        )
        response = request.execute() #Returns a dict
        #dict_keys(['kind', 'etag', 'pageInfo', 'items'])

        for item in response["items"]:
            if item['snippet']['title']==self.my_playlist_name:
                playlist_id=item['id']

        return  playlist_id    

    def get_list_of_songs_from_playlist(self):
        """
        Get all the song titles and their urls and save to a json file (playlist_name.json)
        {
            "title":"Jay-Z feat. Mr Hudson Forever Young Official Music Video and Lyrics"
            "youtube_url":"https://www.youtube.com/watch?v=m1_EDno-44M"
        }
        """
        my_playlist_id =self.get_playlist_id()
        video_titles_and_urls=[]
        output_file_name="{}.json".format(self.my_playlist_name)

        #GET Songs from the first page
        request = self.youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=my_playlist_id,
        )
        response = request.execute()

        print("Total Songs in \""+self.my_playlist_name+"\" are "+str (response["pageInfo"]["totalResults"])+"\n")
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
            
            request = self.youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=my_playlist_id,
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

    def clean_names(self):
        
        video_titles_and_urls =self.get_list_of_songs_from_playlist()
        temp_dictionary = copy.deepcopy(video_titles_and_urls)

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

    def get_final_dictinary(self): 
        final_dictionary = copy.deepcopy(self.clean_names())   
        
        for dictionary in final_dictionary:
            if dictionary['song_name'] is not None :
                song_name=dictionary['song_name']
                # save all important info and skip any missing song and artist
                #dict_keys(['album', 'artists', 'available_markets', 'disc_number', 'duration_ms',
                #  'explicit', 'external_ids', 'external_urls', 'href', 'id', 'is_local', 'name',
                #  'popularity', 'preview_url', 'track_number', 'type', 'uri'])
                # song_info_from_spotify["tracks"]["items"][0]
                

                try:
                    song_info_from_spotify=self.get_song_info_from_spotify(song_name)
                    all_info=song_info_from_spotify["tracks"]["items"][0]
                    spotify_uri=all_info['uri']       
                except :
                    spotify_uri=None
                    all_info=None

                dictionary.update({
                    
                    # add the uri, easy to get song to put into playlist
                    "spotify_uri": spotify_uri,
                    "song_info_from_spotify":all_info
                })

        with open("final_dictionary.json",'w') as f:
            json.dump(final_dictionary , f)
        return final_dictionary

    def add_song_to_playlist(self):
        final_dictionary=self.clean_names()
        with open("final_dictionary.json",'w') as f:
            json.dump(final_dictionary , f)

        all_uris=[dictionary['spotify_uri'] for dictionary in final_dictionary if dictionary['spotify_uri']!=None]
        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(all_uris)
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        response_json = response.json()
        return response_json
            

    def create_playlist(self):
        """Create A New Playlist"""
        request_body = json.dumps({
            "name": "{} from Youtube".format(self.my_playlist_name),
            "description": "{} from Youtube".format(self.my_playlist_name),
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
        return response_json["id"]

    def get_song_info_from_spotify(self, song_name):
            """Search For the Song"""
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

if __name__ == '__main__':
    """
    Either give playlist name as a 1st argumnet like
    python3 youtube.py "All time Favourite"

    or give name in except below
    default name is "All time Favourite"
    Change my_playlist_name as per need
    """
    # try:
    #     my_playlist_name=sys.argv[1]
    #     myclass = createPlaylist(my_playlist_name)
    #     myclass.add_song_to_playlist()
    # except:
    my_playlist_name="All time Favourite"
    myclass = createPlaylist(my_playlist_name)
    myclass.add_song_to_playlist()
    

    