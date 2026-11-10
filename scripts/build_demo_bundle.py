"""Package committed runtime source, a freshly built frontend and offline wheels."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def runtime_paths(tracked):
    return [p for p in tracked if p.startswith(('backend/','configs/','artifacts/','scripts/'))
            or p in {'training/__init__.py','training/policy_features.py'}]


def build(output, wheels):
    if output.exists() or output.with_suffix('.zip').exists():
        raise ValueError('Use a new output path')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tracked = subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    runtime = runtime_paths(tracked)
    changed = subprocess.check_output(['git','diff','HEAD','--name-only','--',*runtime,'frontend/'],cwd=ROOT,text=True).strip()
    if changed:
        raise ValueError('Commit runtime changes before packaging: '+changed)
    subprocess.run(['pnpm','--dir','frontend','build'],cwd=ROOT,check=True,shell=True)
    output.mkdir(parents=True)
    for name in runtime:
        dest = output/'source'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT))
    shutil.copytree(ROOT/'frontend/dist',output/'frontend_dist')
    shutil.copytree(wheels,output/'wheelhouse')
    shutil.copy2(ROOT/'docs/evidence/B/independent_2026-11-07/api_runtime.lock.txt',output/'api_runtime.lock.txt')
    shutil.copy2(ROOT/'scripts/demo_acceptance.py',output/'accept.py')
    (output/'start.py').write_text('''import argparse
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'source'))
from backend.api.main import app
from fastapi.staticfiles import StaticFiles
app.mount('/', StaticFiles(directory=ROOT/'frontend_dist', html=True), name='frontend')
if __name__ == '__main__':
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    os.chdir(ROOT/'source')
    uvicorn.run(app, host='127.0.0.1', port=args.port)
''',encoding='utf-8')
    (output/'README.txt').write_text('''星地智调 · B 最终离线演示候选包
环境：Windows x64，Python 3.12。依赖轮子已包含，运行不需要 Node、Git 或联网。
请先解压到一个全新目录，在该目录执行：
  py -3.12 accept.py
验收将校验文件、创建 env、离线安装、检查页面与 API，执行 S1/S2/S3、健康对照和复跑并导出 ZIP。
所有日志位于 acceptance 下；失败不覆盖，请保留整份目录并在另一全新目录重试。
验收完成后启动：
  .\\env\\Scripts\\python.exe start.py
打开 http://127.0.0.1:8000，选择真实沙盒及 S1/S2/S3 并运行。
若默认端口已用，启动加 --port 8040；验收加 --port 8042。
真实演示中 EDF 为 S1/S3 全交付，Learned 为零交付；S2 两者均为零，保持原样展示。
演示为 synthetic/sandbox，不能替代正式540次结果或当作AI增益。
SOURCE_PROVENANCE.json 是本包来源。历史包不包含在当前运行源码内。
第二台物理机器需实际执行 accept.py；同机重复运行不能算作异机验收。
''',encoding='utf-8')
    def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = dict(schema_version='b-final-demo-v1',source_commit=commit,
                      formal_source_commit='48157a8f4a1cdd7770685b79deb3fe4524b1bf7d',
                      frontend_source_commit=commit,
                      runtime='Windows x64 / Python 3.12',scope='synthetic_sandbox',
                      trained_model_replaced=False,
                      model_sha256=sha(output/'source/artifacts/models/a_n3_policy_v1/weights.npz'),
                      frontend_sha256={p.relative_to(output/'frontend_dist').as_posix():sha(p) for p in sorted((output/'frontend_dist').rglob('*')) if p.is_file()})
    (output/'SOURCE_PROVENANCE.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sums = {p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'SHA256SUMS.json').write_text(json.dumps(sums,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive = output.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(output.rglob('*')):
            if path.is_file(): z.write(path,path.relative_to(output).as_posix())
    metadata = dict(zip=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),source_commit=commit,payload_files=len(sums))
    archive.with_suffix('.metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--wheels',type=Path,default=ROOT/'runs/b_independent_20261107/wheelhouse')
    args = parser.parse_args()
    build(args.output.resolve(),args.wheels.resolve())
