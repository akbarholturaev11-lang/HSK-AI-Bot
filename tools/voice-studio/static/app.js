const $=(id)=>document.getElementById(id);
const examples={tj:'Салом! Ин овоз дар компютери шумо сохта мешавад. Имрӯз мо забони хитоиро меомӯзем.',ru:'Здравствуйте! Этот голос создан на вашем компьютере. Сегодня мы изучаем китайский язык.'};
let ready={},busy=false;
const token=document.querySelector('meta[name="studio-token"]').content;
function update(){ $('count').textContent=`${$('text').value.length} / 1500`;$('generate').disabled=busy||!ready[$('language').value]||!$('text').value.trim();}
$('text').addEventListener('input',()=>{localStorage.setItem('voice-studio-text',$('text').value);update()});
$('text').value=localStorage.getItem('voice-studio-text')||'';
$('sample').onclick=()=>{$('text').value=examples[$('language').value];update()};
$('clear').onclick=()=>{$('text').value='';localStorage.removeItem('voice-studio-text');update()};
$('speed').oninput=()=>{$('speed-label').value=Number($('speed').value).toFixed(2)+'×'};
$('language').onchange=()=>{update();$('status').textContent=ready[$('language').value]?'Model tayyor. Matn kiriting.':'Model yo‘q. Install.command faylini ishga tushiring.'};
async function request(url,options){const r=await fetch(url,options);const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Matn va tezlikni tekshiring.');return data;}
request('/api/status').then(data=>{ready=data.models;$('language').onchange()}).catch(()=>{$('status').textContent='Serverga ulanish yo‘q. Start.command faylini oching.'});
$('form').onsubmit=async(event)=>{event.preventDefault();if(busy)return;busy=true;update();$('player').pause();$('player').hidden=true;$('download').hidden=true;$('result-title').textContent='Ovoz tayyorlanmoqda…';$('result-note').textContent='Birinchi yaratish biroz uzoqroq davom etadi.';$('status').textContent='Matn kompyuteringizda ovozga aylantirilmoqda…';
try{const job=await request('/api/speech',{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Token':token},body:JSON.stringify({text:$('text').value,language:$('language').value,speed:Number($('speed').value)})});let result;const deadline=Date.now()+200000;while(Date.now()<deadline){await new Promise(r=>setTimeout(r,800));result=await request('/api/jobs/'+job.id);if(result.status==='error')throw new Error(result.error);if(result.status==='done')break;}if(result?.status!=='done')throw new Error('Kutish vaqti tugadi. Sahifani yangilang.');$('player').src=result.url;$('player').hidden=false;$('download').href=result.url;$('download').download=`ovoz-${result.language}.wav`;$('download').hidden=false;$('result-title').textContent='Ovozingiz tayyor.';$('result-note').textContent=`${result.duration} soniya · WAV · ${result.sample_rate} Hz`;$('status').textContent='Tinglang yoki WAV faylni saqlang.';}catch(error){$('status').textContent=error.message;$('result-title').textContent='Yaratib bo‘lmadi.';$('result-note').textContent='Chapdagi xabarni tekshirib, qayta urinib ko‘ring.';}finally{busy=false;update();}};
update();
