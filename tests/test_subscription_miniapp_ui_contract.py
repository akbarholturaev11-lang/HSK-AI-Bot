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
    for name in ("hasMethodStep", "isHsk30Unlock", "manualFlow", "lavaInfo", "lavaMode", "flow"):
        match = re.search(r"function " + name + r"\([^)]*\)\{[\s\S]*?\}", html)
        assert match is not None
        functions.append(match.group(0))
    script = (
        'const state={mode:"subscription",plan:"1_month",done:false,pending:false};'
        + "\n".join(functions)
        + '\nconst results={}; for(const region of ["tj","uz","ru","cn","other"]){'
        + 'state.region=region;state.mode="subscription";results[region]=flow();'
        + 'state.mode="hsk30_unlock";results[region+"_unlock"]=flow();}'
        # lava.top second path: only with a server overview.lava block.
        + '\nstate.region="uz";state.mode="subscription";state.plan="1_month";'
        + 'const lavaPlans=[{plan_type:"1_month"}];'
        + 'state.overview={lava:{mode:"both",plans:lavaPlans}};results.both=flow();'
        + 'state.path="lava";results.both_yes=flow();state.path="manual";results.both_no=flow();'
        + 'state.overview={lava:{mode:"lava_only",plans:lavaPlans}};results.lava_only=flow();'
        + 'state.overview={lava:{mode:"both",plans:[]}};results.no_terms=flow();'
        + 'state.overview={lava:{mode:"both",plans:lavaPlans,blocked_reason:"chargeback_open"}};results.chargeback=flow();'
        + 'state.overview={lava:{mode:"lava_only",plans:lavaPlans}};state.mode="hsk30_unlock";results.unlock_lava=flow();'
        + 'state.mode="referral_discount";results.discount_lava=flow();'
        + 'state.mode="subscription";state.lavaStatus="waiting";results.waiting=flow();state.lavaStatus="";'
        + 'state.overview=null;state.path="";'
        + '\nstate.regionalPlans=true;state.region="tj";results.regional_tj=flow();'
        + 'state.region="uz";results.regional_uz=flow();'
        + 'state.overview={lava:{mode:"both",plans:lavaPlans}};state.path="lava";results.regional_lava=flow();'
        + 'state.path="manual";state.region="cn";results.regional_cn=flow();'
        + 'state.pending=true;results.pending=flow();console.log(JSON.stringify(results));'
    )
    results = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert results["both"] == ["card", "country", "plans", "pay"]
    assert results["both_yes"] == ["card", "lavaPlans", "lavaPay"]
    assert results["both_no"] == ["card", "country", "plans", "pay"]
    assert results["lava_only"] == ["lavaPlans", "lavaPay"]
    assert results["no_terms"] == ["country", "plans", "pay"]
    assert results["chargeback"] == ["country", "plans", "pay"]
    assert results["unlock_lava"] == ["country", "pay"]
    # The server includes a lava block in a discount flow only when a promo
    # code carries the same discount; the client then offers the lava path.
    assert results["discount_lava"] == ["lavaPlans", "lavaPay"]
    assert results["waiting"] == ["lavaWait"]
    for region in ("tj", "cn"):
        assert results[region] == ["country", "plans", "method", "pay"]
        assert results[region + "_unlock"] == ["country", "method", "pay"]
    for region in ("uz", "ru", "other"):
        assert results[region] == ["country", "plans", "pay"]
        assert results[region + "_unlock"] == ["country", "pay"]
    assert results["regional_tj"] == ["plans", "method", "pay"]
    assert results["regional_uz"] == ["plans", "pay"]
    assert results["regional_lava"] == ["lavaPlans", "lavaPay"]
    assert results["regional_cn"] == ["plans", "method", "pay"]
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
    transport_start = html.index("function checkoutTransport(path,body,signal,keepalive){")
    transport_end = html.index("\n}\n/* Course checkout runs", transport_start) + 2
    transport = html[transport_start:transport_end]
    script = (
        'const state={preview:false,plan:"1_month",method:"visa"};'
        'const INIT_DATA="signed-test";const PWA_CHECKOUT_HOST=false;'
        'const API={event:"/api/subscription-miniapp/event"};'
        'function contextPayload(){return {attempt_id:"sub-test"}};'
        'const warnings=[];console.warn=(...parts)=>warnings.push(parts);'
        + transport + "\n"
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


def test_browser_checkout_returns_only_to_original_allowlisted_practice_pages():
    """Exercise the actual checkout return URL builder in both browser hosts."""
    html = _html()
    start = html.index('const RETURN_TO_COURSE=PARAMS.get("return_to")==="course"')
    end = html.index("function initTelegramCourseReturn(){", start)
    return_source = html[start:end]
    script = (
        'let PARAMS=new URLSearchParams();let PWA_CHECKOUT_HOST=true;'
        'const window={location:{replace:(url)=>{window.result=url}}};'
        + return_source
        + """
const paths=[
  ["course_v3_voice.html","voice"],
  ["course_v3_recognition.html","recognition"],
  ["course_v3_memorize.html","memorize"],
  ["course_v3_pronunciation.html","pronunciation"],
  ["course_v3_mistakes.html","mistakes"],
  ["course_v3_test.html","test"],
];
const actual=[];
for(const [page,slug] of paths){
  PARAMS=new URLSearchParams({lang:"tj",return_to:"course",return_page:page,return_level:"nhsk2"});
  PWA_CHECKOUT_HOST=true;
  const pwa=courseReturnUrl();
  returnToCourseFromCheckout();
  const replaced=window.result;
  PWA_CHECKOUT_HOST=false;
  const telegram=courseReturnUrl();
  actual.push({page,slug,pwa,telegram,replaced});
}
PARAMS=new URLSearchParams({lang:"evil",return_to:"course",return_page:"https://evil.test",return_level:"../../",return_tab:"mashq"});
PWA_CHECKOUT_HOST=true;
const forged=courseReturnUrl();
process.stdout.write(JSON.stringify({actual,forged}));
"""
    )
    result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    for case in result["actual"]:
        assert case["pwa"] == f'/iphone-pwa/practice/{case["slug"]}?lang=tj&level=nhsk2'
        assert case["telegram"] == f'/{case["page"]}?lang=tj&level=nhsk2'
        assert case["replaced"] == case["pwa"]
    assert result["forged"] == "/iphone-pwa/course?lang=uz&tab=mashq"


def test_server_reports_failed_checkout_event_write_as_503():
    # Guard the exact event route, without changing payment or submit responses.
    source = Path("app/main.py").read_text(encoding="utf-8")
    event_route = source.split('@app.post("/api/subscription-miniapp/event")', 1)[1]
    event_route = event_route.split('@app.post("/api/subscription-miniapp/submit")', 1)[0]
    assert 'status_code=200 if recorded else 503' in event_route
    assert 'content={"ok": bool(recorded)}' in event_route


def test_local_payment_region_hints_and_account_scoped_storage():
    html = _html()
    start = html.index("function regionStorageKey(){")
    end = html.index("/* Havola Xitoy", start)
    script = """
let PWA_CHECKOUT_HOST=true, PWA_CHECKOUT_ACTOR=null, INIT_DATA="";
let tg=null;
const REGION_ORDER=["tj","uz","ru","cn","other"];
const values={};
const localStorage={getItem:key=>values[key]||null,setItem:(key,value)=>{values[key]=value}};
""" + html[start:end] + """
const result={};
result.hints=[
  inferPaymentRegion("Asia/Dushanbe","tg-TJ","ru"),
  inferPaymentRegion("Asia/Shanghai","zh-Hans-CN","uz"),
  inferPaymentRegion("Europe/Moscow","ru-RU","uz"),
  inferPaymentRegion("Asia/Tashkent","uz-UZ","ru"),
  inferPaymentRegion("Asia/Tashkent","ru-RU","uz"),
  inferPaymentRegion("Europe/Warsaw","pl-PL","ru"),
  inferPaymentRegion("UTC","ru","ru"),
];
saveRegion("cn");
result.unbound=savedRegion();
PWA_CHECKOUT_ACTOR={user_id:11};saveRegion("cn");
result.first=savedRegion();
PWA_CHECKOUT_ACTOR={user_id:12};
result.second=savedRegion();
PWA_CHECKOUT_HOST=false;INIT_DATA="signed";tg={initDataUnsafe:{user:{id:11}}};
result.telegram=savedRegion();saveRegion("tj");
PWA_CHECKOUT_HOST=true;PWA_CHECKOUT_ACTOR={user_id:11};
result.firstAgain=savedRegion();
result.keys=Object.keys(values).sort();
console.log(JSON.stringify(result));
"""
    result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert result == {
        "hints": ["tj", "cn", "ru", "uz", "other", "other", "ru"],
        "unbound": "", "first": "cn", "second": "", "telegram": "",
        "firstAgain": "cn",
        "keys": ["hsk_sub_region_v1:11", "hsk_sub_region_v1:pwa:11"],
    }


def test_regional_prices_require_server_display_amounts():
    html = _html()
    start = html.index("function availableRegionalRegions(){")
    end = html.index("/* To'lov turi", start)
    script = """
function availablePlans(){return ["1_month","3_months"]}
function availableRegions(){return ["tj","uz","ru","cn","other"]}
function cardPrices(){return {
  ru:{"1_month":{currency:"RUB",final_amount:"10"},"3_months":{currency:"RUB",final_amount:"20"}},
  uz:{"1_month":{currency:"UZS",final_amount:"100"}},
  other:{"1_month":{currency:"USD",final_amount:"1"},"3_months":{currency:"USD",final_amount:null}},
}}
""" + html[start:end] + """
console.log(JSON.stringify(availableRegionalRegions()));
"""
    assert json.loads(subprocess.check_output(["node", "-e", script], text=True)) == ["tj", "ru", "cn"]


def test_regional_routing_obeys_admin_modes_and_verified_currency():
    html = _html()
    start = html.index("function regionalProviderPlans(")
    end = html.index("function regionalCurrencies(", start)
    script = html[start:end] + """
const regions=["tj","uz","ru","cn","other"];
const result={};
for(const mode of ["manual_only","both","lava_only"]){
  result[mode]=regions.map(region=>regionalRoute(region,mode,true,["USD","RUB"],"USD",""));
}
result.missingRub=regionalRoute("ru","both",true,["USD"],"USD","");
result.lavaOnlyMissing=regionalRoute("ru","lava_only",true,["USD"],"USD","");
result.alternate=regionalRoute("tj","both",true,["USD","RUB"],"USD","lava");
result.noManual=regionalRoute("cn","both",false,["USD"],"USD","manual");
result.filtered=regionalProviderPlans({currency:"USD",plans:[{plan_type:"1_month",amount:"10",currency:"USD"}],plans_by_currency:{RUB:[{plan_type:"1_month",amount:"900",currency:"RUB"},{plan_type:"3_months",amount:null,currency:"RUB"},{plan_type:"6_months",amount:"10",currency:"USD"}]}},"RUB");
console.log(JSON.stringify(result));
"""
    result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    manual = {"path": "manual", "currency": ""}
    usd = {"path": "lava", "currency": "USD"}
    rub = {"path": "lava", "currency": "RUB"}
    assert result["manual_only"] == [manual] * 5
    assert result["both"] == [manual, usd, rub, manual, usd]
    assert result["lava_only"] == [usd, usd, rub, usd, usd]
    assert result["missingRub"] == manual
    assert result["lavaOnlyMissing"] == usd
    assert result["alternate"] == usd
    assert result["noManual"] == usd
    assert result["filtered"] == [{"plan_type": "1_month", "amount": "900", "currency": "RUB"}]
