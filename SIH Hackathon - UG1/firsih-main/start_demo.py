"""Start the local demo; use installed Node or this Mac's bundled runtime."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
BUNDLE = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies'

def main():
    node = shutil.which('node') or str(BUNDLE / 'node/bin/node')
    if not Path(node).is_file():
        raise SystemExit('Install Node.js LTS from https://nodejs.org/en/download, reopen Terminal, and retry.')
    env = dict(os.environ)
    env['PATH'] = str(Path(node).parent) + os.pathsep + env.get('PATH', '')
    env['CASEVAULT_API_PORT'] = '8001'
    env['PORT'] = '8001'
    env['APP_ORIGIN'] = 'http://localhost:5173'
    if not (ROOT / 'frontend/node_modules/vite/bin/vite.js').is_file():
        npm = shutil.which('npm', path=env['PATH'])
        pnpm = BUNDLE / 'bin/fallback/pnpm'
        command = [npm, 'install'] if npm else [str(pnpm), 'install', '--ignore-scripts']
        if not npm and not pnpm.exists():
            raise SystemExit('npm is missing. Install Node.js LTS, reopen Terminal, and retry.')
        print('Installing frontend dependencies for the first launch…', flush=True)
        subprocess.run(command, cwd=ROOT / 'frontend', env=env, check=True)
    children = []
    try:
        backend = subprocess.Popen([sys.executable, '-B', str(ROOT/'backend/server.py')], cwd=ROOT, env=env)
        children.append(backend)
        ready = False
        for _ in range(150):
            time.sleep(0.1)
            if backend.poll() is not None:
                raise SystemExit('Backend could not start. Stop any previous launcher using port 8001 and retry.')
            try:
                urllib.request.urlopen('http://127.0.0.1:8001/api/me', timeout=1).close()
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    ready = True
                    break
            except OSError:
                pass
        if not ready:
            raise SystemExit('Backend did not become ready. Check the error above.')
        frontend = subprocess.Popen([node, 'node_modules/vite/bin/vite.js'], cwd=ROOT/'frontend', env=env)
        children.append(frontend)
        for _ in range(100):
            time.sleep(0.1)
            if frontend.poll() is not None:
                raise SystemExit('Frontend could not start. Stop any previous frontend using port 5173 and retry.')
            try:
                with urllib.request.urlopen('http://localhost:5173', timeout=1) as r:
                    if r.status == 200:
                        print('\nREADY: open http://localhost:5173\nKeep this terminal open. Ctrl+C stops the demo.\n', flush=True)
                        break
            except OSError:
                pass
        else:
            raise SystemExit('Frontend did not become ready. Check the error above.')
        while all(p.poll() is None for p in children):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\nStopping the demo; saved files remain in backend/data/casevault.sqlite3.')
    finally:
        for p in children:
            if p.poll() is None: p.terminate()
        for p in children:
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()

if __name__ == '__main__': main()
