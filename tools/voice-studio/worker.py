"""Bounded, offline-only speech worker; killed on timeout by server."""
import os
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
import json,re,sys
from pathlib import Path
import numpy as np
import torch
from scipy.io.wavfile import write
from transformers import AutoTokenizer,VitsModel
BASE=Path(__file__).resolve().parent

def split_text(text,limit=180):
    sentences=re.split(r'(?<=[.!?…])\s+|\n+',text.strip())
    chunks=[]
    for sentence in sentences:
        words=sentence.split(); current=''
        for word in words:
            if len(current)+len(word)+1>limit and current:
                chunks.append(current);current=''
            current=(current+' '+word).strip()
        if current:chunks.append(current)
    return chunks

def synthesize(request):
    torch.set_num_threads(min(4,os.cpu_count() or 2));torch.manual_seed(17)
    folder=BASE/'.models'/request['language']
    tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True)
    model=VitsModel.from_pretrained(folder,local_files_only=True).eval()
    model.speaking_rate=request['speed']
    sr=model.config.sampling_rate; pieces=[]
    for text in split_text(request['text']):
        inputs=tokenizer(text,return_tensors='pt')
        if inputs['input_ids'].numel()<2:raise ValueError('Matnda o‘qiladigan harflar topilmadi.')
        with torch.inference_mode():sound=model(**inputs).waveform.squeeze().cpu().numpy()
        if not np.isfinite(sound).all():raise ValueError('Ovoz yaratishda xato yuz berdi.')
        pieces.extend([sound,np.zeros(int(sr*.18),dtype=np.float32)])
    sound=np.concatenate(pieces[:-1]);peak=float(np.max(np.abs(sound)))
    if peak<1e-6:raise ValueError('Model bo‘sh ovoz yaratdi.')
    sound=sound/max(1,peak/.95)
    target=BASE/'outputs'/(request['id']+'.wav')
    write(target,sr,(sound*32767).astype(np.int16))
    return {'duration':round(len(sound)/sr,2),'sample_rate':sr}
if __name__=='__main__':
    print(json.dumps(synthesize(json.load(sys.stdin))))
