"""Personal loopback-only text-to-speech studio."""
import json,re,secrets,subprocess,sys,threading,uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel,Field,field_validator
from typing import Literal
BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs';OUT.mkdir(exist_ok=True)
TOKEN=secrets.token_urlsafe(32)
app=FastAPI(docs_url=None,redoc_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
pool=ThreadPoolExecutor(max_workers=1);lock=threading.Lock();jobs={}
class Speech(BaseModel):
    language:Literal['tj','ru']
    text:str=Field(min_length=1,max_length=1500)
    speed:float=Field(default=1,ge=.75,le=1.35)
    @field_validator('text')
    @classmethod
    def readable(cls,value):
        value=value.strip()
        if not re.search('[А-Яа-яЁёӢӣӮӯҚқҒғҲҳҶҷ]',value):raise ValueError('Ruscha yoki tojikcha kirill matn kiriting.')
        if any(len(word)>180 for word in value.split()):raise ValueError('Juda uzun so‘z topildi.')
        return value
@app.middleware('http')
async def local_security(request:Request,call_next):
    if request.method=='POST' and not secrets.compare_digest(request.headers.get('x-studio-token',''),TOKEN):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Sahifani yangilang va qayta urinib ko‘ring.'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response
@app.get('/',response_class=HTMLResponse)
def home():
    return (BASE/'static/index.html').read_text().replace('__TOKEN__',TOKEN)
@app.get('/api/status')
def status():
    return {'app':'voice-studio','models':{lang:all((BASE/'.models'/lang/file).exists() for file in ['model.safetensors','config.json','vocab.json']) for lang in ['tj','ru']}}
def run_job(job_id,payload):
    try:
        result=subprocess.run([sys.executable,str(BASE/'worker.py')],input=json.dumps({**payload,'id':job_id}),text=True,capture_output=True,timeout=180,cwd=BASE)
        if result.returncode:
            print('Speech worker failed:',result.stderr[-1800:],file=sys.stderr)
            raise RuntimeError('Ovoz yaratilmagan. Qisqaroq matn bilan qayta urinib ko‘ring; model fayllarini tekshiring.')
        info=json.loads(result.stdout.strip().splitlines()[-1]);info.update(id=job_id,status='done',language=payload['language'],url=f'/audio/{job_id}.wav')
        (OUT/f'{job_id}.json').write_text(json.dumps(info))
        with lock:jobs[job_id]=info
    except subprocess.TimeoutExpired:
        with lock:jobs[job_id]={'status':'error','error':'Vaqt chegarasi tugadi (3 daqiqa). Matnni qisqartiring.'}
    except Exception as exc:
        with lock:jobs[job_id]={'status':'error','error':str(exc)}
@app.post('/api/speech',status_code=202)
def speech(body:Speech):
    if not status()['models'][body.language]:raise HTTPException(409,'Model yuklanmagan. Install.command faylini ishga tushiring.')
    with lock:
        if any(j['status']=='running' for j in jobs.values()):raise HTTPException(409,'Oldingi ovoz tayyor bo‘lishini kuting.')
        job_id=uuid.uuid4().hex;jobs[job_id]={'status':'running'}
        if len(jobs)>100:
            for old in list(jobs)[:-50]:jobs.pop(old,None)
    pool.submit(run_job,job_id,body.model_dump())
    return {'id':job_id,'status':'running'}
@app.get('/api/jobs/{job_id}')
def job(job_id:str):
    with lock:result=jobs.get(job_id)
    if result is None:raise HTTPException(404,'Ovoz topilmadi.')
    return result
@app.get('/audio/{filename}')
def audio(filename:str):
    if not re.fullmatch('[a-f0-9]{32}\.wav',filename):raise HTTPException(404)
    path=OUT/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,media_type='audio/wav',filename=filename)
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8766)
