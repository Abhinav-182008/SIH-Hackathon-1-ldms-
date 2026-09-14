"""Local synthetic-data prototype. Python 3.9+, standard library only."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('CASEVAULT_DB', ROOT / 'data/casevault.sqlite3'))
MAX_FILE = 50 * 1024 * 1024
# JSON uses base64, which adds about one third to the original file size.
MAX_REQUEST = ((MAX_FILE + 2) // 3) * 4 + 64 * 1024
PORT = int(os.environ.get('PORT', '8000'))
ORIGIN = os.environ.get('APP_ORIGIN', 'http://localhost:5173')

def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def audit(db, actor, action, case_id=''):
    db.execute('INSERT INTO audit(actor,action,case_id,at) VALUES(?,?,?,?)',
               (actor, action, case_id, time.time()))


def notify(db, user_id, request, kind):
    messages = {
        'requested': ('New access request', 'A request for ' + request['case_id'] + ' is waiting for your review.'),
        'approved': ('Access approved', 'Your request for ' + request['case_id'] + ' was approved. You can open the case until the grant expires.'),
        'rejected': ('Request rejected', 'Your request for ' + request['case_id'] + ' was rejected.'),
        'revoked': ('Access revoked', 'The reviewer withdrew your grant for ' + request['case_id'] + '.'),
        'expired': ('Access expired', 'Your grant for ' + request['case_id'] + ' has ended. Request access again if needed.'),
    }
    title, message = messages[kind]
    db.execute('INSERT OR IGNORE INTO notifications(id,user_id,request_id,case_id,kind,title,message,created,event_key) VALUES(?,?,?,?,?,?,?,?,?)',
        ('NTF-' + secrets.token_hex(12), user_id, request['id'], request['case_id'], kind, title, message, time.time(), request['id'] + ':' + kind + ':' + user_id))

def expire_grants(db):
    # Serialize expiry with review decisions; a notification is created exactly once.
    for row in db.execute("SELECT * FROM requests WHERE status='approved' AND expires<=?", (time.time(),)).fetchall():
        changed = db.execute("UPDATE requests SET status='expired' WHERE id=? AND status='approved' AND expires<=?", (row['id'],time.time())).rowcount
        if changed:
            notify(db, row['requester'], row, 'expired')
            audit(db, 'System', 'Access expired for ' + row['requester'], row['case_id'])

def initialize_notifications(db):
    expire_grants(db)
    # Existing requests remain visible after upgrading; deduplication preserves read state.
    for row in db.execute('SELECT * FROM requests').fetchall():
        if row['status'] == 'pending':
            for target in db.execute('SELECT user_id FROM reviewers WHERE case_id=? AND user_id!=?', (row['case_id'],row['requester'])).fetchall():
                notify(db, target['user_id'], row, 'requested')
        elif row['status'] in ['approved','rejected','revoked','expired']:
            notify(db, row['requester'], row, row['status'])

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

def seed():
    DB.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,login TEXT UNIQUE,salt TEXT,hash TEXT,profile TEXT);
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(case_id TEXT REFERENCES cases(id),user_id TEXT REFERENCES users(id),PRIMARY KEY(case_id,user_id));
        CREATE TABLE IF NOT EXISTS reviewers(case_id TEXT REFERENCES cases(id),user_id TEXT REFERENCES users(id),PRIMARY KEY(case_id,user_id));
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires REAL);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,case_id TEXT REFERENCES cases(id),requester TEXT REFERENCES users(id),reason TEXT,status TEXT,expires REAL,reviewer TEXT,created REAL);
        CREATE UNIQUE INDEX IF NOT EXISTS one_pending ON requests(case_id,requester) WHERE status='pending';
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,case_id TEXT REFERENCES cases(id),name TEXT,type TEXT,mime TEXT,metadata TEXT,body BLOB,sha256 TEXT,created REAL,creator TEXT REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,case_id TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),request_id TEXT REFERENCES requests(id),case_id TEXT,kind TEXT,title TEXT,message TEXT,created REAL,read_at REAL,event_key TEXT UNIQUE);
        CREATE INDEX IF NOT EXISTS notifications_user ON notifications(user_id,created);
        CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT PRIMARY KEY,count INTEGER,reset REAL);
        ''')
        if db.execute('SELECT count(*) FROM users').fetchone()[0]:
            initialize_notifications(db)
            return
        profiles = json.loads((ROOT / 'seed/officers.json').read_text())
        credentials = json.loads((ROOT / 'seed/credentials.json').read_text())
        for cred in credentials:
            profile = next(p for p in profiles if p['officer_id'] == cred['officer_id'])
            salt = secrets.token_hex(16)
            db.execute('INSERT INTO users VALUES(?,?,?,?,?)', (profile['officer_id'], cred['login_id'], salt,
                password_hash(cred['password'], salt), json.dumps(profile)))
        ids = {p['officer_id'] for p in profiles}
        for case in json.loads((ROOT / 'seed/cases_manifest.json').read_text()):
            # Seed document labels are not actual uploaded files.
            case['documents'] = []
            db.execute('INSERT INTO cases VALUES(?,?)', (case['case_id'], json.dumps(case)))
            for field in ['investigating_officer', 'assisting_officer', 'external_assignments']:
                assert isinstance(case[field], list) and all(x in ids for x in case[field])
                for uid in case[field]:
                    db.execute('INSERT OR IGNORE INTO assignments VALUES(?,?)', (case['case_id'], uid))
            reviewers = [p['officer_id'] for p in profiles if p['access_level'] == 4 and p['station'] == case['station_name']]
            # Explicit fallback reviewer for stations without a Level 4 officer.
            for uid in reviewers or ['OFF-001']:
                db.execute('INSERT INTO reviewers VALUES(?,?)', (case['case_id'], uid))
        for index, cid in enumerate(['2024-CR-104', '2024-CR-105'], 1):
            body = ('SYNTHETIC DEMO DOCUMENT\nCase ' + cid + '\nNo real evidence.\n').encode()
            db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)',
                ('DEMO-DOC-' + str(index), cid, 'synthetic-note.txt', 'Demo note', 'text/plain', '{}', body,
                 hashlib.sha256(body).hexdigest(), time.time(), 'OFF-001'))
        audit(db, 'System', 'Seeded five synthetic cases and two actual sample files')
    os.chmod(DB, 0o600)

def reviewer(db, uid, cid):
    return bool(db.execute('SELECT 1 FROM reviewers WHERE case_id=? AND user_id=?', (cid, uid)).fetchone())

def assigned(db, uid, cid):
    return bool(db.execute('SELECT 1 FROM assignments WHERE case_id=? AND user_id=?', (cid, uid)).fetchone())

def can_read(db, uid, cid):
    return assigned(db, uid, cid) or reviewer(db, uid, cid) or bool(db.execute(
        "SELECT 1 FROM requests WHERE case_id=? AND requester=? AND status='approved' AND expires>?",
        (cid, uid, time.time())).fetchone())

class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def require(condition, status=403, message='Access denied'):
    if not condition:
        raise ApiError(status, message)

def field(data, name, limit=500, required=True):
    value = data.get(name, '')
    require(isinstance(value, str) and len(value) <= limit, 400, 'Invalid ' + name)
    value = value.strip()
    require(bool(value) or not required, 400, 'Missing ' + name)
    return value

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never print credentials, cookies, or request bodies.

    def respond(self, status, body, headers=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, mutation):
        db = connect()
        uid = 'Anonymous'
        cid = ''
        try:
            path = urlparse(self.path).path
            data = {}
            if mutation:
                require(self.headers.get('Origin') == ORIGIN, 403, 'Invalid request origin')
                require(self.headers.get('Content-Type', '').split(';')[0] == 'application/json', 415, 'JSON required')
                length = int(self.headers.get('Content-Length', '0'))
                require(0 < length <= MAX_REQUEST, 413, 'Request too large or empty')
                data = json.loads(self.rfile.read(length))
                require(isinstance(data, dict), 400, 'JSON object required')
            if path == '/api/login' and mutation:
                ip = self.client_address[0]
                attempt = db.execute('SELECT * FROM login_attempts WHERE ip=?', (ip,)).fetchone()
                require(not attempt or attempt['reset'] < time.time() or attempt['count'] < 10, 429, 'Too many attempts. Try again in 15 minutes.')
                login = field(data, 'loginId', 100).lower()
                password = field(data, 'password', 200)
                row = db.execute('SELECT * FROM users WHERE login=?', (login,)).fetchone()
                salt = row['salt'] if row else '00' * 16
                valid = hmac.compare_digest(password_hash(password, salt), row['hash'] if row else '0' * 64)
                if not row or not valid:
                    count = attempt['count'] + 1 if attempt and attempt['reset'] > time.time() else 1
                    reset = attempt['reset'] if attempt and attempt['reset'] > time.time() else time.time() + 900
                    db.execute('INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)', (ip, count, reset))
                    raise ApiError(401, 'Login ID or password is incorrect')
                token = secrets.token_urlsafe(32)
                cookie = SimpleCookie(self.headers.get('Cookie', ''))
                if 'session' in cookie:
                    db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(cookie['session'].value.encode()).hexdigest(),))
                db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
                db.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), row['id'], time.time()+3600))
                db.execute('DELETE FROM login_attempts WHERE ip=?', (ip,))
                audit(db, row['id'], 'Login')
                db.commit()
                self.respond(200, {'officer': json.loads(row['profile'])}, {'Set-Cookie': self.cookie(token, 3600)})
                return
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookie['session'].value if 'session' in cookie else ''
            session = db.execute('SELECT * FROM sessions WHERE token=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
            require(session is not None, 401, 'Please sign in')
            uid = session['user_id']
            profile = json.loads(db.execute('SELECT profile FROM users WHERE id=?', (uid,)).fetchone()[0])
            if path == '/api/me' and not mutation:
                self.respond(200, {'officer': profile})
                return
            if path == '/api/logout' and mutation:
                db.execute('DELETE FROM sessions WHERE token=?', (session['token'],))
                audit(db, uid, 'Logout')
                db.commit()
                self.respond(200, {}, {'Set-Cookie': self.cookie('', 0)})
                return
            if path == '/api/state' and not mutation:
                db.execute('BEGIN IMMEDIATE')
                expire_grants(db)
                db.commit()
                # Discovery policy: only case ID, type and station may be shared across officers.
                cases = []
                for row in db.execute('SELECT * FROM cases'):
                    c = json.loads(row['data'])
                    allowed = can_read(db, uid, row['id'])
                    public = {key: c[key] for key in ['case_id', 'crime_type', 'station_name']}
                    public.update(eligible=allowed, canUpload=assigned(db, uid, row['id']) or reviewer(db, uid, row['id']))
                    cases.append(public)
                requests = []
                for row in db.execute('SELECT * FROM requests ORDER BY created DESC'):
                    if row['requester'] == uid or reviewer(db, uid, row['case_id']):
                        r = dict(row)
                        case_data = json.loads(db.execute('SELECT data FROM cases WHERE id=?',(row['case_id'],)).fetchone()[0])
                        r['caseTitle'] = case_data['crime_type']
                        r['stationName'] = case_data['station_name']
                        r['incidentDate'] = case_data['incident_date']
                        r['requesterName'] = json.loads(db.execute('SELECT profile FROM users WHERE id=?',(row['requester'],)).fetchone()[0])['name']
                        r['reviewerNames'] = [json.loads(x[0])['name'] for x in db.execute('SELECT u.profile FROM reviewers r JOIN users u ON u.id=r.user_id WHERE r.case_id=?',(row['case_id'],))]
                        r['reviewedBy'] = json.loads(db.execute('SELECT profile FROM users WHERE id=?',(row['reviewer'],)).fetchone()[0])['name'] if row['reviewer'] else None
                        r['canOpen'] = can_read(db,uid,row['case_id'])
                        r['canReview'] = reviewer(db, uid, row['case_id']) and row['requester'] != uid
                        if r['status'] == 'approved' and r['expires'] <= time.time():
                            r['status'] = 'expired'
                        requests.append(r)
                events = [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 500')
                          if r['actor'] == uid or reviewer(db, uid, r['case_id'])]
                self.respond(200, {'cases': cases, 'accessRequests': requests, 'auditLog': events[:50],
                    'canReview': bool(db.execute('SELECT 1 FROM reviewers WHERE user_id=? LIMIT 1',(uid,)).fetchone()),
                    'notifications': [dict(n) for n in db.execute('SELECT id,request_id,case_id,kind,title,message,created,read_at FROM notifications WHERE user_id=? ORDER BY created DESC LIMIT 100',(uid,))],
                    'unreadCount': db.execute('SELECT count(*) FROM notifications WHERE user_id=? AND read_at IS NULL',(uid,)).fetchone()[0]})
                return
            if path == '/api/notifications/read' and mutation:
                notification_id = data.get('id')
                if notification_id == 'all':
                    db.execute('UPDATE notifications SET read_at=? WHERE user_id=? AND read_at IS NULL',(time.time(),uid))
                else:
                    require(isinstance(notification_id,str),400,'Invalid notification ID')
                    require(db.execute('SELECT 1 FROM notifications WHERE id=? AND user_id=?',(notification_id,uid)).fetchone() is not None,404,'Notification not found')
                    db.execute('UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND user_id=?',(time.time(),notification_id,uid))
                db.commit()
                self.respond(200,{})
                return
            if path == '/api/search' and not mutation:
                query = parse_qs(urlparse(self.path).query).get('q', [''])[0][:500].lower()
                tokens = [t for t in re.findall(r'[\w-]+', query) if len(t) > 2 and t not in {'the','case','cases','find','show','records','with','for','all','get','and'}]
                results = []
                for row in db.execute('SELECT * FROM cases'):
                    c = json.loads(row['data'])
                    allowed = can_read(db, uid, row['id'])
                    public = {key: c[key] for key in ['case_id', 'crime_type', 'station_name']}
                    searchable = json.dumps(public)
                    if allowed:
                        searchable = json.dumps(c) + ' '.join(r[0] + ' ' + r[1] for r in db.execute('SELECT name,metadata FROM documents WHERE case_id=?', (row['id'],)))
                    score = sum(t in searchable.lower() for t in tokens)
                    if score:
                        public.update(eligible=allowed, score=score)
                        results.append(public)
                audit(db, uid, 'Search (authorized fields only)')
                db.commit()
                self.respond(200, sorted(results, key=lambda r: -r['score']))
                return
            if path.startswith('/api/cases/') and not mutation:
                cid = unquote(path[len('/api/cases/'):])
                require(can_read(db, uid, cid))
                row = db.execute('SELECT data FROM cases WHERE id=?', (cid,)).fetchone()
                require(row is not None, 404, 'Case not found')
                c = json.loads(row[0])
                c['files'] = [dict(r) for r in db.execute('SELECT id,name,type,mime,metadata,sha256,created FROM documents WHERE case_id=?', (cid,))]
                audit(db, uid, 'Viewed case', cid)
                db.commit()
                self.respond(200, c)
                return
            if path.startswith('/api/documents/') and not mutation:
                did = unquote(path[len('/api/documents/'):])
                row = db.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone()
                cid = row['case_id'] if row else ''
                require(row is not None and can_read(db, uid, cid))
                audit(db, uid, 'Downloaded document ' + did, cid)
                db.commit()
                self.send_response(200)
                self.send_header('Content-Type', row['mime'])
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(row['name'], safe=''))
                self.send_header('Content-Length', str(len(row['body'])))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.wfile.write(row['body'])
                return
            if path == '/api/upload' and mutation:
                db.execute('BEGIN IMMEDIATE')
                cid = field(data, 'caseId', 80)
                require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', cid)), 400, 'Invalid case ID')
                row = db.execute('SELECT data FROM cases WHERE id=?', (cid,)).fetchone()
                creating = data.get('createNew') is True
                require(not creating or row is None, 409, 'Case ID already exists')
                if row:
                    require(assigned(db, uid, cid) or reviewer(db, uid, cid))
                else:
                    require(creating and profile['access_level'] in [3, 4], 403, 'Only investigating/station officers can create cases')
                name = field(data, 'name', 150)
                require('/' not in name and '\\' not in name and not any(ord(c)<32 for c in name), 400, 'Invalid filename')
                body = base64.b64decode(field(data, 'content', MAX_REQUEST), validate=True)
                require(0 < len(body) <= MAX_FILE, 413, 'File must be 1 byte to 50 MB')
                ext = Path(name).suffix.lower()
                mime = None
                if ext == '.pdf' and body.startswith(b'%PDF-'): mime = 'application/pdf'
                if ext == '.png' and body.startswith(b'\x89PNG\r\n\x1a\n'): mime = 'image/png'
                if ext in ['.jpg', '.jpeg'] and body.startswith(b'\xff\xd8\xff'): mime = 'image/jpeg'
                if ext == '.txt':
                    body.decode('utf-8')
                    require(b'\x00' not in body, 400, 'Invalid text file')
                    mime = 'text/plain'
                require(mime is not None, 400, 'Use PDF, PNG, JPG or UTF-8 TXT with matching contents')
                metadata = {key: field(data, key, 4000, False) for key in ['suspectName', 'section', 'location', 'notes']}
                dtype = field(data, 'documentType', 100)
                if not row:
                    c = dict(case_id=cid, crime_type=field(data,'crimeType',200), station_name=profile['station'],
                        status='Investigation Active', incident_date=time.strftime('%Y-%m-%d'), suspect_name=metadata['suspectName'],
                        section_act=metadata['section'], incident_location=metadata['location'], summary=metadata['notes'],
                        investigating_officer=[uid], assisting_officer=[], external_assignments=[], documents=[])
                    db.execute('INSERT INTO cases VALUES(?,?)', (cid, json.dumps(c)))
                    db.execute('INSERT INTO assignments VALUES(?,?)', (cid, uid))
                    supervisors = [r['id'] for r in db.execute('SELECT id,profile FROM users') if
                        json.loads(r['profile'])['access_level'] == 4 and json.loads(r['profile'])['station'] == profile['station']]
                    for rid in supervisors or ['OFF-001']:
                        db.execute('INSERT INTO reviewers VALUES(?,?)', (cid, rid))
                did = 'DOC-' + secrets.token_hex(12)
                db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)', (did,cid,name,dtype,mime,json.dumps(metadata),body,
                           hashlib.sha256(body).hexdigest(),time.time(),uid))
                audit(db, uid, 'Uploaded document ' + did, cid)
                db.commit()
                self.respond(201, {'docId': did})
                return
            if path == '/api/requests' and mutation:
                db.execute('BEGIN IMMEDIATE')
                cid = field(data, 'caseId', 80)
                reason = field(data, 'reason', 1000)
                require(db.execute('SELECT 1 FROM cases WHERE id=?', (cid,)).fetchone() is not None, 404, 'Case not found')
                require(not can_read(db, uid, cid), 409, 'You already have access')
                require(not db.execute("SELECT 1 FROM requests WHERE case_id=? AND requester=? AND status='pending'", (cid,uid)).fetchone(), 409, 'Request already pending')
                rid = 'REQ-'+secrets.token_hex(12)
                db.execute('INSERT INTO requests VALUES(?,?,?,?,?,?,?,?)', (rid,cid,uid,reason,'pending',None,None,time.time()))
                request_row = db.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
                for target in db.execute('SELECT user_id FROM reviewers WHERE case_id=? AND user_id!=?',(cid,uid)).fetchall():
                    notify(db,target['user_id'],request_row,'requested')
                audit(db, uid, 'Requested access', cid)
                db.commit()
                self.respond(201, {})
                return
            if path.startswith('/api/requests/') and mutation:
                db.execute('BEGIN IMMEDIATE')
                rid = unquote(path[len('/api/requests/'):])
                row = db.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()
                cid = row['case_id'] if row else ''
                require(row is not None and reviewer(db, uid, cid) and row['requester'] != uid)
                expire_grants(db)
                row = db.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
                action = field(data, 'action', 20)
                require(action in ['approve','reject','revoke'], 400, 'Invalid action')
                require(row['status'] == ('approved' if action == 'revoke' else 'pending'), 409, 'Request is no longer in that state')
                expiry = None
                if action == 'approve':
                    hours = data.get('hours', 1)
                    require(type(hours) in [int,float] and 0 < hours <= 720, 400, 'Duration must be greater than 0 and at most 720 hours (30 days)')
                    expiry = time.time() + hours*3600
                status = {'approve':'approved','reject':'rejected','revoke':'revoked'}[action]
                db.execute('UPDATE requests SET status=?,expires=?,reviewer=? WHERE id=?', (status,expiry,uid,rid))
                notify(db,row['requester'],row,status)
                db.execute("UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE request_id=? AND kind='requested'",(time.time(),rid))
                audit(db, uid, status.capitalize() + ' access for ' + row['requester'], cid)
                db.commit()
                self.respond(200, {})
                return
            raise ApiError(404, 'Not found')
        except ApiError as exc:
            # Roll back partially written uploads/decisions; save denial separately.
            if not (urlparse(self.path).path == '/api/login' and exc.status == 401):
                db.rollback()
            audit(db, uid, 'Denied/failed ' + urlparse(self.path).path[:150] + ' (' + str(exc.status) + ')', cid)
            db.commit()
            self.respond(exc.status, {'error': exc.message})
        except (ValueError, TypeError, UnicodeError):
            db.rollback()
            audit(db, uid, 'Invalid request data', cid)
            db.commit()
            self.respond(400, {'error': 'Invalid request data'})
        except Exception:
            db.rollback()
            audit(db, uid, 'Operation failed', cid)
            db.commit()
            self.respond(500, {'error': 'Operation failed; no success recorded'})
        finally:
            db.close()

    def cookie(self, token, age):
        return 'session=' + token + '; HttpOnly; SameSite=Strict; Path=/api; Max-Age=' + str(age) + ('; Secure' if ORIGIN.startswith('https://') else '')

if __name__ == '__main__':
    seed()
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print('CaseVault API: http://127.0.0.1:' + str(PORT), flush=True)
    server.serve_forever()
