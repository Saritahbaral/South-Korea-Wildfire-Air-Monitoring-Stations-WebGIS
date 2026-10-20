"""Serve the bundled viewer locally. No third-party Python packages required."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
 for port in range(8765,8776):
  try:
   server=ThreadingHTTPServer(('127.0.0.1',port),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
   break
  except OSError:
   continue
 else: raise SystemExit('Ports 8765–8775 are busy. Close another viewer and retry.')
 url=f'http://127.0.0.1:{port}/'
 print('Wildfire viewer:',url,'\nKeep this window open. Press Ctrl+C to stop.')
 webbrowser.open(url)
 try: server.serve_forever()
 except KeyboardInterrupt: pass
 finally: server.server_close()
