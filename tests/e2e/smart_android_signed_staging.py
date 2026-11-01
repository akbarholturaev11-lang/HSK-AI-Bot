"""Explicit, one-shot synthetic signed-staging acceptance on two owned AVDs.

Install the separately signed .qa Direct/Play apps and matching test APKs first.
Use only the private operator fixture, never a real account/phone. No DB reset,
provider, APK publication or automatic retry after an uncertain result.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile


async def command(*args):
    process=await asyncio.create_subprocess_exec(*map(str,args),stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT)
    try:
        output=(await asyncio.wait_for(process.communicate(),180))[0].decode()
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError('Owned QA command timed out; preserve unknown outcomes') from None
    if process.returncode: raise RuntimeError('Owned QA command failed: '+str(args[0]))
    return output


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb',type=Path,required=True)
    parser.add_argument('--serials',nargs=2,required=True)
    parser.add_argument('--owned-avds',nargs=2,required=True)
    parser.add_argument('--private-input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--continue-stored',action='store_true',
        help='Use retained encrypted credentials after an inspected pre-claim failure; never reseed')
    parser.add_argument('--positive-case',action='store_true',
        help='Use the independent second synthetic account after ordinary acknowledged logout')
    parser.add_argument('--clock-case',action='store_true',help='Use the third exact-clock synthetic account')
    args=parser.parse_args()
    if args.positive_case and args.clock_case: parser.error('Choose one explicit synthetic case')
    if (len(set(args.serials))!=2 or any(not re.fullmatch(r'emulator-\d+',s) for s in args.serials) or
            len(set(args.owned_avds))!=2 or any(not s.startswith('Codex_Smart_Mixed_') for s in args.owned_avds)):
        parser.error('Use two explicit dedicated owned Smart Mixed emulators')
    if args.private_input.stat().st_mode & 0o077:
        parser.error('Private operator fixture must be owner-only')
    private=json.loads(args.private_input.read_text())
    until=datetime.fromisoformat(private['HSK_SMART_QA_UNTIL'])
    if until.tzinfo is None or until<=datetime.now(timezone.utc):
        parser.error('Operator window expired; never reseed/retry implicitly')
    args.output.mkdir(parents=True,exist_ok=True)
    day=datetime.now(timezone.utc).date().isoformat()
    package='com.pomp.hskai.qa'
    folder='/sdcard/Android/data/'+package+'/files'
    remote=folder+'/smart-signed-input.json'
    async def device(index,initial):
        serial=args.serials[index]
        avd=await command(args.adb,'-s',serial,'emu','avd','name')
        if avd.splitlines()[0]!=args.owned_avds[index]: raise RuntimeError('Refuse unrelated emulator')
        install_proof=initial and not args.continue_stored
        body=dict(fixture_version='smart-qa-synthetic-v1'+(':clock' if args.clock_case else ':positive' if args.positive_case else ''),
            local_day=day,initial=install_proof,replace_link=install_proof and (args.positive_case or args.clock_case),
            expected_active=1 if initial and index==0 else 0,expected_operations=1 if index==0 else 0)
        if install_proof: body['refresh_token']=private['HSK_SMART_QA_REFRESH_'+str(index+1)]
        label=('initial' if initial else 'restart')+'-'+str(index+1)
        await command(args.adb,'-s',serial,'shell','am','force-stop',package)
        await command(args.adb,'-s',serial,'shell','mkdir','-p',folder)
        with tempfile.TemporaryDirectory(prefix='smart-signed-',dir=args.output) as tmp:
            local=Path(tmp)/'input.json'
            local.write_text(json.dumps(body)); local.chmod(0o600)
            try:
                await command(args.adb,'-s',serial,'push',local,remote)
                result=await command(args.adb,'-s',serial,'shell','am','instrument','-w','-r',
                    '-e','smart_fixture',remote,'-e','class',
                    'com.pomp.hskai.core.notify.SmartStudySignedStagingTest#signedAppRefreshesAndRunsItsActualCoordinator',
                    package+'.test/androidx.test.runner.AndroidJUnitRunner')
                (args.output/(label+'.log')).write_text(result)
                if ('OK (1 test)' not in result or 'FAILURES' in result or 'INSTRUMENTATION_FAILED' in result):
                    raise RuntimeError('Signed staging test failed; inspect bounded log, do not retry automatically')
                evidence=await command(args.adb,'-s',serial,'shell','cat',folder+'/smart-signed-result.json')
                parsed=json.loads(evidence)
                if parsed['debuggable'] or parsed['active_notifications']!=body['expected_active']:
                    raise RuntimeError('Unexpected signed staging result')
                (args.output/(label+'.json')).write_text(json.dumps(parsed,indent=2)+'\n')
            finally:
                await command(args.adb,'-s',serial,'shell','rm','-f',remote)
                await command(args.adb,'-s',serial,'shell','am','force-stop',package)
    for initial in (True,False):
        # Preserve both device logs/cleanup even if one fails. Never retry a
        # partly executed pair or reset its durable grant/credential state.
        results=await asyncio.gather(*(device(index,initial) for index in (0,1)),return_exceptions=True)
        if any(isinstance(result,BaseException) for result in results):
            raise RuntimeError('Signed staging pair failed; inspect both logs before any further action')
    print('SIGNED_STAGING_PASS: 4 device tests; selected=1, other=0, restart duplicates=0; synthetic only')


if __name__=='__main__': asyncio.run(main())
