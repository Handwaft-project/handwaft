import os
import json
from flask import Flask, render_template, redirect, request, session, jsonify
import requests
import base64
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-dev-key-change-this')

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8080/callback')

USERS_FILE = 'users.json'


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/signup')
def signup():
    # Only one entry point now — send them to the same Spotify login screen.
    return redirect('/login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/index')
def index():
    return render_template(
        'index.html',
        spotify_connected=bool(session.get('spotify_token')),
        user_logged_in='user_id' in session,
        user_name=session.get('user_name'),
        user_initial=(session.get('user_name') or '?')[0].upper()
    )


# Step 1: send the user to Spotify to approve access
@app.route('/login/spotify')
def login_spotify():
    scope = 'user-read-private user-read-email playlist-read-private user-library-read'
    params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'scope': scope,
    }
    url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode(params)
    return redirect(url)


# Step 2: Spotify sends the user back here — this both logs in and signs up
@app.route('/callback')
def callback():
    code = request.args.get('code')
    error = request.args.get('error')

    if error or not code:
        return redirect('/login?error=1')

    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    resp = requests.post(
        'https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI,
        },
        headers={'Authorization': f'Basic {auth_header}'}
    )
    token_data = resp.json()
    access_token = token_data.get('access_token')

    if not access_token:
        return redirect('/login?error=1')

    # Fetch the Spotify profile so we know who this is
    profile_resp = requests.get(
        'https://api.spotify.com/v1/me',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    profile = profile_resp.json()
    spotify_id = profile.get('id')

    if not spotify_id:
        return redirect('/login?error=1')

    # Create the local account on first login, or reuse it on repeat visits —
    # this is the "login or signup, one and the same" behavior.
    users = load_users()
    if spotify_id not in users:
        users[spotify_id] = {
            'name': profile.get('display_name') or 'Spotify User',
        }
        save_users(users)

    session['user_id'] = spotify_id
    session['user_name'] = users[spotify_id]['name']
    session['spotify_token'] = access_token
    session['spotify_refresh'] = token_data.get('refresh_token')

    return redirect('/index')


# Real user playlists, using their real token
@app.route('/api/spotify/playlists')
def spotify_playlists():
    token = session.get('spotify_token')
    if not token:
        return jsonify({'error': 'not connected'}), 401
    resp = requests.get(
        'https://api.spotify.com/v1/me/playlists',
        headers={'Authorization': f'Bearer {token}'}
    )
    if resp.status_code == 401:
        session.pop('spotify_token', None)
        return jsonify({'error': 'spotify session expired, please reconnect'}), 401

    data = resp.json()
    playlists = [
        {
            'id': p['id'],
            'name': p['name'],
            'trackCount': p.get('tracks', {}).get('total', 0)
        }
        for p in data.get('items', [])
    ]
    return jsonify({'playlists': playlists})

# Real song search
@app.route('/api/spotify/search')
def spotify_search():
    token = session.get('spotify_token')
    if not token:
        return jsonify({'error': 'not connected'}), 401
    q = request.args.get('q', '')
    resp = requests.get(
        'https://api.spotify.com/v1/search',
        params={'q': q, 'type': 'track', 'limit': 10},
        headers={'Authorization': f'Bearer {token}'}
    )
    if resp.status_code == 401:
        session.pop('spotify_token', None)
        return jsonify({'error': 'spotify session expired, please reconnect'}), 401

    data = resp.json()
    tracks = data.get('tracks', {}).get('items', [])
    items = [
        {
            'id': t['id'],
            'title': t['name'],
            'artist': ', '.join(a['name'] for a in t.get('artists', [])),
            'artwork': (t.get('album', {}).get('images') or [{}])[-1].get('url', ''),
            'previewUrl': t.get('preview_url'),
            'externalUrl': t.get('external_urls', {}).get('spotify')
        }
        for t in tracks
    ]
    return jsonify({'items': items})

    @app.route('/api/spotify/playlists/<playlist_id>/tracks')
def spotify_playlist_tracks(playlist_id):
    token = session.get('spotify_token')
    if not token:
        return jsonify({'error': 'not connected'}), 401
    resp = requests.get(
        f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
        headers={'Authorization': f'Bearer {token}'}
    )
    if resp.status_code == 401:
        session.pop('spotify_token', None)
        return jsonify({'error': 'spotify session expired, please reconnect'}), 401

    data = resp.json()
    items = []
    for entry in data.get('items', []):
        t = entry.get('track')
        if not t:
            continue
        items.append({
            'id': t['id'],
            'title': t['name'],
            'artist': ', '.join(a['name'] for a in t.get('artists', [])),
            'artwork': (t.get('album', {}).get('images') or [{}])[-1].get('url', ''),
            'previewUrl': t.get('preview_url'),
            'externalUrl': t.get('external_urls', {}).get('spotify')
        })
    return jsonify({'items': items})