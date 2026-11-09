"""Launch/reuse a loopback-only local app. No global services or startup changes."""
from pathlib import Path
import argparse,json,os,socket,subprocess,sys,time,urllib.request,webbrowser

ROOT=Path(__file__).resolve().parent

def health(port,data_dir=None):
    try:
      with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1) as r:data=json.load(r)
      same_root=str(data.get('instance_root','')).replace('\\','/').casefold()==str(ROOT).replace('\\','/').casefold()
      same_data=data_dir is None or str(data.get('data_directory','')).replace('\\','/').casefold()==str(Path(data_dir).resolve()).replace('\\','/').casefold()
      return data if data.get('app_id')=='company_knowledge_graph' and same_root and same_data else None
    except Exception:return None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');parser.add_argument('--stop',action='store_true');parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    if args.stop:
      state=ROOT/'data/running.json'
      if not state.exists():print('No app instance was started by this launcher.');return
      saved=json.loads(state.read_text(encoding='utf-8'))
      if str(saved.get('root','')).casefold()!=str(ROOT).casefold() or not health(int(saved['port']),saved.get('data_directory')):
        print('This app instance is already stopped.');return
      import signal
      os.kill(int(saved['pid']),signal.SIGTERM)
      print('Company Knowledge Graph stopped.');return
    if not (ROOT/'frontend/dist/index.html').exists():raise SystemExit('The bundled interface is missing. See README.md for rebuilding the frontend.')
    try:import fastapi,uvicorn,yfinance
    except ImportError as e:raise SystemExit(f'Missing dependency: {e}. Run: "{sys.executable}" -m pip install -r "{ROOT / "requirements.txt"}"')
    data=ROOT/'data';data.mkdir(exist_ok=True)
    expected_data=Path(os.environ.get('CKG_DATA_DIR',str(data))).resolve()
    current=None;port=args.port
    # Prefer the saved instance; otherwise inspect only the documented loopback port range.
    state=data/'running.json'
    if state.exists():
      try:
        saved=json.loads(state.read_text(encoding='utf-8'));candidate=int(saved['port'])
        if health(candidate,expected_data):port=candidate;current=health(candidate,expected_data)
      except Exception:pass
    if not current:
      for candidate in range(args.port,args.port+10):
        found=health(candidate,expected_data)
        if found:port=candidate;current=found;break
        with socket.socket() as s:
          try:s.bind(('127.0.0.1',candidate));port=candidate;break
          except OSError:continue
      else:raise SystemExit('No available loopback port in the configured range.')
    if not current:
      log=open(data/'server.log','ab',buffering=0)
      flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
      process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=flags)
      for _ in range(150):
        current=health(port,expected_data)
        if current:break
        if process.poll() is not None:raise SystemExit(f'App startup failed. Read {data / "server.log"}')
        time.sleep(.2)
      if not current:raise SystemExit(f'App is still starting. Read {data / "server.log"}')
      state.write_text(json.dumps(dict(pid=process.pid,port=port,root=str(ROOT),data_directory=str(expected_data))),encoding='utf-8')
    url=f'http://127.0.0.1:{port}'
    if not args.no_browser:webbrowser.open(url)
    print(json.dumps(dict(url=url,revision=current.get('revision'),companies=current.get('counts',{}).get('companies'),root=str(ROOT))))

if __name__=='__main__':main()
