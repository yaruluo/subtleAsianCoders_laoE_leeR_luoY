'''
subtleAsianCoders - Yaru Luo, Matthew Chan, Eric "Morty" Lau, ray. lee.
SoftDev1 pd1
P02 -- The End
RYthEM
'''

# from app.utl import build_db
from flask import Flask, request, redirect, session, render_template, url_for, flash
from utl import models
from config import Config
import sqlite3
import urllib.request
import urllib.parse
import functools
import os
import random
import json
import datetime

api_file = os.path.dirname(os.path.abspath(__file__)) + '/api.json'

# TODO: remove api keys from the file after development is done

with open( api_file, 'r') as read_file:
    keys = json.load( read_file) # retrieve keys from json

SPOTIFY_CLIENT_ID = keys[ 'SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = keys[ 'SPOTIFY_CLIENT_SECRET']
MUSIXMATCH_API_KEY = keys[ 'MUSIXMATCH_API_KEY']

# SQLAlchemy DB Models
db = models.db
Song = models.Song
Album = models.Album

app = Flask(__name__)
app.config.from_object( Config)

# creates secret key for sessions
app.secret_key = os.urandom( 32)

# renders spotify api url data vis a vis ur own spotify account
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE_URL = 'https://api.spotify.com'
SPOTIFY_API_VERSION = 'v1'
SPOTIFY_API_URL = f"{SPOTIFY_API_BASE_URL}/{SPOTIFY_API_VERSION}"

CLIENT_SIDE_URL = 'http://127.0.0.1'
PORT = 5000
SPOTIFY_REDIRECT_URI = f"{CLIENT_SIDE_URL}:{PORT}/callback/q"
SPOTIFY_SCOPE = 'user-library-read user-library-modify user-top-read'

spotify_auth_query_parameters = {
    'client_id': SPOTIFY_CLIENT_ID,
    'response_type': 'code',
    'redirect_uri': SPOTIFY_REDIRECT_URI,
    'scope': SPOTIFY_SCOPE,
}

# checks if logged in to ur Spotify acc
def protected( f):
    @functools.wraps( f)
    def wrapper( *args, **kwargs):
        if 'access_token' in session:
            # if logged in, continue with expected function
            return f( *args, **kwargs)
        else:
            flash( 'You are not connected to your Spotify account', 'error')
            return redirect( url_for( 'home'))
    return wrapper

def spotify_api_query( url, method):
    authorization_header = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    req = urllib.request.Request(
        url,
        headers=authorization_header,
        method=method,
    )

    req = urllib.request.urlopen( req)

    if method == 'GET':
        res = req.read()
        data = json.loads( res)

        return data

    return None

@app.route( '/')
def home():
    return render_template(
        'home.html',
    )

@app.route( '/spotify_connect')
def spotify_connect():
    url_args = "&".join( [ f"{key}={urllib.parse.quote(val)}" for key,
                         val in spotify_auth_query_parameters.items()])
    auth_url = f"{SPOTIFY_AUTH_URL}/?{url_args}"
    return redirect( auth_url)

@app.route('/callback/q')
def callback():
    auth_token = request.args['code']
    code_payload = {
        'grant_type': 'authorization_code',
        'code': str(auth_token),
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET
    }

    post_request = urllib.request.Request(
        SPOTIFY_TOKEN_URL,
        data=urllib.parse.urlencode(code_payload).encode()
    )

    post_request = urllib.request.urlopen(post_request)
    post_request = post_request.read()

    response_data = json.loads(post_request)
    access_token = response_data['access_token']
    refresh_token = response_data['refresh_token']
    token_type = response_data['token_type']
    expires_in = response_data['expires_in']

    session['access_token'] = access_token

    get_user_name()
    get_user_top()

    return redirect(url_for('home'))

def get_user_name():
    data = spotify_api_query("https://api.spotify.com/v1/me/", 'GET')

    session['display_name'] = data['display_name']

'''
Accesses the Musixmatch API and returns the lyrics of a given song title and/or artist and/or album
'''
def musixmatch_get(title='', artist='', album=''):
    #===SEARCHING=FOR=SONG==========================
    search_request = 'https://api.musixmatch.com/ws/1.1/matcher.track.get?'
    arguments = list()
    if (len(title) != 0):
        title = 'q_track=' + urllib.parse.quote(title)
        arguments.append(title)
    if (len(artist) != 0):
        artist = 'q_artist=' + urllib.parse.quote(artist)
        arguments.append(artist)
    if (len(album) != 0):
        album = 'q_album=' + urllib.parse.quote(album)
        arguments.append(album)
    search_request += '&'.join(arguments)
    search_request += '&apikey=' + MUSIXMATCH_API_KEY
    url = urllib.request.urlopen(search_request)
    search_json = json.loads(url.read())

    track_id = search_json['message']['body']['track']['track_id']
    music_genre_list = search_json['message']['body']['track']['primary_genres']['music_genre_list']
    if(len(music_genre_list) == 0):
        genre = "No genre found!"
    else:
        genre = music_genre_list[0]['music_genre']['music_genre_name']
    print(search_json['message']['body']['track'])

    has_lyrics = search_json['message']['body']['track']['has_lyrics']
    if (has_lyrics == 1):
        #===GETTING=LYRICS==============================
        lyrics_request = 'https://api.musixmatch.com/ws/1.1/track.lyrics.get?'
        lyrics_request += 'track_id=' + str(track_id)
        lyrics_request += '&apikey=' + MUSIXMATCH_API_KEY
        # print(lyrics_request)
        url = urllib.request.urlopen(lyrics_request)
        lyrics_json = json.loads(url.read())

        lyrics = lyrics_json['message']['body']['lyrics']['lyrics_body']
    else:
        lyrics = 'LYRICS NOT AVAILABLE'

    #===FORMATTING=MUSIXMATCH=DATA==================
    data = dict()
    data['lyrics'] = lyrics
    data['genre'] = genre
    return data

def get_user_top():
    data = spotify_api_query("https://api.spotify.com/v1/me/top/tracks", 'GET')['items']

    songs = list()
    for track in data:
        track_link = track['external_urls']['spotify']
        track_data = {
            'title': track['name'],
            'artist': track['album']['artists'][0]['name'],
            'album': track['album']['name'],
            'coverArtLink': track['album']['images'][0]['url'],
            'genre': "",
            'lyrics': "",
            'popularity': track['popularity'],
            'spotify_id': track['id'],
            'iframe': f"{track_link[:25]}embed/{track_link[25:]}",
        }
        songs.append(track_data)
        # print(track_data)
        # musixmatch_track_data = musixmatch_get(title=track_data['title'], artist=track_data['artist'], album=track_data['album'])
        # print(musixmatch_track_data)
        # track_data['genre'] = musixmatch_track_data['genre']
        # track_data['lyrics'] = musixmatch_track_data['lyrics']
        # track_data['genre'] = musixmatch_track_data['genre']
        # track_data['lyrics'] = musixmatch_track_data['lyrics']
        # # print(track_data)
        # potentialAlbum = Album.query.filter_by(title=track_data['album']).first()
        # if potentialAlbum == None:
        #     albumObject = Album(title=track_data['album'], coverartlink=track_data['coverArtLink'])
        #     db.session.add(albumObject)
        #     db.session.commit()
        # album = Album.query.filter_by(title=track_data['album']).first()

    # newTrack = Song()
    session['songs'] = songs

@app.route('/higher_lower/<choice>')
def higher_lower(choice):
    if choice == 'screen':
        return render_template(
            'higherlowerscreen.html',
            )
    elif choice == 'random':
        return render_template(
            'higherlowergame.html',
            songs=session['songs'],
            choice = choice
            )
    if choice == 'favorite':
        if 'access_token' in session:
            return render_template(
                'higherlowergame.html',
                songs=session['songs'],
                choice = choice
            )
        else:
            flash( 'You are not connected to your Spotify account', 'error')
            return redirect(url_for('home'))

@protected # openable if connected
@app.route("/save_song/<song_id>")
def save_song( song_id):

    spotify_api_query( f"https://api.spotify.com/v1/me/tracks?ids={song_id}", 'PUT')

    return redirect( url_for( 'hearted_songs'))

@protected
@app.route("/hearted_songs")
def hearted_songs():

    data = spotify_api_query("https://api.spotify.com/v1/me/tracks?limit=10", 'GET')

    return render_template(
        "hearted_songs.html",
        data = data['items'],
    )

@protected
@app.route("/playlists")
def playlists():
    data = spotify_api_query("http://api.spotify.com/v1/me/playlists?limit=50", 'GET')

    return render_template(
        "playlists.html",
        data = data['items'],
    )

@protected
@app.route('/artists')
def artists():
    rand = random.randrange(0, 100)
    data = spotify_api_query(f"http://api.spotify.com/v1/search?q=year:0000-9999&type=artist&offset={rand}", 'GET')

    return render_template(
        'test.html',
        data = data['artists']['items']
    )

@app.route('/logout')
def logout():
    session['access_token'] = None
    session['display_name'] = None
    return redirect(url_for('home'))

if __name__ == '__main__':
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.run(
        debug=True,
        threaded=True
        )
