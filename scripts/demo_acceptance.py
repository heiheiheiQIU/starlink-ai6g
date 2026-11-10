"""Portable Windows offline installation and real HTTP acceptance (stdlib entry)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import sysconfig
import time
from urllib.request import build_opener, ProxyHandler
import venv


def runtime_supported():
    return sys.version_info[:2] == (3,12) and sysconfig.get_platform() == 'win-amd64'


def verify_integrity(root):
    root = Path(root).resolve()
    manifest = json.loads((root/'SHA256SUMS.json').read_text(encoding='utf-8'))
    for name, digest in manifest.items():
        path = root/name
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            raise ValueError('unsafe path: '+name)
        if not path.is_file():
            raise ValueError('missing: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('hash mismatch: '+name)
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if (rel.parts[0] in {'env', 'acceptance'} or '__pycache__' in rel.parts
                or rel.parts[:2] == ('source', 'runs')):
            continue
        if path.is_file() and rel.as_posix() not in {*manifest, 'SHA256SUMS.json'}:
            raise ValueError('unlisted payload: '+rel.as_posix())
    return len(manifest)


def run(root, port, output):
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Acceptance output already exists; keep each attempt separately')
    count = verify_integrity(root)
    if not runtime_supported():
        raise ValueError('Offline wheels require Python 3.12 / Windows x64')
    output.mkdir(parents=True)
    report = dict(status='running', scope='single_machine_offline_acceptance',
                  machine_fingerprint=hashlib.sha256(platform.node().encode()).hexdigest(),
                  platform=platform.platform(), python=sys.version, immutable_files=count,
                  started_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    def save():
        (output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    started = time.perf_counter()
    try:
        env_dir = root/'env'
        if env_dir.exists():
            raise ValueError('env already exists; extract a fresh copy for an independent attempt')
        venv.EnvBuilder(with_pip=True).create(env_dir)
        python = env_dir/'Scripts/python.exe'
        process_env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        with (output/'install.log').open('w',encoding='utf-8') as log:
            subprocess.run([str(python),'-m','pip','install','--no-index','--find-links',str(root/'wheelhouse'),'-r',str(root/'api_runtime.lock.txt')],check=True,stdout=log,stderr=subprocess.STDOUT,env=process_env)
            subprocess.run([str(python),'-m','pip','check'],check=True,stdout=log,stderr=subprocess.STDOUT,env=process_env)
        log = (output/'launcher.log').open('w',encoding='utf-8')
        server = subprocess.Popen([str(python),str(root/'start.py'),'--port',str(port)],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=process_env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            opener = build_opener(ProxyHandler({}))
            for _ in range(150):
                if server.poll() is not None:
                    raise RuntimeError('launcher exited')
                try:
                    with opener.open(f'http://127.0.0.1:{port}/',timeout=1) as response:
                        page = response.read().decode('utf-8')
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise TimeoutError('launcher readiness')
            assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"',page)
            if not assets:
                raise ValueError('Built frontend assets missing')
            for asset in assets:
                with opener.open(f'http://127.0.0.1:{port}'+asset,timeout=10) as response:
                    if not response.read():
                        raise ValueError('Empty frontend asset')
            with opener.open(f'http://127.0.0.1:{port}/openapi.json') as response:
                if '/runs' not in json.load(response)['paths']:
                    raise ValueError('Backend route missing')
            report['launcher_static_assets'] = assets
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait(timeout=5)
            log.close()
        with (output/'golden.log').open('w',encoding='utf-8') as log:
            subprocess.run([str(python),'-m','scripts.verify_sandbox','--port',str(port+1),'--output',str(output/'golden')],cwd=root/'source',check=True,stdout=log,stderr=subprocess.STDOUT,env=process_env)
        report['golden'] = json.loads((output/'golden/verification.json').read_text(encoding='utf-8'))
        verify_integrity(root)
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report['wall_seconds'] = time.perf_counter()-started
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--port',type=int,default=8030)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.root,args.port,args.output or args.root/'acceptance'/time.strftime('%Y%m%d_%H%M%S')),ensure_ascii=False,indent=2))
