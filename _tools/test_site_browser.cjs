// Optional browser QA: requires Playwright and installed Edge; no runtime dependency.
// SITE_URL and QA_OUTPUT may override the local review target and evidence directory.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const OUT=path.resolve(process.env.QA_OUTPUT || path.join(__dirname,'../temp/browser-qa')), BASE=(process.env.SITE_URL || 'http://127.0.0.1:8812').replace(/\/$/,'');
fs.mkdirSync(OUT,{recursive:true});
const routes=['/','/about/','/work/targeting-architecture/','/work/testing-the-fix/','/work/personal-finance-tools/','/404.html'];
const widths=[320,340,360,390,400,412,430,460,600,760,768,880,900,1000,1200];
const results={routes:[],interactions:[],screenshots:[],limitations:['Browser emulation only; not physical iOS/Android or actual low-memory device validation.']};
const report=()=>fs.writeFileSync(path.join(OUT,'browser-qa.json'),JSON.stringify(results,null,2));
(async()=>{
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1200,height:1000}}), page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of widths){await page.setViewportSize({width,height:1000});for(const route of routes){
   const response=await page.goto(BASE+route);assert.equal(response.status(),200);
   await page.evaluate(()=>document.fonts.ready);
   const state=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,h1:document.querySelectorAll('h1').length,main:document.querySelectorAll('main').length,images:[...document.images].filter(i=>i.loading!=='lazy').map(i=>({src:i.currentSrc,ok:i.complete&&i.naturalWidth>0}))}));
   assert.equal(state.overflow,false,`${width} ${route} overflow`);assert.equal(state.h1,1);assert.equal(state.main,1);
   assert(state.images.every(i=>i.ok),JSON.stringify(state.images));results.routes.push({width,route,pass:true});
 }}
 assert.deepEqual(errors,[]);await context.close();report();
 for(const scenario of [
   {name:'desktop-2x',width:1200,dpr:2,mobile:false,rich:true},
   {name:'phone-3x',width:390,dpr:3,mobile:true,rich:true},
   {name:'phone-2x',width:430,dpr:2,mobile:true,rich:true},
   {name:'desktop-1x',width:1200,dpr:1,mobile:false,rich:false},
   {name:'save-data',width:390,dpr:3,mobile:true,rich:false,saveData:true},
   {name:'slow-2g',width:390,dpr:2,mobile:true,rich:false,effectiveType:'slow-2g'},
   {name:'reduced-motion',width:390,dpr:3,mobile:true,rich:true,reduced:true}
 ]){
  const ctx=await browser.newContext({viewport:{width:scenario.width,height:900},deviceScaleFactor:scenario.dpr,isMobile:scenario.mobile,hasTouch:scenario.mobile,reducedMotion:scenario.reduced?'reduce':'no-preference'});
  if(scenario.saveData||scenario.effectiveType)await ctx.addInitScript(({saveData,effectiveType})=>Object.defineProperty(navigator,'connection',{value:{saveData:!!saveData,effectiveType:effectiveType||'4g'},configurable:true}),scenario);
  const p=await ctx.newPage(),requests=[],failures=[],consoleErrors=[];
  p.on('request',r=>{if(r.url().includes('/assets/img/pints/'))requests.push(r.url())});p.on('requestfailed',r=>failures.push(r.url()));p.on('pageerror',e=>consoleErrors.push(e.message));
  await p.goto(BASE);await p.evaluate(()=>document.fonts.ready);
  assert.equal(await p.locator('.pint-motion').count(),0,'No canvas allocated before interaction');
  if(scenario.saveData||scenario.effectiveType){await p.waitForTimeout(350);assert(!requests.some(u=>/frame-(0[1-9]|[12][0-9])\.webp/.test(u)),'speculative motion on constrained connection');}
  for(let i=0;i<3;i++){
   const card=p.locator('.pint-card').nth(i),button=card.locator('.pint-turn');await button.scrollIntoViewIfNeeded();
   const tier=await card.getAttribute('data-quality');assert.equal(tier,scenario.rich?'retina':'lean');
   await (scenario.mobile?button.tap():button.click());assert.equal(await card.locator('.pint-label-read').isVisible(),true);
   if(!scenario.reduced){await p.waitForFunction(i=>{const c=document.querySelectorAll('.pint-card')[i];const f=+c.dataset.frame;return f>0&&f<30},i,{timeout:20000});
     const mid=await card.locator('canvas').evaluate(i=>({src:i.dataset.source,width:i.width}));assert.equal(mid.src.includes('/motion-600/'),scenario.rich);assert.equal(mid.width,(scenario.saveData||scenario.effectiveType)?400:800);
   }
   await p.waitForFunction(i=>document.querySelectorAll('.pint-card')[i].dataset.frame==='30' && !document.querySelectorAll('.pint-card')[i].dataset.loading,i);
   await p.waitForFunction(i=>{const image=document.querySelectorAll('.pint-card img')[i];return image.complete&&image.naturalWidth>0},i);
   const end=await card.locator('canvas').evaluate(i=>({current:i.dataset.source}));assert(end.current.endsWith('frame-30.webp'));if(scenario.rich)assert(end.current.includes('/still-800/'));assert.equal(await card.locator('canvas').count(),1);
   if(i===0&&['phone-3x','desktop-2x'].includes(scenario.name)){const file=`${scenario.name}-back.png`;await card.screenshot({path:path.join(OUT,file)});results.screenshots.push(file);}
   await card.locator('.pint-label-read').click();assert(await p.locator('.label-dialog').evaluate(d=>d.open));assert.equal(await p.locator('.label-dialog dt').count(),3);await p.keyboard.press('Escape');assert.equal(await p.locator('.label-dialog').evaluate(d=>d.open),false);
   await (scenario.mobile?button.tap():button.click());await p.waitForFunction(i=>document.querySelectorAll('.pint-card')[i].dataset.frame==='0',i);assert.equal(await card.locator('.pint-label-read').isVisible(),false);
  }
  if(scenario.reduced)assert(!requests.some(u=>/frame-(0[1-9]|[12][0-9])\.webp/.test(u)),'reduced motion fetched intermediates');
  assert.deepEqual(failures,[]);assert.deepEqual(consoleErrors,[]);
  results.interactions.push({scenario:scenario.name,pass:true,uniquePintRequests:new Set(requests).size,richMotionRequests:new Set(requests.filter(u=>u.includes('/motion-600/'))).size});await ctx.close();report();
 }
 // Keyboard, rapid reversals, viewport resize, and preserved rail.
 const ctx=await browser.newContext({viewport:{width:1200,height:1000},deviceScaleFactor:2}),p=await ctx.newPage();await p.goto(BASE);
 await p.locator('.pint-stage').first().focus();await p.waitForFunction(()=>document.querySelector('.pint-card').dataset.frame==='30');await p.keyboard.press('Escape');await p.waitForFunction(()=>document.querySelector('.pint-card').dataset.frame==='0');
 const b=p.locator('.pint-turn').first();await b.click();await p.waitForTimeout(90);await b.click();await p.waitForTimeout(90);await b.click();await p.waitForFunction(()=>document.querySelector('.pint-card').dataset.frame==='30' && !document.querySelector('.pint-card').dataset.loading);assert.equal(await p.locator('.pint-card').first().getAttribute('data-loading'),null);
 await p.setViewportSize({width:430,height:900});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await b.click();await p.waitForFunction(()=>document.querySelector('.pint-card').dataset.frame==='0');
 await p.setViewportSize({width:1200,height:1000});await p.goto(BASE+'/work/targeting-architecture/');assert.equal(await p.locator('.story-rail').evaluate(e=>getComputedStyle(e).position),'sticky');assert.equal(await p.locator('.story-pint img').evaluate(i=>i.currentSrc.includes('/still-800/')),true);
 await p.evaluate(()=>scrollTo(0,1200));await p.waitForTimeout(400);assert(await p.locator('.chapter-rail [aria-current="true"]').count());
 results.interactions.push({scenario:'keyboard-rapid-reversal-resize-sticky-rail',pass:true});await ctx.close();
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:900},deviceScaleFactor:3}),n=await nojs.newPage();await n.goto(BASE);assert.equal(await n.locator('.pint-turn:visible').count(),0);assert.equal(await n.locator('.pint-case-link').count(),3);await n.locator('.pint-stage').first().click();assert(n.url().includes('/work/targeting-architecture/'));assert(await n.locator('.story-pint img').evaluate(i=>i.currentSrc.includes('/still-800/')));await nojs.close();results.interactions.push({scenario:'no-javascript-retina-still-and-navigation',pass:true});
 // Slow-network cold start (Chrome DevTools emulation; not physical radio).
 const slow=await browser.newContext({viewport:{width:390,height:900},deviceScaleFactor:2,isMobile:true,hasTouch:true}),s=await slow.newPage(),cdp=await slow.newCDPSession(s);await cdp.send('Network.enable');await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:200,downloadThroughput:200000,uploadThroughput:100000});await s.goto(BASE);const sb=s.locator('.pint-turn').first();await sb.tap();assert(await s.locator('.pint-label-read').first().isVisible());await s.waitForFunction(()=>document.querySelector('.pint-card').dataset.frame==='30',null,{timeout:30000});assert.equal(await s.locator('.pint-card').first().getAttribute('data-error'),null);await slow.close();results.interactions.push({scenario:'cold-200ms-200KBps',pass:true});
 // Stress the actual mouse path with NO RAF recorder/DOM instrumentation.
 const hover=await browser.newContext({viewport:{width:1200,height:1200},deviceScaleFactor:2}),h=await hover.newPage();
 const hoverErrors=[];h.on('pageerror',e=>hoverErrors.push(e.message));await h.goto(BASE);
 assert.equal(await h.locator('.pint-shelf').getAttribute('data-renderer'),'persistent-canvas-v3');
 assert.equal(await h.locator('#hover-diagnostic').count(),0);
 const posters=await h.locator('.pint-stage img').elementHandles();
 for(const i of [1,2]){await h.locator('.pint-turn').nth(i).click();await h.waitForFunction(i=>document.querySelectorAll('.pint-card')[i].dataset.frame==='30'&&!document.querySelectorAll('.pint-card')[i].dataset.loading,i);}
 await h.keyboard.press('Escape');await h.waitForFunction(()=>[...document.querySelectorAll('.pint-card')].every(c=>c.dataset.frame==='0'&&!c.dataset.loading));
 const surfaces=await h.locator('.pint-motion').elementHandles();
 const boxes=await h.locator('.pint-stage').evaluateAll(a=>a.map(e=>{const b=e.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}}));
 for(let round=0;round<4;round++)for(const [i,x,y,dwell] of [[1,.5,.25,170],[2,.1,.1,330],[1,.95,.65,250],[2,.5,.5,850],[1,.02,.9,180],[2,.98,.85,200],[-1,0,0,1200]]){
   if(i<0)await h.mouse.move(10,100,{steps:8});else{const b=boxes[i];await h.mouse.move(b.x+b.w*x,b.y+b.h*y,{steps:8});}
   await h.waitForTimeout(dwell);
 }
 await h.mouse.move(10,100);await h.waitForFunction(()=>[...document.querySelectorAll('.pint-card')].every(c=>c.dataset.frame==='0'&&!c.dataset.loading));
 assert.deepEqual(hoverErrors,[]);for(const image of posters)assert(await image.evaluate(e=>e.isConnected&&e.complete&&e.naturalWidth>0));for(const surface of surfaces)assert(await surface.evaluate(e=>e.isConnected&&e.width===800&&e.height===1200));
 // At rest, compare actual painted pixels to the chosen decoded source, not
 // only a frame counter. This readback is AFTER the uninstrumented stress run.
 for(const index of [1,2])for(const target of [30,0]){
   await h.locator('.pint-turn').nth(index).click();await h.waitForFunction(({index,target})=>{const c=document.querySelectorAll('.pint-card')[index];return c.dataset.frame===String(target)&&!c.dataset.loading},{index,target});
   const diff=await h.locator('.pint-card').nth(index).locator('canvas').evaluate(async canvas=>{
     const image=new Image();image.src=canvas.dataset.source;await image.decode();const reference=document.createElement('canvas');reference.width=canvas.width;reference.height=canvas.height;const rc=reference.getContext('2d',{alpha:false});rc.drawImage(image,0,0,reference.width,reference.height);
     const a=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data,b=rc.getImageData(0,0,canvas.width,canvas.height).data;let max=0;for(let i=0;i<a.length;i++)max=Math.max(max,Math.abs(a[i]-b[i]));return max;
   });assert.equal(diff,0,'Canvas pixels differ from selected source');
 }
 await h.screenshot({path:path.join(OUT,'hover-stress-settled.png'),fullPage:true});await hover.close();results.interactions.push({scenario:'uninstrumented-adjacent-hover-28-moves-stable-surfaces-exact-endpoint-pixels',pass:true});
 // Missing canvas support and failed frame fetch retain static case access.
 for(const mode of ['no-canvas','failed-frame']){
   const f=await browser.newContext({viewport:{width:1200,height:1000},deviceScaleFactor:2});
   if(mode==='no-canvas')await f.addInitScript(()=>{HTMLCanvasElement.prototype.getContext=()=>null});
   const q=await f.newPage();if(mode==='failed-frame')await q.route('**/motion-600/frame-05.webp',route=>route.abort());await q.goto(BASE);await q.locator('.pint-turn').nth(1).click();await q.waitForFunction(()=>document.querySelectorAll('.pint-card')[1].dataset.error==='true');
   assert.equal(await q.locator('.pint-motion').count(),0);assert(await q.locator('.pint-stage img').nth(1).evaluate(i=>i.complete&&i.naturalWidth>0));await q.locator('.pint-label-read').nth(1).click();assert(await q.locator('.label-dialog').evaluate(d=>d.open));await q.keyboard.press('Escape');await q.locator('.pint-case-link').nth(1).click();assert(q.url().endsWith('/work/testing-the-fix/'));await f.close();results.interactions.push({scenario:mode+'-static-label-and-navigation-fallback',pass:true});
 }
 // Motion preference changes while frames are in flight must settle cleanly.
 const pref=await browser.newContext({viewport:{width:1200,height:1000},deviceScaleFactor:2}),mp=await pref.newPage();await mp.goto(BASE);await mp.locator('.pint-turn').nth(1).click();await mp.waitForFunction(()=>{const f=+document.querySelectorAll('.pint-card')[1].dataset.frame;return f>0&&f<30});await mp.emulateMedia({reducedMotion:'reduce'});await mp.waitForFunction(()=>{const c=document.querySelectorAll('.pint-card')[1];return c.dataset.frame==='30'&&!c.dataset.loading});await mp.emulateMedia({reducedMotion:'no-preference'});await mp.locator('.pint-turn').nth(1).click();await mp.waitForFunction(()=>document.querySelectorAll('.pint-card')[1].dataset.frame==='0');await pref.close();results.interactions.push({scenario:'mid-turn-motion-preference-change',pass:true});
 // Final screenshots: full pages, not just the hero.
 const shots=await browser.newContext({viewport:{width:1200,height:1000},deviceScaleFactor:2}),v=await shots.newPage();for(const [name,route] of [['home','/'],['about','/about/'],['case-publisher','/work/targeting-architecture/'],['case-evidence','/work/testing-the-fix/'],['case-compound','/work/personal-finance-tools/']]){await v.goto(BASE+route);await v.evaluate(()=>document.fonts.ready);await v.screenshot({path:path.join(OUT,`${name}-desktop.png`),fullPage:true});results.screenshots.push(`${name}-desktop.png`)}await shots.close();
 results.passed=true;report();console.log(JSON.stringify({passed:true,routeWidthChecks:results.routes.length,interactionScenarios:results.interactions.length,screenshots:results.screenshots.length}));
}catch(e){results.passed=false;results.error=e.stack;report();throw e}finally{await browser.close()}
})();
