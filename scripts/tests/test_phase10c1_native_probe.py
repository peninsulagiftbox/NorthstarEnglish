"""Verify test instrumentation preserves real media and local write boundaries."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase10c1_r_native_probe as probe


class ProbeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.folder=Path(self.temp.name)
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                data=b'original-media-bytes' if self.path=='/audio' else b'<html><body>original app</body></html>'
                partial=self.path=='/audio' and self.headers.get('Range')=='bytes=0-3'
                if partial:data=data[:4]
                self.send_response(206 if partial else 200)
                self.send_header('Content-Type','audio/mpeg' if self.path=='/audio' else 'text/html')
                self.send_header('Content-Length',str(len(data)))
                if partial:self.send_header('Content-Range','bytes 0-3/20')
                self.end_headers()
                self.wfile.write(data)
            def do_HEAD(self):
                self.send_response(200)
                self.send_header('Content-Length','20')
                self.end_headers()
        self.upstream=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        threading.Thread(target=self.upstream.serve_forever,daemon=True).start()
        self.server,_=probe.start(self.folder,upstream=self.upstream.server_port,port=0)

    def tearDown(self):
        for server in [self.server,self.upstream]:server.shutdown();server.server_close()
        self.temp.cleanup()

    def call(self,path,method='GET',body=None,headers=None):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            client.request(method,path,body=body,headers=headers or {})
            response=client.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally:client.close()

    def test_only_test_lesson_html_gets_observer(self):
        status,_,data=self.call('/lesson/c1-shared')
        self.assertEqual(200,status)
        self.assertIn(b'original app',data)
        self.assertEqual(1,data.count(b'<script src="/__r_probe.js"></script>'))
        self.assertEqual(b'<html><body>original app</body></html>',self.call('/dashboard')[2])

    def test_media_range_and_head_are_preserved(self):
        self.assertEqual(b'original-media-bytes',self.call('/audio')[2])
        status,headers,data=self.call('/audio',headers={'Range':'bytes=0-3'})
        self.assertEqual((206,b'orig'),(status,data))
        self.assertEqual('bytes 0-3/20',headers['Content-Range'])
        self.assertEqual('4',headers['Content-Length'])
        self.assertEqual('20',self.call('/audio',method='HEAD')[1]['Content-Length'])

    def test_observer_rejects_other_origin_without_writing(self):
        status,_,_=self.call('/__r_probe/events',method='POST',body='{}',headers={'Origin':'https://invalid.example'})
        self.assertEqual(403,status)
        self.assertFalse((self.folder/'native-events.jsonl').exists())


if __name__=='__main__':unittest.main()
