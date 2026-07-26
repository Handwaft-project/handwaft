import os
import json
import uuid
from flask import Flask, render_template, redirect, request, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    users = load_users()
    user = users.get(email)

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Incorrect email or password.'}), 401

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = email

    return jsonify({'ok': True}), 200


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    data = request.get_json()
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or not email or len(password) < 8:
        return jsonify({'error': 'Please fill all fields — password needs 8+ characters.'}), 400

    users = load_users()
    if email in users:
        return jsonify({'error': 'An account with that email already exists.'}), 409

    users[email] = {
        'id': str(uuid.uuid4()),
        'name': name,
        'password_hash': generate_password_hash(password)
    }
    save_users(users)

    session['user_id'] = users[email]['id']
    session['user_name'] = name
    session['user_email'] = email

    return jsonify({'ok': True}), 200


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
    error = request.args.get('error')

    if error or not code:
        # Spotify rejected the login or the user cancelled — go back cleanly,
        # don't set a broken session key.
        return redirect('/index?spotify_error=1')

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
        # THE FIX: only write the token into the session if it's real.
        # Previously this always set session['spotify_token'], even to None,
        # which made spotify_connected read True with no working token.
        return redirect('/index?spotify_error=1')

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
        # Token expired/invalid — clear it so the UI stops claiming we're connected
        session.pop('spotify_token', None)
        return jsonify({'error': 'spotify session expired, please reconnect'}), 401
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
    if resp.status_code == 401:
        session.pop('spotify_token', None)
        return jsonify({'error': 'spotify session expired, please reconnect'}), 401
    return jsonify(resp.json())


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)