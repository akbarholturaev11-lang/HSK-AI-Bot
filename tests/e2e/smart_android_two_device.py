"""Owned-emulator TLS/native SQL acceptance. No production credentials/provider.

Run with a disposable loopback SMART_REMINDER_TEST_DATABASE_URL, two .qa APK
installs, and a generated loopback SAN certificate/key. The test never logs
native tokens, reads real users, publishes APKs or enables the real router.
"""
import argparse
import asyncio
import json
from pathlib import Path
import re
import shlex

from fastapi import FastAPI
import uvicorn

from app.api.smart_reminder import create_smart_reminder_router
from app.services.smart_reminder_android import GRANT
from app.services.smart_reminder_shadow_queue import ATTEMPT
from tests.test_smart_reminder_android import PostgreSQLAndroidProtocolTests


async def command(*args,payload=None):
    process=await asyncio.create_subprocess_exec(*args,stdin=asyncio.subprocess.PIPE if payload else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
    output=(await process.communicate(payload))[0].decode()
    if process.returncode: raise RuntimeError(f"Owned QA command failed: {args[0]}")
    return output


async def scenario(args, *, unknown_other):
    case=PostgreSQLAndroidProtocolTests(methodName='test_mode_is_read_only_sticky_observation_and_not_authority')
    await case.asyncSetUp()
    server=None
    task=None
    name='unknown-other' if unknown_other else 'two-compatible'
    try:
        await case.second_installation(capable=not unknown_other)
        app=FastAPI()
        app.include_router(create_smart_reminder_router(session_factory=case.sessions,settings_obj=case.settings,
            android_delivery_factory=case.service))
        paths={}
        @app.middleware('http')
        async def counts(request,call_next):
            result=await call_next(request)
            key=request.method+' '+request.url.path
            paths[key]=paths.get(key,0)+1
            return result
        config=uvicorn.Config(app,host='127.0.0.1',port=args.port,ssl_certfile=str(args.cert),
            ssl_keyfile=str(args.key),log_level='error',access_log=False)
        server=uvicorn.Server(config)
        task=asyncio.create_task(server.serve())
        for _ in range(100):
            if server.started: break
            if task.done(): await task
            await asyncio.sleep(.05)
        if not server.started: raise RuntimeError('Owned TLS server did not start')
        selected=args.serials[:1] if unknown_other else args.serials
        expected=[0] if unknown_other else [1,0]
        async def device(serial,uid,wanted):
            avd=await command(args.adb,'-s',serial,'emu','avd','name')
            if avd.splitlines()[0] not in args.owned_avds: raise RuntimeError('Refusing unrelated emulator')
            await command(args.adb,'-s',serial,'reverse',f'tcp:{args.port}',f'tcp:{args.port}')
            headers=await case.bearer(uid)
            fixture=args.output/f'{name}-{uid}.json'
            fixture.write_text(json.dumps(dict(origin=f'https://127.0.0.1:{args.port}',
                access_token=headers['Authorization'].removeprefix('Bearer '),certificate_pem=args.cert.read_text(),
                job_id=case.job_id,local_day=case.tick.date().isoformat(),expected_posts=wanted)))
            fixture.chmod(0o600)
            relative=f'cache/smart-two-{name}-{uid}.json'
            remote=f'/data/user/0/com.pomp.hskai.qa/{relative}'
            try:
                await command(args.adb,'-s',serial,'shell','run-as','com.pomp.hskai.qa','sh','-c',
                    shlex.quote(f'cat > {relative}'),payload=fixture.read_bytes())
                result=await command(args.adb,'-s',serial,'shell','am','instrument','-w','-r','-e','smart_fixture',remote,
                    '-e','class','com.pomp.hskai.core.notify.SmartStudyTwoDeviceTest',
                    'com.pomp.hskai.qa.test/androidx.test.runner.AndroidJUnitRunner')
                (args.output/f'{name}-{uid}-instrumentation.log').write_text(result)
                if 'OK (1 test)' not in result or 'FAILURES' in result or 'INSTRUMENTATION_FAILED' in result:
                    raise RuntimeError('Isolated native HTTP instrumentation failed; inspect bounded log')
                return dict(serial=serial,posts=wanted,passed=True)
            finally:
                fixture.unlink(missing_ok=True)
                await command(args.adb,'-s',serial,'shell','run-as','com.pomp.hskai.qa','rm','-f',relative)
                await command(args.adb,'-s',serial,'reverse','--remove',f'tcp:{args.port}')
        devices=await asyncio.gather(*(device(serial,uid,posts) for uid,(serial,posts) in enumerate(zip(selected,expected),1)))
        grants=await case.rows(GRANT)
        attempts=await case.rows(ATTEMPT)
        if len(grants)!=(0 if unknown_other else 1) or len(attempts)!=len(grants):
            raise RuntimeError('Unexpected canonical issuance/attempt count')
        if grants and (grants[0]['device_id']!='device-1' or grants[0]['receipt_outcome']!='client_posted_unverified'):
            raise RuntimeError('Unexpected selected-device outcome')
        required=('GET /api/v3/android/smart-reminder/mode','GET /api/v3/android/smart-reminder/due')
        if any(paths.get(path,0)<1 for path in required): raise RuntimeError('Live protocol was not exercised')
        report=dict(scenario=name,synthetic_only=True,devices=devices,grants=len(grants),attempts=len(attempts),
            outcome=grants[0]['receipt_outcome'] if grants else None,http_counts=paths,
            not_proven=['real FCM','signed installed production build','historical APK account execution','fleet fencing','canary'])
        (args.output/f'{name}-summary.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(scenario=name,grants=len(grants),posts=sum(expected),passed=True)),flush=True)
    finally:
        if server: server.should_exit=True
        if task: await task
        await case.asyncTearDown()


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb',required=True)
    parser.add_argument('--serials',nargs=2,required=True)
    parser.add_argument('--owned-avds',nargs=2,required=True)
    parser.add_argument('--cert',type=Path,required=True)
    parser.add_argument('--key',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',type=int,default=58443)
    args=parser.parse_args()
    if not 1024<=args.port<=65535 or len(set(args.serials))!=2 or any(not re.fullmatch(r'emulator-\d+',s) for s in args.serials):
        parser.error('Use two distinct explicit owned emulator serials and an unprivileged port')
    if not all(name.startswith('Codex_Smart_Mixed_') for name in args.owned_avds):
        parser.error('Use dedicated Codex_Smart_Mixed_ AVDs only')
    args.output.mkdir(parents=True,exist_ok=True)
    await scenario(args,unknown_other=False)
    await scenario(args,unknown_other=True)


if __name__=='__main__': asyncio.run(main())
