"""Small local experimental baseline. Run: python app.py."""
import json
import os
import secrets
import sqlite3
import time
import uuid
from functools import wraps
from pathlib import Path
from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, bio TEXT NOT NULL, role TEXT NOT NULL, password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS webinars(id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, host_id INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS participants(id TEXT PRIMARY KEY, webinar_id TEXT NOT NULL REFERENCES webinars(id), user_id INTEGER NOT NULL REFERENCES users(id), seen REAL NOT NULL);
CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY AUTOINCREMENT, webinar_id TEXT NOT NULL, sender TEXT NOT NULL, recipient TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
'''


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=str(Path(__file__).parent / 'instance' / 'webinar.sqlite'), SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32), MAX_CONTENT_LENGTH=65536, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    if config:
        app.config.update(config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        conn = g.pop('db', None)
        if conn:
            conn.close()

    with app.app_context():
        db().executescript(SCHEMA)
        if not db().execute('SELECT 1 FROM users LIMIT 1').fetchone():
            for i, (name, role) in enumerate([('Alex Morgan', 'host'), ('Sam Rivera', 'panelist'), ('Jamie Chen', 'attendee')], 1):
                db().execute('INSERT INTO users VALUES(?,?,?,?,?,?)', (i, role+'@demo.test', name, 'Demo '+role+' profile', role, generate_password_hash('StudyDemo123!')))
            db().execute('INSERT INTO webinars VALUES(?,?,?,?)', ('welcome', 'The research room', 'A space to test, discuss, and build together.', 1))
            db().commit()

    def auth(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            g.user = db().execute('SELECT id,email,name,bio,role FROM users WHERE id=?', (session.get('uid'),)).fetchone()
            if not g.user:
                return jsonify(error='Please sign in.'), 401
            return fn(*args, **kwargs)
        return wrapped

    def member(wid, pid):
        return db().execute('SELECT * FROM participants WHERE id=? AND webinar_id=? AND user_id=? AND seen>?', (pid, wid, g.user['id'], time.time()-30)).fetchone()

    @app.before_request
    def check_json():
        if request.path.startswith('/api/') and request.method == 'POST' and not request.is_json:
            return jsonify(error='JSON request required.'), 415
        if request.method == 'POST' and request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(error='Cross-site request rejected.'), 403

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='Request is too large.'), 413

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.post('/api/login')
    def login():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify(error='Invalid request.'), 400
        user = db().execute('SELECT * FROM users WHERE email=?', (str(data.get('email', '')).lower().strip(),)).fetchone()
        if not user or not check_password_hash(user['password'], str(data.get('password', ''))):
            return jsonify(error='Email or password is incorrect.'), 401
        session.clear()
        session['uid'] = user['id']
        return jsonify(ok=True)

    @app.post('/api/logout')
    @auth
    def logout():
        db().execute('DELETE FROM participants WHERE user_id=?', (g.user['id'],))
        db().commit()
        session.clear()
        return jsonify(ok=True)

    @app.get('/api/me')
    @auth
    def me():
        return jsonify(dict(g.user))

    @app.route('/api/webinars', methods=['GET', 'POST'])
    @auth
    def webinars():
        if request.method == 'POST':
            if g.user['role'] != 'host':
                return jsonify(error='Only hosts can create webinars.'), 403
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict) or not isinstance(data.get('title'), str) or not 1 <= len(data['title'].strip()) <= 100 or not isinstance(data.get('description', ''), str) or len(data.get('description', '')) > 500:
                return jsonify(error='Use a title of 1–100 characters and a description up to 500 characters.'), 400
            wid = uuid.uuid4().hex
            db().execute('INSERT INTO webinars VALUES(?,?,?,?)', (wid, data['title'].strip(), data.get('description', '').strip(), g.user['id']))
            db().commit()
            return jsonify(id=wid), 201
        rows = db().execute('SELECT w.*,u.name host_name,(SELECT count(*) FROM participants p WHERE p.webinar_id=w.id AND p.seen>?) online FROM webinars w JOIN users u ON u.id=w.host_id ORDER BY w.rowid DESC', (time.time()-30,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post('/api/webinars/<wid>/join')
    @auth
    def join(wid):
        if not db().execute('SELECT 1 FROM webinars WHERE id=?', (wid,)).fetchone():
            return jsonify(error='Webinar not found.'), 404
        # Serialize capacity check and insert across simultaneous requests.
        db().execute('BEGIN IMMEDIATE')
        db().execute('DELETE FROM participants WHERE seen<?', (time.time()-30,))
        if db().execute('SELECT count(*) FROM participants WHERE webinar_id=?', (wid,)).fetchone()[0] >= 4:
            db().rollback()
            return jsonify(error='This small room is full (4 participants).'), 409
        pid = uuid.uuid4().hex
        db().execute('INSERT INTO participants VALUES(?,?,?,?)', (pid, wid, g.user['id'], time.time()))
        db().commit()
        return jsonify(participant_id=pid), 201

    @app.post('/api/webinars/<wid>/leave')
    @auth
    def leave(wid):
        data = request.get_json(silent=True) or {}
        pid = data.get('participant_id') if isinstance(data, dict) else None
        db().execute('DELETE FROM participants WHERE id=? AND webinar_id=? AND user_id=?', (pid, wid, g.user['id']))
        db().commit()
        return jsonify(ok=True)

    @app.route('/api/webinars/<wid>/signals', methods=['GET', 'POST'])
    @auth
    def signals(wid):
        data = request.get_json(silent=True) or {} if request.method == 'POST' else request.args
        if request.method == 'POST' and not isinstance(data, dict):
            return jsonify(error='Invalid request.'), 400
        pid = data.get('participant_id')
        if not member(wid, pid):
            return jsonify(error='Room session expired. Leave and rejoin.'), 403
        db().execute('UPDATE participants SET seen=? WHERE id=?', (time.time(), pid))
        db().execute('DELETE FROM signals WHERE created<?', (time.time()-120,))
        if request.method == 'POST':
            target = data.get('recipient')
            if not db().execute('SELECT 1 FROM participants WHERE id=? AND webinar_id=? AND seen>?', (target, wid, time.time()-30)).fetchone():
                return jsonify(error='Participant has left.'), 404
            payload = data.get('payload')
            if not isinstance(payload, dict) or payload.get('type') not in ('offer', 'answer', 'ice'):
                return jsonify(error='Invalid signal.'), 400
            db().execute('INSERT INTO signals(webinar_id,sender,recipient,payload,created) VALUES(?,?,?,?,?)', (wid, pid, target, json.dumps(payload), time.time()))
            db().commit()
            return jsonify(ok=True)
        try:
            after = max(0, int(data.get('after', 0)))
        except (TypeError, ValueError):
            return jsonify(error='Invalid cursor.'), 400
        peers = db().execute('SELECT p.id,u.name,u.role FROM participants p JOIN users u ON u.id=p.user_id WHERE p.webinar_id=? AND p.seen>? ORDER BY p.id', (wid, time.time()-30)).fetchall()
        messages = db().execute('SELECT id,sender,payload FROM signals WHERE webinar_id=? AND recipient=? AND id>? ORDER BY id', (wid, pid, after)).fetchall()
        db().commit()
        return jsonify(peers=[dict(r) for r in peers], signals=[dict(id=r['id'], sender=r['sender'], payload=json.loads(r['payload'])) for r in messages])

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False, threaded=True)
