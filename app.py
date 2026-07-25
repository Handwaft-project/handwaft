import os
from flask import Flask, render_template, redirect, request, session, jsonify
import requests
import base64
import urllib.parse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-dev-key-change-this')

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8080/callback')


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/index')
def index():
    return render_template('index.html', spotify_connected=('spotify_token' in session))


# Step 1: send the user to Spotify to approve access
@app.route('/login/spotify')
def login_spotify():
    scope = 'user-read-private playlist-read-private user-library-read'
    params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'scope': scope,
    }
    url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode(params)
    return redirect(url)


# Step 2: Spotify sends the user back here with a code we trade for a token
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect('/login')

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
    session['spotify_token'] = token_data.get('access_token')
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
    return jsonify(resp.json())


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
    return jsonify(resp.json())


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)