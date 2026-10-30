import json
import re
import subprocess
from pathlib import Path


SUBSCRIPTION_HTML = Path("app/static/subscription.html")


def _html() -> str:
    return SUBSCRIPTION_HTML.read_text(encoding="utf-8")


def test_subscription_checkout_keeps_backend_contracts():
    html = _html()
    for marker in (
        "/api/subscription-miniapp/overview",
        "/api/subscription-miniapp/discount-start",
        "/api/subscription-miniapp/quote",
        "/api/subscription-miniapp/event",
        "/api/subscription-miniapp/submit",
        "X-Telegram-Init-Data",
    ):
        assert marker in html


def test_subscription_checkout_routes_banks_and_permanent_unlock_separately():
    html = _html()
    functions = []
    for name in ("hasMethodStep", "isHsk30Unlock", "flow"):
        match = re.search(r"function " + name + r"\([^)]*\)\{[\s\S]*?\}", html)
        assert match is not None
        functions.append(match.group(0))
    script = (
        'const state={mode:"subscription",plan:"1_month",done:false,pending:false};'
        + "\n".join(functions)
        + '\nconst results={}; for(const region of ["tj","uz","ru","cn","other"]){'
        + 'state.region=region;state.mode="subscription";results[region]=flow();'
        + 'state.mode="hsk30_unlock";results[region+"_unlock"]=flow();}'
        + '\nstate.pending=true;results.pending=flow();console.log(JSON.stringify(results));'
    )
    results = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    for region in ("tj", "cn"):
        assert results[region] == ["country", "plans", "method", "pay"]
        assert results[region + "_unlock"] == ["country", "method", "pay"]
    for region in ("uz", "ru", "other"):
        assert results[region] == ["country", "plans", "pay"]
        assert results[region + "_unlock"] == ["country", "pay"]
    assert results["pending"] == ["done"]
    assert "Dushanbe City" in html
    assert "«На карту»" in html
    assert 'id="qrPreview"' in html
    assert 'cn:"🇨🇳"' in html


def test_subscription_checkout_preserves_discount_modes():
    html = _html()
    for mode in ("subscription", "referral_discount", "admin_discount", "feedback_discount"):
        assert mode in html

def test_checkout_telemetry_requires_ack_and_retries_only_transient_failures():
    html = _html()
    start = html.index("async function trackSubscriptionStage(stage){")
    end = html.index("/* Sekin internetda", start)
    snippet = html[start:end]
    script = (
        'const state={preview:false,plan:"1_month",method:"visa"};'
        'const INIT_DATA="signed-test";const API={event:"/api/subscription-miniapp/event"};'
        'function contextPayload(){return {attempt_id:"sub-test"}};'
        'const warnings=[];console.warn=(...parts)=>warnings.push(parts);'
        + snippet
        + """
async function check(items){
  let count=0;
  globalThis.fetch=async()=>{
    count++;
    const item=items.shift();
    if(item==="network")throw new Error("offline");
    return {status:item.status,ok:item.status>=200&&item.status<300,
      json:async()=>item.body};
  };
  const success=await trackSubscriptionStage("payment_instructions_viewed");
  return {success,count};
}
(async()=>{
  const outcomes={
    acknowledged:await check([{status:200,body:{ok:true}}]),
    recovered:await check([{status:503,body:{ok:false}},{status:200,body:{ok:true}}]),
    forbidden:await check([{status:409,body:{ok:false}}]),
    noAck:await check([{status:200,body:{ok:false}},{status:200,body:{ok:true}}]),
    offline:await check(["network",{status:200,body:{ok:true}}]),
  };
  process.stdout.write(JSON.stringify(outcomes));
})().catch(e=>{process.stderr.write(String(e));process.exit(1)});
"""
    )
    results = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert results == {
        "acknowledged": {"success": True, "count": 1},
        "recovered": {"success": True, "count": 2},
        "forbidden": {"success": False, "count": 1},
        "noAck": {"success": True, "count": 2},
        "offline": {"success": True, "count": 2},
    }


def test_server_reports_failed_checkout_event_write_as_503():
    # Guard the exact event route, without changing payment or submit responses.
    source = Path("app/main.py").read_text(encoding="utf-8")
    event_route = source.split('@app.post("/api/subscription-miniapp/event")', 1)[1]
    event_route = event_route.split('@app.post("/api/subscription-miniapp/submit")', 1)[0]
    assert 'status_code=200 if recorded else 503' in event_route
    assert 'content={"ok": bool(recorded)}' in event_route
