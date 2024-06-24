import base64
import auth
import requests
from flask import Flask, redirect, request, render_template, session, jsonify, make_response
import random
import string
import urllib.parse
from datetime import datetime
import html
from googleapiclient.http import MediaFileUpload
from oauthlib.oauth2 import WebApplicationClient
from pytube import YouTube, Search
import os
import subprocess
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

google_client_id = auth.GOOGLE_CLIENT_ID
google_client_secret = auth.GOOGLE_CLIENT_SECRET
google_redirect_uri = auth.GOOGLE_REDIRECT
google_client = WebApplicationClient(google_client_id)

google_auth_url = "https://accounts.google.com/o/oauth2/auth"
google_token_url = "https://oauth2.googleapis.com/token"
google_user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"


app = Flask(__name__)
app.secret_key = 'Sup3rS3cr37k3y'
spotify_client_id = auth.SPOTIFY_CLIENT_ID
spotify_client_secret = auth.SPOTIFY_CLIENT_SECRET
spotify_redirect_uri = auth.SPOTIFY_REDIRECT
port = 3000


class Track:
    def __init__(self, name, artist, artist_id, album, album_id, duration, year, id, explicit, image):
        self.name = name
        self.artist = artist
        self.artist_id = artist_id
        self.album = album
        self.album_id = album_id
        self.duration = duration
        self.year = year
        self.id = id
        self.explicit = explicit
        self.image = image
        self.genre = ""
        self.mood = ""
        self.label = ""
        self.to_add = True

    def encoder(self):
        if isinstance(self, Track):
            return {
                'name': self.name,
                'artist': self.artist,
                'artist_id': self.artist_id,
                'album': self.album,
                'album_id': self.album_id,
                'duration': self.duration,
                'year': self.year,
                'id': self.id,
                'explicit': self.explicit,
                'image': self.image,
                'genre': self.genre,
                'mood': self.mood,
                'label': self.label,
                'to_add': self.to_add
            }
        return self


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', id='404')


@app.route('/error')
def error():
    id = request.args.get('id', '0')
    return render_template('error.html', id=id)


@app.route('/')
def login_check():
    print("login_check")
    return render_template('login.html')


@app.route('/begin-login')
def google_login():
    print("session check")
    for key in list(session.keys()):
        print(key)
    google_oauth_params = {
        'redirect_uri': google_redirect_uri,
        'scope': 'openid'
                 ' email'
                 ' https://www.googleapis.com/auth/spreadsheets'
                 ' https://www.googleapis.com/auth/userinfo.profile'
                 ' https://www.googleapis.com/auth/drive',
        'state': 'google'
    }
    google_oauth_url = google_client.prepare_request_uri(google_auth_url, **google_oauth_params)
    return redirect(google_oauth_url)


@app.route('/google-callback')
def google_callback():
    print("google callback")
    print(request)
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    if error or state is None:
        return render_template('error.html', id='google-callback')
    else:
        token_params = {
            'code': code,
            'client_id': google_client_id,
            'client_secret': google_client_secret,
            'redirect_uri': google_redirect_uri,
            'grant_type': 'authorization_code'
        }
        response = requests.post(google_token_url, data=token_params)
        if response.status_code == 200:
            google_access_token = response.json()['access_token']
            session['google_access_token'] = google_access_token
            google_user_info_response = requests.get(google_user_info_url, headers={'Authorization': 'Bearer ' + google_access_token})
            user_info = google_user_info_response.json()
            session['first_name'] = user_info['given_name']
            session['last_name'] = user_info['family_name']
            return redirect('/spotify-login')
        else:
            return redirect('error?id=google-callback')


@app.route('/spotify-login')
def spotify_login():
    state = ''
    for x in range(16):
        y = (random.choice(string.ascii_uppercase + string.digits))
        state += y
    scope = 'user-read-private user-read-email playlist-read-private'
    spotify_authorize_url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
        'response_type': 'code',
        'client_id': spotify_client_id,
        'scope': scope,
        'redirect_uri': spotify_redirect_uri,
        'state': state
    })
    return redirect(spotify_authorize_url)


@app.route('/spotify-callback')
def callback():
    print('spotify-callback')
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    if error or state is None:
        return redirect('/error?id=spotify-callback')
    else:
        auth_options = {
            'url': 'https://accounts.spotify.com/api/token',
            'form': {
                'code': code,
                'redirect_uri': spotify_redirect_uri,
                'grant_type': 'authorization_code',
            },
            'headers': {
                'content-type': 'application/x-www-form-urlencoded',
                'Authorization': 'Basic ' + base64.b64encode(bytes(spotify_client_id + ':' + spotify_client_secret, 'utf-8')).decode()
            }
        }

    response = requests.post(auth_options['url'], data=auth_options['form'], headers=auth_options['headers'])

    if response.status_code == 200:
        spotify_access_token = response.json()['access_token']
        session['spotify_access_token'] = spotify_access_token
        user_data = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
        # playlists = requests.get('https://api.spotify.com/v1/me/playlists?limit=20', headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
        # print(playlists)
        session['user_name'] = user_data['display_name']
        # session['playlists'] = playlists
        return redirect('index')
    else:
        return redirect('/error?id=spotify-callback')


@app.route('/index')
def index():
    spotify_access_token = session.get('spotify_access_token')
    print(spotify_access_token)
    if spotify_access_token is None:
        return redirect('login')
    user_name = session.get('user_name')
    playlists = requests.get('https://api.spotify.com/v1/me/playlists?limit=20&',
                             headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
    if playlists.get('error'):
        print('error redirect')
        return redirect('error?id=playlists')
    print(len(playlists['items']))
    return render_template('index.html',
                           user_name=user_name, data=[0, playlists])


@app.route('/additional-playlists')
def additional_playlists():
    spotify_access_token = session.get('spotify_access_token')
    print(spotify_access_token)
    page = request.args.get('page')
    if page is None:
        print('page is none')
    if spotify_access_token is None:
        print('no spotify_access_token', page)
        return redirect('error?id=playlists')
    playlists = requests.get('https://api.spotify.com/v1/me/playlists?limit=20&offset=' + str(int(page)*20),
                             headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
    # print(playlists)
    if playlists.get('error'):
        print('additional-playlists fetch error')
        return redirect('error?id=playlists')
    return jsonify([
        page,
        playlists
    ])


@app.route('/playlist')
def playlist():
    id = request.args.get('id')
    spotify_access_token = session.get('spotify_access_token')
    if spotify_access_token:
        playlist = requests.get('https://api.spotify.com/v1/playlists/'
                                + id, headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
        print(playlist)
        trackset = tracks_to_trackset('https://api.spotify.com/v1/playlists/'
                                      + id + '/tracks?limit=20')
        if playlist.get('error'):
            return redirect('error?id=playlist')
        print(len(trackset))
        return render_template('playlist.html', playlist=playlist, data=[0, trackset])
    else:
        return redirect('error?id=playlist')


def tracks_to_trackset(endpoint):
    spotify_access_token = session.get('spotify_access_token')
    tracks = requests.get(endpoint,
                          headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
    trackset = []
    print(playlist)
    if tracks.get('error'):
        return redirect('error?id=playlist')
    for x in tracks.get('items'):
        print(x)
        t = Track(x['track']['name'], x['track']['artists'][0]['name'],
                  x['track']['artists'][0]['id'], x['track']['album']['name'],
                  x['track']['album']['id'], x['track']['duration_ms'],
                  x['track']['album']['release_date'],
                  x['track']['id'], x['track']['explicit'],
                  x['track']['album']['images'][0]['url'])
        trackset.append(t.encoder())
    for x in trackset:
        print(x['name'])
        print(x['album'])
        print(x['duration'])
        print(x['year'])
        print(x['duration'])
        print(x['id'])
        print('________')
    return trackset


@app.route('/additional-playlist')
def additional_playlist_info():
    id = request.args.get('id')
    page = request.args.get('page')
    print(page)
    if page is None:
        return redirect('error?id=playlist')
    spotify_access_token = session.get('spotify_access_token')
    if spotify_access_token:
        playlist = requests.get('https://api.spotify.com/v1/playlists/'
                                + id, headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
        trackset = tracks_to_trackset('https://api.spotify.com/v1/playlists/'
                                      + id + '/tracks?limit=20&offset=' + str(int(page)*20))
        if int(page) > (int(playlist['tracks']['total']) / 20):
            return redirect('error?id=playlist')
        print(page)
        return jsonify([
            page,
            trackset
        ])


@app.route('/edit-sheets', methods=['POST'])
def edit_sheets():
    google_access_token = session.get('google_access_token')
    creds = Credentials(google_access_token)
    data = request.get_json()
    spreadsheet = data['body'][1]
    # spreadsheet = "WNYO Song Submission Logbook 2023-24"
    trackset = data['body'][0]
    identify_moods(trackset)
    identify_genres(trackset)
    id = find_file(spreadsheet, 'application/vnd.google-apps.spreadsheet')
    update_requests = []
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets().values().get(spreadsheetId=id, range=f"Sheet1!A:A").execute()
        index = len(sheet.get('values'))
        for track in trackset:
            if track['to_add'] == 'True':
                update_requests.append(
                    {
                        "updateCells": {
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"stringValue": f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}"}},
                                        {"userEnteredValue": {"stringValue": f"{session.get('first_name')} {session.get('last_name')}"}},
                                        {"userEnteredValue": {"stringValue": html.unescape(track['name'])}},
                                        {"userEnteredValue": {"stringValue": html.unescape(track['artist'])}},
                                        {"userEnteredValue": {"stringValue": html.unescape(track['album'])}},
                                        {"userEnteredValue": {"stringValue": "{:d}:{:02d}".format(int(int(track['duration'])/60000), int((int(track['duration'])%60000)/1000))}},
                                        {"userEnteredValue": {"stringValue": track['year']}},
                                        {"userEnteredValue": {"boolValue": track['explicit']}},
                                        {"userEnteredValue": {"stringValue": track['genre']}},
                                        {"userEnteredValue": {"stringValue": track['mood']}},
                                        {"userEnteredValue": {"stringValue": 'O- Multiple/Feature/Instrumental'}},
                                        {"userEnteredValue": {"stringValue": track['label']}}
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue",
                            "start": {
                                "sheetId": 0,
                                "rowIndex": index,
                                "columnIndex": 0
                            }
                        }
                    }
                )
                index += 1
        response = (
            service.spreadsheets()
            .batchUpdate(spreadsheetId=id, body={"requests": update_requests})
            .execute()
        )
        print('response')
        print(response)
        return jsonify({'message': 'successful'})
    except Exception as e:
        print(e)
        return jsonify({'message': 'error'})


def identify_genres(trackset):
    spotify_access_token = session.get('spotify_access_token')
    album_request = ''
    artist_request = ''

    for track in trackset:
        album_request += track['album_id'] + '%2C'
        artist_request += track['artist_id'] + '%2C'
    artist_response = requests.get('https://api.spotify.com/v1/artists?ids='
                                   + artist_request[:-3],
                                   headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
    album_response = requests.get('https://api.spotify.com/v1/albums?ids='
                                  + album_request[:-3],
                                  headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
    if artist_response.get('error') or album_response.get('error'):
        return redirect('error?id=genre')
    genres = ['Alternative', 'Classic Rock', 'Electronic', 'Rock',
              'Country', 'Hip Hop', 'Holiday', 'Currents (Top-40s)',
              'Indie', 'Jazz', 'Metal', 'Oldies', 'Pop', 'Punk',
              'R&B/Soul', 'Funk', 'Reggae/Reggaeton', 'Sports Hits',
              'Student', 'Throwbacks', 'World', 'House/Weekend Party',
              'Sleepless 70s', 'Other']
    genres_dict = {genre: genre for genre in genres}
    genres_dict = {'Emo': 'Punk', **genres_dict, 'Other': 'Other'}
    for x in range(len(album_response['albums'])):
        trackset[x]['label'] = album_response['albums'][x]['label']
    for y in range(len(artist_response['artists'])):
        for artist_genre in artist_response['artists'][y]['genres']:
            words_in_genre = artist_genre.split()
            for word in words_in_genre:
                for genre_key in genres_dict:
                    if genre_key.lower() in word.lower():
                        trackset[y]['genre'] = genres_dict[genre_key]
                        break
        if trackset[y]['genre'] == '':
            trackset[y]['genre'] = 'Other'


def identify_moods(trackset):
    spotify_access_token = session.get('spotify_access_token')
    request = ''
    for track in trackset:
        request += track['id'] + '%2C'
    response = requests.get('https://api.spotify.com/v1/audio-features?ids='
                            + request[:-3],
                            headers={'Authorization': 'Bearer ' + spotify_access_token}).json()
    for x in range(len(response['audio_features'])):
        valence = response['audio_features'][x]['valence']
        energy = response['audio_features'][x]['energy']
        if energy > 0.8 and valence > 0.5:
            trackset[x]['mood'] = '6- Upbeat'
        elif energy < 0.2 and valence < 0.5:
            trackset[x]['mood'] = '1- Depressed'
        elif energy < 0.2:
            trackset[x]['mood'] = '4- Calm'
        elif valence < 0.5:
            trackset[x]['mood'] = '3- Sad'
        elif valence >= 0.5:
            trackset[x]['mood'] = '5- Happy'
        else:
            trackset[x]['mood'] = '7- Chaotic'


@app.route('/downloads', methods=['POST'])
def download_youtube_links():
    data = request.get_json()
    print(data)
    directory = r"C:\Downloads"
    playlist_name = data['body'][1]
    print(playlist_name)
    folder_name = data['body'][0]
    folder_id = find_file(folder_name, 'application/vnd.google-apps.folder')
    if folder_id is None:
        print("error: folder not found")
        return jsonify({'error': 'Folder not found'})
    print("folder name:", folder_name)
    print(folder_id)
    playlist_folder = create_folder(playlist_name, folder_id)
    trackset = data['body'][2]
    print("trackset")
    print(trackset)
    for track in trackset:
        print(track)
        if track['to_add'] == "True":
            results = Search(track['name'] + " " + track['artist'] + " Official Audio")
            if results.results:
                first = results.results[0]
                print(first)
                print(first.title)
                print(first.video_id)
                print("_____")
                try:
                    yt = YouTube(r"https://www.youtube.com/watch?v=" + first.video_id)
                    yt.streams.first().download(directory, "target.mp4")
                    print(track['name'] + " Downloaded to " + directory)
                    new_name = track['name'] + "_" + track['artist'] + "_" + session.get('first_name') + " " + session.get('last_name') + ".mp3"
                    subprocess.run([
                        'ffmpeg',
                        '-y', '-i',
                        os.path.join(directory, "target.mp4"),
                        os.path.join(directory,
                                     new_name)
                    ])
                    print("converted to mp3")
                    subprocess.run([
                        'del',
                        os.path.join(directory, "target.mp4")
                    ])
                    print("removed mp4")
                    upload_to_drive(os.path.join(directory, new_name), new_name, folder_id, playlist_folder)
                    print("uploaded to drive")
                    subprocess.run([
                        'del',
                        os.path.join(directory, new_name)
                    ])
                    print("removed mp3")
                except Exception as e:
                    print(e)
            else:
                print('No results found for ' + track['name'])
    return jsonify({'message': 'successful'})


def upload_to_drive(file_path, file_name, folder_id, playlist_folder_id):
    google_access_token = session.get('google_access_token')
    creds = Credentials(google_access_token)
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        media = MediaFileUpload(file_path, resumable=True)
        metadata = {'name': file_name, 'parents': [playlist_folder_id]}
        drive_service.files().create(body=metadata, media_body=media, fields='id').execute()
    except Exception as e:
        print(e)


def create_folder(playlist_name, folder_id):
    google_access_token = session.get('google_access_token')
    creds = Credentials(google_access_token)
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        metadata = {'name': playlist_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [folder_id]}
        file = drive_service.files().create(body=metadata, fields='id').execute()
        return file.get('id')
    except Exception as e:
        print(e)
        return None


def find_file(file_name, mimetype):
    google_access_token = session.get('google_access_token')
    creds = Credentials(google_access_token)
    drive_service = build('drive', 'v3', credentials=creds)
    page_token = None
    query = f"name='{file_name}' and mimeType='{mimetype}' and trashed=false"
    try:
        while True:
            response = drive_service.files().list(q=query,
                                                  spaces='drive',
                                                  fields='nextPageToken, files(id, name)',
                                                  pageToken=page_token).execute()
            for file in response.get('files', []):
                if file.get('name') == file_name:
                    return file.get('id')
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except Exception as e:
        print(e)
        return None


@app.route('/logout')
def logout():
    for key in list(session.keys()):
        print(key)
        session.pop(key)
    print("derrrrrp")
    for cookie in request.cookies:
        print(cookie)
    response = make_response(render_template('login.html'))
    response.set_cookie('session', '', expires=0)
    return response


if __name__ == '__main__':
    app.run(debug=True, port=port)
