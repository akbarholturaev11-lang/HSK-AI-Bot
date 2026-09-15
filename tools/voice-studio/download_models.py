"""One-time model download. Text synthesis never uses the network."""
import os
from pathlib import Path
os.environ['HF_HUB_DISABLE_XET']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
from huggingface_hub import snapshot_download
BASE=Path(__file__).resolve().parent
for lang,repo,revision in [('tj','facebook/mms-tts-tgk','df7cb4bd7ab732587045120cb502d5bda8d8c68c'),('ru','facebook/mms-tts-rus','a6f0f76c028c49175f42074ee79bd3e17ee1dd47')]:
    print(f'Downloading {repo}',flush=True)
    snapshot_download(repo, revision=revision, local_dir=BASE/'.models'/lang,
        allow_patterns=['config.json','model.safetensors','tokenizer_config.json','special_tokens_map.json','vocab.json','README.md'],max_workers=2)
    print(f'{lang}: ready',flush=True)
