"""Integration checks against real HTTP handlers and a temporary on-disk database."""
import base64
import http.cookiejar
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.env = dict(os.environ, CASEVAULT_DB=str(Path(cls.temp.name)/'test.sqlite3'), PORT='18090')
        cls.start()

    @classmethod
    def start(cls):
        cls.proc = subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('server.py'))], env=cls.env, stdout=subprocess.PIPE)
        line = cls.proc.stdout.readline()
        assert b'CaseVault API' in line, line

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate(); cls.proc.wait(); cls.proc.stdout.close(); cls.temp.cleanup()

    def client(self, login=None, password=None):
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        if login:
            status, data = self.call(client, '/login', {'loginId':login,'password':password})
            self.assertEqual(status, 200, data)
        return client

    def call(self, client, path, data=None, origin='http://localhost:5173'):
        req = urllib.request.Request('http://127.0.0.1:18090/api'+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Content-Type':'application/json', 'Origin':origin})
        try:
            response = client.open(req)
        except urllib.error.HTTPError as e:
            response = e
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if response.headers.get_content_type() == 'application/json' else raw

    def test_complete_workflow(self):
        anon = self.client()
        self.assertEqual(self.call(anon,'/state')[0],401)
        self.assertEqual(self.call(anon,'/login',{'loginId':'rmenon','password':'wrong'})[0],401)
        officer = self.client('rmenon','Kochi@004')
        requester = self.client('vprasad','Kochi@010')
        reviewer = self.client('akumar','Kochi@001')
        station = self.client('pnair','Kochi@002')
        self.assertEqual(self.call(reviewer,'/cases/2024-CR-104')[0],403, 'Level 5 must not have blanket access')
        self.assertEqual(self.call(officer,'/cases/2024-CR-104')[0],200)
        self.assertEqual(self.call(officer,'/cases/2024-CR-105')[0],403)
        status, state = self.call(requester,'/state')
        self.assertFalse(any('summary' in c or 'suspect_name' in c for c in state['cases']))
        _, search = self.call(requester,'/search?q=damaged')
        self.assertFalse(any(c['case_id']=='2024-CR-105' for c in search), 'Restricted summary leaked through search')
        self.assertEqual(self.call(requester,'/documents/DEMO-DOC-2')[0],403)
        _, allowed = self.call(officer,'/search?q=red')
        self.assertTrue(any(c['case_id']=='2024-CR-104' for c in allowed))
        body = b'Synthetic original exact bytes\n'
        upload = dict(caseId='2024-CR-104',name='demo.txt',content=base64.b64encode(body).decode(),documentType='FIR',notes='unique-upload-note')
        status, result = self.call(officer,'/upload',upload)
        self.assertEqual(status,201,result)
        did = result['docId']
        self.assertEqual(self.call(officer,'/documents/'+did),(200,body))
        self.assertTrue(self.call(officer,'/search?q=unique-upload-note')[1])
        self.assertEqual(self.call(officer,'/upload',{**upload,'caseId':'2024-CR-105'})[0],403)
        self.assertEqual(self.call(officer,'/upload',{**upload,'name':'bad.pdf'})[0],400)
        self.assertEqual(self.call(officer,'/upload',{**upload,'name':'../bad.txt'})[0],400)
        self.assertEqual(self.call(officer,'/upload',{**upload,'content':base64.b64encode(b'x'*(50*1024*1024+1)).decode()})[0],413)
        large = b'x' * (50*1024*1024)
        status, large_result = self.call(officer,'/upload',{**upload,'name':'boundary-50mb.txt','content':base64.b64encode(large).decode()})
        self.assertEqual(status,201,large_result)
        status, downloaded = self.call(officer,'/documents/'+large_result['docId'])
        self.assertEqual(status,200)
        import hashlib
        self.assertEqual(hashlib.sha256(downloaded).digest(),hashlib.sha256(large).digest())
        del large, downloaded
        self.assertEqual(self.call(officer,'/upload',{**upload,'createNew':True})[0],409)
        new = {**upload,'caseId':'DEMO-NEW','createNew':True,'crimeType':'Synthetic new case'}
        self.assertEqual(self.call(officer,'/upload',new)[0],201)
        self.assertEqual(self.call(requester,'/upload',{**new,'caseId':'FORBIDDEN'})[0],403)
        request = {'caseId':'2024-CR-105','reason':'Synthetic cross-case investigation'}
        self.assertEqual(self.call(requester,'/requests',request)[0],201)
        self.assertEqual(self.call(requester,'/requests',request)[0],409)
        reviewer_state = self.call(reviewer,'/state')[1]
        self.assertTrue(reviewer_state['canReview'])
        self.assertFalse(self.call(officer,'/state')[1]['canReview'])
        notice = next(n for n in reviewer_state['notifications'] if n['kind']=='requested')
        self.assertEqual(self.call(requester,'/notifications/read',{'id':notice['id']})[0],404)
        self.assertEqual(self.call(reviewer,'/notifications/read',{'id':notice['id']})[0],200)
        self.assertEqual(self.call(reviewer,'/state')[1]['unreadCount'],0)

        rid = self.call(requester,'/state')[1]['accessRequests'][0]['id']
        self.assertEqual(self.call(requester,'/requests/'+rid,{'action':'approve'})[0],403)
        self.assertEqual(self.call(station,'/requests/'+rid,{'action':'approve'})[0],403)
        self.assertEqual(self.call(reviewer,'/requests/'+rid,{'action':'approve','hours':1},origin='https://evil.example')[0],403)
        self.assertEqual(self.call(reviewer,'/requests/'+rid,{'action':'approve','hours':721})[0],400)
        self.assertEqual(self.call(reviewer,'/requests/'+rid,{'action':'approve','hours':720})[0],200)
        approved_state = self.call(requester,'/state')[1]
        approval = next(r for r in approved_state['accessRequests'] if r['id']==rid)
        self.assertEqual(approval['status'],'approved')
        self.assertTrue(approval['canOpen'])
        self.assertIn('requesterName',approval)
        self.assertTrue(29.9*86400 < approval['expires']-time.time() <= 30*86400)
        approved_notice = next(n for n in approved_state['notifications'] if n['kind']=='approved')
        self.assertEqual(self.call(requester,'/notifications/read',{'id':approved_notice['id']})[0],200)
        self.assertEqual(self.call(requester,'/documents/DEMO-DOC-2')[0],200)

        self.assertEqual(self.call(requester,'/upload',{**upload,'caseId':'2024-CR-105'})[0],403,'Read grant must not grant upload')
        self.assertEqual(self.call(reviewer,'/requests/'+rid,{'action':'revoke'})[0],200)
        self.assertTrue(any(n['kind']=='revoked' for n in self.call(requester,'/state')[1]['notifications']))

        self.assertEqual(self.call(requester,'/documents/DEMO-DOC-2')[0],403)
        self.assertEqual(self.call(requester,'/requests',request)[0],201)
        rid = self.call(requester,'/state')[1]['accessRequests'][0]['id']
        self.assertEqual(self.call(reviewer,'/requests/'+rid,{'action':'reject'})[0],200)
        self.assertTrue(any(n['kind']=='rejected' for n in self.call(requester,'/state')[1]['notifications']))

        self.assertEqual(self.call(requester,'/requests',request)[0],201)
        rid = self.call(requester,'/state')[1]['accessRequests'][0]['id']
        self.assertEqual(self.call(reviewer,'/requests/'+rid,{'action':'approve','hours':0.00001})[0],200)
        time.sleep(0.1)
        self.assertEqual(self.call(requester,'/documents/DEMO-DOC-2')[0],403)
        expired_state = self.call(requester,'/state')[1]
        self.assertEqual(next(r for r in expired_state['accessRequests'] if r['id']==rid)['status'],'expired')
        expiry_notices = [n for n in expired_state['notifications'] if n['kind']=='expired']
        self.assertEqual(len(expiry_notices),1)
        self.assertEqual(len([n for n in self.call(requester,'/state')[1]['notifications'] if n['kind']=='expired']),1)
        # Restart the backend, retaining disk state and the original client session.
        self.proc.terminate(); self.proc.wait(); self.proc.stdout.close(); type(self).start()
        self.assertEqual(self.call(officer,'/documents/'+did),(200,body))
        self.assertEqual(self.call(officer,'/cases/DEMO-NEW')[0],200)
        restored_notifications = self.call(requester,'/state')[1]['notifications']
        self.assertIsNotNone(next(n for n in restored_notifications if n['id']==approved_notice['id'])['read_at'])
        self.assertEqual(len([n for n in restored_notifications if n['kind']=='expired']),1)
        events = self.call(reviewer,'/state')[1]['auditLog']
        self.assertTrue(any('Revoked' in e['action'] for e in events))
        self.assertTrue(any('Downloaded' in e['action'] for e in events))
        self.assertTrue(any('Denied' in e['action'] for e in events))
        self.assertEqual(self.call(officer,'/logout',{})[0],200)
        self.assertEqual(self.call(officer,'/state')[0],401)
        import sqlite3
        with sqlite3.connect(self.env['CASEVAULT_DB']) as db:
            hashes = db.execute('SELECT hash FROM users').fetchall()
            self.assertTrue(all('Kochi' not in r[0] and len(r[0]) == 64 for r in hashes))
            self.assertEqual(db.execute('SELECT count(*) FROM documents WHERE name="bad.pdf"').fetchone()[0],0)
        print('Verified auth, persistence, upload validation, protected search/download, approval/rejection/expiry/revocation, audit and logout.')

if __name__ == '__main__': unittest.main()
