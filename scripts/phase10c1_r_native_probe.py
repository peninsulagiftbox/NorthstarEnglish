#!/usr/bin/env python3
"""Loopback-only test proxy: add a passive observer without changing the candidate build."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

PROBE = r'''(() => {
 const id = crypto.randomUUID(); let seq = 0; let last = '';
 const badge = document.createElement('output'); badge.id = 'r-native-probe';
 badge.style.cssText = 'position:fixed;top:0;right:0;z-index:99999;background:#fff8cd;color:#111;padding:8px;font:12px monospace;pointer-events:none';
 document.body.append(badge);
 const sample = (event, trusted = null) => {
  const a = document.querySelector('audio');
  const row = {id,seq:++seq,event,trusted,at:performance.now(),wall:Date.now(),
   visibility:document.visibilityState,paused:a?.paused??null,time:a?.currentTime??null,
   mode:document.querySelector('.player-bar')?.dataset.mode??null,
   sentence:document.querySelector('.player-bar')?.dataset.sentence??null};
  badge.textContent = `R ${id.slice(0,8)} ${row.visibility} ${row.paused?'paused':'playing'} ${row.time?.toFixed(3)??'-'} ${event}`;
  navigator.sendBeacon('/__r_probe/events',new Blob([JSON.stringify(row)],{type:'application/json'}));
 };
 document.addEventListener('visibilitychange',e=>sample(e.type,e.isTrusted));
 const attach = () => { const a=document.querySelector('audio'); if(a&&!a.dataset.rObserved){
  a.dataset.rObserved='true'; for(const n of ['play','playing','pause','seeked','ended','error']) a.addEventListener(n,e=>sample(e.type,e.isTrusted));
  sample('audio-attached');
 }};
 new MutationObserver(attach).observe(document.body,{childList:true,subtree:true});
 attach(); sample('observer-ready');
 setInterval(()=>{const a=document.querySelector('audio'); const k=`${document.visibilityState}:${a?.paused}`;if(k!==last){last=k;sample('state');}},250);
})();'''


def start(folder, upstream=3177, port=3175):
    lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == '/__r_probe.js':
                data = PROBE.encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/javascript; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.forward()

        def do_POST(self):
            if self.path == '/__r_probe/events':
                if self.headers.get('Origin') != f'http://127.0.0.1:{port}':
                    self.send_error(403, 'Same-origin test observer only')
                    return
                size = int(self.headers.get('Content-Length', '0'))
                assert 0 < size < 4096
                row = json.loads(self.rfile.read(size))
                assert set(row) == {'id','seq','event','trusted','at','wall','visibility','paused','time','mode','sentence'}
                row['receivedAtNs'] = time.time_ns()
                with lock, (folder / 'native-events.jsonl').open('a') as stream:
                    stream.write(json.dumps(row) + '\n')
                self.send_response(204)
                self.end_headers()
            else:
                self.forward()

        def do_PUT(self):
            self.forward()

        def do_HEAD(self):
            self.forward()

        def forward(self):
            connection = http.client.HTTPConnection('127.0.0.1', upstream, timeout=30)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                assert 0 <= size <= 1024 * 1024
                body = self.rfile.read(size) if size else None
                headers = {k:v for k,v in self.headers.items() if k.lower() not in {'connection','accept-encoding'}}
                headers['Accept-Encoding'] = 'identity'
                connection.request(self.command, self.path, body=body, headers=headers)
                response = connection.getresponse()
                data = response.read()
                if self.command == 'GET' and 'text/html' in response.getheader('Content-Type', '') and self.path.startswith('/lesson/c1-'):
                    assert response.getheader('Content-Encoding') is None
                    assert b'</body>' in data
                    data = data.replace(b'</body>', b'<script src="/__r_probe.js"></script></body>', 1)
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in {'content-length','transfer-encoding','connection','content-encoding'}:
                        self.send_header(key, value)
                self.send_header('Content-Length', response.getheader('Content-Length', '0') if self.command == 'HEAD' else str(len(data)))
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(data)
            except ConnectionRefusedError:
                self.send_error(503, 'Isolated upstream starting')
            finally:
                connection.close()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
