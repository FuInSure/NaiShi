const fs=require('fs'),path=require('path'),os=require('os'),{spawn}=require('child_process'),{pathToFileURL}=require('url');
const root=path.resolve(__dirname,'..'),qa=path.join(root,'qa');fs.mkdirSync(qa,{recursive:true});
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'research-english-qa-'));
const browser=spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));const assert=(x,m)=>{if(!x)throw Error(m)};
let socket,seq=0;const pending=new Map(),errors=[],checks=[];
async function main(){
  const portFile=path.join(profile,'DevToolsActivePort');for(let i=0;i<100&&!fs.existsSync(portFile);i++)await delay(150);
  assert(fs.existsSync(portFile),'browser did not start');
  const port=fs.readFileSync(portFile,'utf8').split(/\r?\n/)[0];
  const targets=await (await fetch('http://127.0.0.1:'+port+'/json/list',{signal:AbortSignal.timeout(5000)})).json();
  socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject});
  socket.onmessage=e=>{const msg=JSON.parse(e.data);if(msg.id&&pending.has(msg.id)){const p=pending.get(msg.id);pending.delete(msg.id);clearTimeout(p.timer);msg.error?p.reject(Error(p.method+": "+msg.error.message)):p.resolve(msg.result)}if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails.text)};
  function cdp(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(Error('timeout '+method))},10000);pending.set(id,{resolve,reject,timer,method});socket.send(JSON.stringify({id,method,params}))})}
  async function evalJs(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text+': '+expression);return r.result.value}
  async function click(selector){const rect=await evalJs('(function(){const e=document.querySelector('+JSON.stringify(selector)+');e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()');await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...rect});await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...rect})}
  async function select(id,value){await evalJs('(function(){const e=document.getElementById('+JSON.stringify(id)+');e.value='+JSON.stringify(value)+';e.dispatchEvent(new Event("change",{bubbles:true}))})()')}
  async function setSearch(value){await evalJs('(function(){const e=document.getElementById("search");e.value='+JSON.stringify(value)+';e.dispatchEvent(new Event("input",{bubbles:true}))})()')}
  async function screenshot(name){const s=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(qa,name),Buffer.from(s.data,'base64'))}
  await cdp('Runtime.enable');await cdp('Page.enable');await cdp('Emulation.setDeviceMetricsOverride',{width:1365,height:900,deviceScaleFactor:1,mobile:false});
  await cdp('Page.navigate',{url:pathToFileURL(path.join(root,'打开词库.html')).href});
  for(let i=0;i<100;i++){if(await evalJs('!!document.getElementById("word-grid")&&document.querySelectorAll(".wordcard").length===18'))break;await delay(100)}
  assert((await evalJs('document.getElementById("result-count").textContent')).includes('1900 / 1900'),'total count');
  await screenshot('desktop.png');checks.push('桌面加载、1900 总数及18条分页');
  await click('#search');await cdp('Input.insertText',{text:'GNN'});assert(await evalJs('document.querySelectorAll(".wordcard").length>0'),'abbreviation search');
  await click('.wordcard');assert(await evalJs('document.getElementById("detail").open'),'detail opening');
  await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  assert(!(await evalJs('document.getElementById("detail").open')),'Esc closes detail');checks.push('实际坐标点击、键入GNN、详情与Escape关闭');
  await setSearch('');assert(await evalJs('!document.querySelector("#scope option[value=examples]")'),'examples removed');
  await select('module','概率建模');assert(await evalJs('Array.from(document.querySelectorAll(".wordcard .badge:first-child")).every(e=>e.textContent==="概率建模")'),'module filter');
  await setSearch('zzzz-no-result');assert((await evalJs('document.getElementById("result-count").textContent')).includes('0 / 1900'),'empty results');checks.push('例句入口已移除、模块筛选和空结果计数');
  await setSearch('');await select('module','');await select('scope','all');await click('#page-next');assert((await evalJs('document.getElementById("page-label").textContent')).startsWith('2 /'),'next page');await click('#page-prev');
  await click('button[data-view="flash"]');assert(!(await evalJs('!!document.querySelector("#flash-card .answer")')),'answer initially hidden');
  await click('#flip');assert(await evalJs('!!document.querySelector("#flash-card .answer")'),'flip answer');await click('#flash-next');assert(!(await evalJs('!!document.querySelector("#flash-card .answer")')),'next hides answer');checks.push('分页与翻卡答案状态重置');
  await click('button[data-view="sentences"]');await select('sentence-choice','0');assert(!(await evalJs('document.getElementById("sentence-answer").open')),'reference hidden');
  await click('#sentence-answer summary');assert(await evalJs('document.getElementById("sentence-answer").open'),'reference expands');await click('#translation');await cdp('Input.insertText',{text:'测试草稿：时空预测。'});
  await click('#sentence-next');assert(!(await evalJs('document.getElementById("sentence-answer").open')),'sentence change hides answer');await click('#sentence-prev');assert((await evalJs('document.getElementById("translation").value')).includes('测试草稿'),'draft recovery');
  await screenshot('translation.png');checks.push('论文句子切换、参考答案折叠与浏览器草稿恢复');
  await click('button[data-view="flash"]');await click('#mark-unknown');await click('button[data-view="unknown"]');assert((await evalJs('document.getElementById("unknown-count").textContent')).includes('1 个'),'unknown count');await click('#unknown-grid button[data-card]');assert(await evalJs('document.getElementById("detail").open'),'unknown details');await click('#close-detail');await click('#unknown-grid button[data-known]');assert((await evalJs('document.getElementById("unknown-count").textContent')).includes('0 个'),'known removes card');checks.push('不会词页面收录、详情、改为会及数量同步');await click('button[data-view="sentences"]');
  await click('button[data-view="training"]');await click('#train-start');await evalJs('document.querySelector("[data-option="+JSON.stringify(training.queue[0])+"]").click()');assert((await evalJs('study.events.length'))===1,'training recorded');await click('button[data-view="records"]');assert((await evalJs('document.getElementById("records").textContent')).includes('100%'),'training accuracy');
  await click('button[data-view="manage"]');await click('[data-favorite]');assert((await evalJs('Object.keys(study.favorites).length'))===1,'favorite saved');
  await evalJs('persistMark(all[1].id,"unknown")');await click('button[data-view="review"]');await click('#review-reveal');await click('[data-grade="hard"]');assert((await evalJs('study.events.length'))===2,'review recorded');assert(await evalJs('study.reviews[all[1].id].due>Date.now()'),'review scheduled');
  await click('button[data-view="phonetics"]');assert((await evalJs('document.querySelectorAll("#phonetics [data-card]").length'))===18,'IPA pagination');
  await click('button[data-view="sentences"]');await click('#paper-save');assert((await evalJs('Object.keys(study.papers).length'))===1,'paper saved');
  await cdp('Page.reload');for(let i=0;i<50;i++){if(await evalJs('typeof study!=="undefined"&&study.events.length===2'))break;await delay(100);}assert(await evalJs('study.events.length===2&&Object.keys(study.favorites).length===1&&Object.keys(study.papers).length===1'),'study persists after reload');await click('button[data-view="sentences"]');await select('sentence-choice','0');checks.push('训练计分、复习排期、收藏、音标、译文记录及刷新恢复');
  await evalJs('Object.defineProperty(Storage.prototype,"setItem",{value:function(){throw new Error("simulated quota")},configurable:true});void 0');await click('#translation');await cdp('Input.insertText',{text:'存储失败时仍保留。'});
  assert((await evalJs('document.getElementById("save-status").textContent')).includes('不可用'),'storage failure notice');assert((await evalJs('document.getElementById("translation").value')).includes('存储失败'),'draft retained');checks.push('模拟存储失败保留输入并显示失败状态');
  await cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await click('button[data-view="library"]');await evalJs('window.scrollTo(0,0)');assert(await evalJs('document.documentElement.scrollWidth<=window.innerWidth+1'),'mobile horizontal overflow');await screenshot('mobile.png');
  await click('.wordcard');assert(await evalJs('document.getElementById("detail").getBoundingClientRect().width<=window.innerWidth'),'mobile dialog fit');await screenshot('mobile-detail.png');await click('#close-detail');checks.push('390px窄屏无横向溢出、词卡详情适配');
  await cdp('Emulation.setDeviceMetricsOverride',{width:1280,height:600,deviceScaleFactor:1,mobile:false});await click('.wordcard');assert(await evalJs('document.getElementById("detail").getBoundingClientRect().height<=window.innerHeight'),'short viewport dialog fit');checks.push('600px短屏详情高度与滚动容器');
  assert(errors.length===0,'runtime exceptions: '+errors.join(','));
  fs.writeFileSync(path.join(qa,'browser-validation.json'),JSON.stringify({result:'pass',browser:'Microsoft Edge headless via CDP',checks,errors,note:'桌面浏览器与窄屏模拟；不代表安卓APP或真机验收。'},null,2));
  console.log(JSON.stringify({result:'pass',checks},null,2));await cdp('Browser.close').catch(()=>{});
}
main().catch(e=>{console.error(e.stack);process.exitCode=1}).finally(()=>{if(socket)socket.close();browser.kill()});
