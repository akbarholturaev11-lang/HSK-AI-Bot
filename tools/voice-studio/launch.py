"""Open an existing studio or start one; works on macOS and Windows."""
import subprocess,sys,time,webbrowser,json
from pathlib import Path
from urllib.request import urlopen
URL='http://127.0.0.1:8766'
def running():
    try:
        with urlopen(URL+'/api/status',timeout=1) as r:return json.load(r).get('app')=='voice-studio'
    except Exception:return False
if running():webbrowser.open(URL)
else:
    process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py'))])
    try:
        for _ in range(40):
            if running():webbrowser.open(URL);break
            if process.poll() is not None:raise SystemExit('Server ishga tushmadi. 8766 portini tekshiring.')
            time.sleep(.5)
        print('Ovoz studiyasi ochiq. To‘xtatish uchun Ctrl+C bosing.')
        process.wait()
    except KeyboardInterrupt:process.terminate();process.wait()
