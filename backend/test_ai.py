"""Real HTTP/database tests; only outbound xAI transport is mocked."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import server
import ai_extraction as ai
import test_server

VALUES = {key: None for key in ai.FIELDS}
VALUES.update(fir_number='104/2024', police_station='Synthetic station', summary='A synthetic report.')

class ExtractionWorkflow(unittest.TestCase):
    client = test_server.Workflow.client
    call = test_server.Workflow.call

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.old_db = server.DB
        server.DB = Path(cls.temp.name) / 'ai.sqlite3'
        server.seed()
        cls.http = ThreadingHTTPServer(('127.0.0.1', 18090), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.thread.join()
        server.DB = cls.old_db
        cls.temp.cleanup()

    def setUp(self):
        with server.connect() as db:
            db.execute('DELETE FROM case_extractions')
            db.execute('DELETE FROM requests')
            db.execute('DELETE FROM audit')
            body = b'Synthetic exact original\n'
            db.execute('UPDATE documents SET body=?,sha256=? WHERE id=?', (body, hashlib.sha256(body).hexdigest(), 'DEMO-DOC-1'))
        self.officer = self.client('rmenon', 'Kochi@004')
        self.base = '/documents/DEMO-DOC-1'
        self.transport = patch.object(ai, 'request', side_effect=self.provider)
        self.mock = self.transport.start()
        self.key = patch.object(ai, 'api_key', return_value='synthetic-test-key')
        self.key.start()
        self.addCleanup(self.transport.stop); self.addCleanup(self.key.stop)

    def provider(self, path, key, payload=None, **kwargs):
        if path == '/files':
            self.assertIn(b'Synthetic exact original\n', payload)
            return {'id':'file-test'}
        if path == '/responses':
            self.assertEqual(payload['model'], ai.MODEL)
            self.assertTrue(payload['text']['format']['strict'])
            self.assertEqual(payload['text']['format']['schema'], ai.SCHEMA)
            self.assertFalse(payload['store'])
            self.assertEqual(payload['input'][0]['content'][1], {'type':'input_file','file_id':'file-test'})
            return {'status':'completed', 'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(VALUES)}]}]}
        self.assertEqual(path, '/files/file-test')
        self.assertEqual(kwargs['method'], 'DELETE')
        return {}

    def draft(self):
        status, result = self.call(self.officer, self.base + '/extractions', {})
        self.assertEqual(status, 201, result)
        return result

    def test_unauthorized_all_endpoints(self):
        anon = self.client()
        other = self.client('akumar','Kochi@001')
        for path, data in [('/integrity',{}),('/extractions',{}),('/extractions',None),('/extractions/made-up/confirm',{'fields':VALUES})]:
            self.assertEqual(self.call(anon,self.base+path,data)[0],401)
            self.assertEqual(self.call(other,self.base+path,data)[0],403)
        self.mock.assert_not_called()

    def test_success_draft_edit_confirm_persistence_and_linkage(self):
        before = self.call(self.officer, '/cases/2024-CR-104')[1]
        original = self.call(self.officer,self.base)[1]
        draft = self.draft()
        self.assertEqual(draft['status'],'draft')
        with server.connect() as db:
            r=db.execute('SELECT * FROM case_extractions').fetchone()
            self.assertIsNone(r['confirmed_at']); self.assertIsNone(r['confirmed_by'])
        edited = {**VALUES, 'summary':'Human corrected summary'}
        path=self.base+'/extractions/'+draft['id']
        self.assertEqual(self.call(self.officer,path+'/edit',{'fields':edited})[0],200)
        self.assertEqual(self.call(self.officer,path+'/confirm',{'fields':edited,'source_sha256':'forged','model':'forged','confirmed_by':'forged'})[0],200)
        server.seed()  # Additive migration on restart preserves metadata and originals.
        records=self.call(self.officer,self.base+'/extractions')[1]['records']
        r=records[0]
        self.assertEqual(r['fields'],edited);self.assertEqual(r['status'],'verified')
        self.assertEqual(r['source_sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(r['document_id'],'DEMO-DOC-1'); self.assertEqual(r['case_id'],'2024-CR-104')
        self.assertEqual(r['confirmed_by'],'OFF-004');self.assertIsNotNone(r['confirmed_at'])
        self.assertEqual(r['model'],ai.MODEL)
        self.assertEqual(self.call(self.officer,self.base)[1], original)
        self.assertEqual(self.call(self.officer,'/cases/2024-CR-104')[1],before)
        self.assertEqual(self.call(self.officer,path+'/confirm',{'fields':edited})[0],409)
        with server.connect() as db:
            events=' '.join(r[0] for r in db.execute('SELECT action FROM audit'))
        for name in ['AI extraction requested','AI extraction completed','Extracted data edited by user','Extracted information confirmed']:
            self.assertIn(name,events)
        self.assertNotIn('Human corrected summary',events);self.assertNotIn('synthetic-test-key',events)
        self.assertEqual(self.mock.call_args_list[-1].args[0],'/files/file-test')

    def test_missing_key_upload_still_works(self):
        with patch.object(ai,'api_key',return_value=''):
            status,result=self.call(self.officer,self.base+'/extractions',{})
        self.assertEqual((status,result),(503,{'error':'AI extraction unavailable'}))
        self.mock.assert_not_called()
        import base64
        status,_=self.call(self.officer,'/upload',dict(caseId='2024-CR-104',name='still-works.txt',content=base64.b64encode(b'Normal upload').decode(),documentType='FIR'))
        self.assertEqual(status,201)

    def test_bad_responses_are_safe_and_cleanup_attempted(self):
        for response in [{'status':'incomplete'}, {'status':'completed','output':[]},
                         {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'not JSON'}]}]},
                         {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"unexpected":"secret"}'}]}]}]:
            with self.subTest(response=response):
                self.mock.side_effect=lambda path,*a,**k: {'id':'file-test'} if path=='/files' else response if path=='/responses' else {}
                status,result=self.call(self.officer,self.base+'/extractions',{})
                self.assertEqual((status,result),(503,{'error':'AI extraction unavailable'}))
                self.assertEqual(self.mock.call_args.args[0],'/files/file-test')
        self.assertEqual(self.call(self.officer,self.base+'/extractions')[1]['records'],[])

    def test_timeout_credit_and_network_failures(self):
        from urllib.error import HTTPError, URLError
        for failure in [TimeoutError('sensitive'), URLError('sensitive'), HTTPError('url',402,'sensitive',{},None)]:
            self.mock.side_effect=failure
            self.assertEqual(self.call(self.officer,self.base+'/extractions',{}),(503,{'error':'AI extraction unavailable'}))
        with server.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM audit WHERE action LIKE 'AI extraction failed%'").fetchone()[0],3)

    def test_invalid_confirmation_and_discard(self):
        d=self.draft();path=self.base+'/extractions/'+d['id']
        self.assertEqual(self.call(self.officer,path+'/confirm',{'fields':{'summary':'fake'}})[0],400)
        self.assertEqual(self.call(self.officer,path+'/discard',{})[0],200)
        self.assertEqual(self.call(self.officer,path+'/confirm',{'fields':VALUES})[0],409)
        self.assertEqual(self.call(self.officer,self.base+'/extractions')[1]['records'],[])

    def test_integrity_success_and_failure_and_audit(self):
        self.assertTrue(self.call(self.officer,self.base+'/integrity',{})[1]['verified'])
        with server.connect() as db: db.execute("UPDATE documents SET body=? WHERE id='DEMO-DOC-1'",(b'Changed bytes',))
        self.assertFalse(self.call(self.officer,self.base+'/integrity',{'sha256':hashlib.sha256(b'Changed bytes').hexdigest()})[1]['verified'])
        with server.connect() as db:
            events=' '.join(r[0] for r in db.execute('SELECT action FROM audit'))
        self.assertIn('Integrity verification Verified document DEMO-DOC-1',events)
        self.assertIn('Integrity verification Verification Failed document DEMO-DOC-1',events)

    def test_changed_source_blocks_confirmation_and_extraction(self):
        d=self.draft()
        with server.connect() as db: db.execute("UPDATE documents SET body=? WHERE id='DEMO-DOC-1'",(b'Changed bytes',))
        self.assertEqual(self.call(self.officer,self.base+'/extractions/'+d['id']+'/confirm',{'fields':VALUES})[0],409)
        self.mock.reset_mock()
        self.assertEqual(self.call(self.officer,self.base+'/extractions',{})[0],503)
        self.mock.assert_not_called()

    def test_access_revoked_during_external_call(self):
        def provider(path,*args,**kwargs):
            result=self.provider(path,*args,**kwargs)
            if path=='/responses':
                with server.connect() as db: db.execute("DELETE FROM assignments WHERE user_id='OFF-004' AND case_id='2024-CR-104'")
            return result
        self.mock.side_effect=provider
        try:
            self.assertEqual(self.call(self.officer,self.base+'/extractions',{})[0],403)
            with server.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM case_extractions').fetchone()[0],0)
        finally:
            with server.connect() as db:db.execute("INSERT OR IGNORE INTO assignments VALUES('2024-CR-104','OFF-004')")

    def test_other_user_cannot_edit_draft_and_read_grant_cannot_confirm(self):
        other=self.client('akumar','Kochi@001')
        with server.connect() as db:
            db.execute("INSERT INTO requests VALUES('test-grant','2024-CR-104','OFF-001','test','approved',9999999999,NULL,0)")
        d=self.draft()
        self.assertEqual(self.call(other,self.base+'/extractions')[1]['records'],[])
        self.assertEqual(self.call(other,self.base+'/extractions/'+d['id']+'/edit',{'fields':VALUES})[0],403)
        status,d=self.call(other,self.base+'/extractions',{})
        self.assertEqual(status,201)
        self.assertEqual(self.call(other,self.base+'/extractions/'+d['id']+'/confirm',{'fields':VALUES})[0],403)

class AdapterValidation(unittest.TestCase):
    def test_image_input_and_temporary_file_cleanup_failure(self):
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(VALUES)}]}]}
        with patch.object(ai,'api_key',return_value='test-only'), patch.object(ai,'request',return_value=response) as transport:
            fields,model,cleanup=ai.extract({'mime':'image/png','body':b'image bytes'})
            self.assertEqual(fields,VALUES)
            self.assertEqual(transport.call_count,1)
            attachment=transport.call_args.args[2]['input'][0]['content'][1]
            self.assertEqual(attachment['type'],'input_image')
            self.assertTrue(attachment['image_url'].startswith('data:image/png;base64,'))
        def provider(path,*args,**kwargs):
            if path=='/files':return {'id':'file-test'}
            if path=='/responses':return response
            raise TimeoutError()
        with patch.object(ai,'api_key',return_value='test-only'), patch.object(ai,'request',side_effect=provider):
            self.assertTrue(ai.extract({'mime':'text/plain','body':b'test'})[2])

    def test_unsupported_and_oversized_files_not_sent(self):
        with patch.object(ai,'api_key',return_value='test-only'), patch.object(ai,'request') as transport:
            for doc in [{'mime':'video/mp4','body':b'test'}, {'mime':'text/plain','body':b'x'*(ai.MAX_AI_FILE+1)}]:
                with self.assertRaises(ai.Unavailable):ai.extract(doc)
            transport.assert_not_called()


    def test_schema_rejects_nested_extra_and_oversized_fields(self):
        for value in [[],{**VALUES,'extra':'x'},{**VALUES,'summary':{}},{**VALUES,'summary':'x'*4001}]:
            with self.assertRaises(ValueError):ai.validate_fields(value)

    def test_environment_key_and_no_key(self):
        with patch.dict(os.environ,{'XAI_API_KEY':'test-only'}):self.assertEqual(ai.api_key(),'test-only')
        with patch.dict(os.environ,{'XAI_API_KEY':''}):self.assertEqual(ai.api_key(),'')

if __name__=='__main__':unittest.main()
