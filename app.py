import json
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from flask import Flask, redirect, request, jsonify, g, session, url_for, render_template
import pandas as pd

# spotify client secret and id
# https://developer.spotify.com/dashboard
cs = os.environ['CLIENT_SECRET']
ci = os.environ['CLIENT_ID']
#redirect_url = "http://192.168.178.47:5000/callback"
redirect_url = os.environ['SERVER_CALLBACK_URL']
scope = "user-read-playback-state user-modify-playback-state playlist-read-private playlist-read-collaborative app-remote-control"


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(client_id=ci, client_secret=cs, redirect_uri=redirect_url, scope=scope, cache_handler=cache_handler)
sp = Spotify(auth_manager=sp_oauth)

@app.route('/')
def home():
    # try to get spotify authorization
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('search_playlists'))

@app.route('/callback')
def callback():
    # set spotify authorization token
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('search_playlists'))

@app.route('/search_playlists')
def search_playlists():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    # render search page
    return render_template('search_playlist.html')

@app.route('/game')
def game():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    # render game html
    playlist_id = request.args['playlist_id']
    return render_template('game.html', playlist_id=playlist_id)

@app.route('/search_data')
def search_data():
    query = request.args['query']
    result = sp.search(query, 10, 0, "playlist", "DE")
    items = list(filter(None,result["playlists"]["items"]))
    data = pd.read_json(json.dumps(items))
    data["author"] = data['owner'].apply(lambda x: x['display_name'] + " : " + x['id'])
    data["image"] = data['images'].apply(lambda x: x[0]['url'])
    df = data[["name", "id", "author", "image"]]
    return jsonify(json.loads(df.to_json(orient='records')))

@app.route('/playlist_data')
def playlist_data():
    playlist_id = request.args['playlist_id']
    # get all tracks from playlist
    track_result = sp.playlist_items(playlist_id, additional_types=('track',))
    tracks = [track["track"] for track in track_result["items"]]
    # and get as json data
    data = pd.read_json(json.dumps(tracks))
    data['year'] = data['album'].apply(lambda x: x['release_date'][:4])
    data['artist'] = data['artists'].apply(lambda x: x[0]['name'])
    df = data[["name", "artist", "year", "uri"]]
    df = df.sample(frac=1)
    return jsonify(json.loads(df.to_json(orient='records')))

@app.route('/play_song', methods=['POST'])
def play_song():
    data = request.json
    uri = data.get('uri')
    if uri:
        sp.start_playback(uris=[uri])
        return jsonify({"message": "Song is now playing."}), 200
    else:
        return jsonify({"error": "No URI provided."}), 400


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host= '192.168.178.47')