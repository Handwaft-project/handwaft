import os
import json
import urllib.parse
import requests
from flask import Flask, render_template, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-dev-key-change-this')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'https://handwaft.up.railway.app/callback/google')

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


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    users = load_users()
    user = users.get(session['user_id'], {})
    if not user.get('username'):
        return redirect('/choose-username')
    return render_template(
        'index.html',
        user_logged_in=True,
        user_name=user.get('username'),
        user_initial=(user.get('username') or '?')[0].upper()
    )


@app.route('/choose-username', methods=['GET', 'POST'])
def choose_username():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'GET':
        return render_template('choose_username.html')

    data = request.get_json()
    username = (data.get('username') or '').strip()

    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters.'}), 400

    users = load_users()
    for uid, u in users.items():
        if (u.get('username') or '').lower() == username.lower() and uid != session['user_id']:
            return jsonify({'error': 'That username is already taken.'}), 409

    users[session['user_id']]['username'] = username
    save_users(users)
    return jsonify({'ok': True}), 200


@app.route('/login/google')
def login_google():
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'online',
        'prompt': 'select_account'
    }
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
    return redirect(url)


@app.route('/callback/google')
def callback_google():
    code = request.args.get('code')
    error = request.args.get('error')

    if error or not code:
        return redirect('/login?error=1')

    token_resp = requests.post('https://oauth2.googleapis.com/token', data={
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    })
    token_data = token_resp.json()
    access_token = token_data.get('access_token')

    if not access_token:
        return redirect('/login?error=1')

    profile_resp = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    profile = profile_resp.json()
    google_id = profile.get('id')
    email = profile.get('email')

    if not google_id:
        return redirect('/login?error=1')

    users = load_users()
    if google_id not in users:
        users[google_id] = {'email': email, 'username': None}
        save_users(users)

    session['user_id'] = google_id
    return redirect('/index')


@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'not logged in'}), 401
    users = load_users()
    user = users.get(session['user_id'], {})
    return jsonify({'username': user.get('username'), 'email': user.get('email')})


@app.route('/api/user/username', methods=['POST'])
def change_username():
    if 'user_id' not in session:
        return jsonify({'error': 'not logged in'}), 401

    data = request.get_json()
    new_username = (data.get('username') or '').strip()

    if len(new_username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters.'}), 400

    users = load_users()
    for uid, u in users.items():
        if (u.get('username') or '').lower() == new_username.lower() and uid != session['user_id']:
            return jsonify({'error': 'That username is already taken.'}), 409

    users[session['user_id']]['username'] = new_username
    save_users(users)
    return jsonify({'ok': True})


@app.route('/api/user/delete', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'error': 'not logged in'}), 401
    users = load_users()
    users.pop(session['user_id'], None)
    save_users(users)
    session.clear()
    return jsonify({'ok': True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)