"""Live API and browser smoke test. Run with the studio server running."""
import json,re,time,wave,shutil
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
BASE=Path(__file__).resolve().parents[1];URL='http://127.0.0.1:8766'
def call(path,body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token:headers['X-Studio-Token']=token
    req=Request(URL+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urlopen(req,timeout=10) as r:return json.load(r)
with urlopen(URL) as r:html=r.read().decode()
token=re.search('name="studio-token" content="([^"]+)"',html).group(1)
for body,auth,expected in [({'language':'tj','text':'Салом'},None,403),({'language':'xx','text':'Салом'},token,422),({'language':'ru','text':'   '},token,422),({'language':'ru','text':'Привет','speed':5},token,422)]:
    try:call('/api/speech',body,auth);raise AssertionError('Invalid request accepted')
    except HTTPError as e:assert e.code==expected,(e.code,expected)
for lang,text in [('tj','Салом! Ин овоз дар компютери шумо сохта мешавад.'),('ru','Здравствуйте! Этот голос создан на вашем компьютере.')]:
    start=time.monotonic();item=call('/api/speech',{'language':lang,'text':text,'speed':1},token)
    try:call('/api/speech',{'language':lang,'text':text},token);raise AssertionError('Concurrent job accepted')
    except HTTPError as e:assert e.code==409
    while time.monotonic()-start<190:
        result=call('/api/jobs/'+item['id'])
        if result['status']!='running':break
        time.sleep(1)
    assert result['status']=='done',result
    with urlopen(URL+result['url']) as r:data=r.read()
    assert len(data)>10000
    path=BASE/'outputs'/f'sample-{lang}.wav';path.write_bytes(data)
    with wave.open(str(path)) as w:
        assert w.getframerate()==16000
        assert w.getnframes()>16000
    print(lang,result,'wall_seconds',round(time.monotonic()-start,2),flush=True)
print('API validation, concurrency and both real voices passed.',flush=True)
