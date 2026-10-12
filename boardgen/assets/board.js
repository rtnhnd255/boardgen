// ===== META (roadmap.json; дефолты — SPEC §6) =====
const META=window.ROADMAP_META||{};
const START=META.start_date||null;
const TW=META.total_weeks||78;
const QWn=META.quarters_weeks||13;
const NQ=Math.ceil(TW/QWn);
const BUFW=META.buffer_weeks||[];
const ST=META.stream_ids||['A','B','C','D','E'];
const SL=META.stream_labels||{};
const SC=META.stream_colors||{};
function curWeek(){if(!START)return 1;const sd=new Date(START);return Math.max(1,Math.min(TW,Math.floor((Date.now()-sd)/(7*864e5))))}
function planWeek(){if(!START)return 0;const sd=new Date(START);return Math.max(0,Math.min(TW,Math.floor((Date.now()-sd)/(7*864e5))))}

// ===== STATE =====
const LS=META.ls_key||'boardgen';let S={};try{S=JSON.parse(localStorage.getItem(LS)||'{}')}catch(e){S={}}
function bufWk(e,cv){
  const r=cv.getBoundingClientRect();
  const wx=(e.clientX-r.left-V.x)/V.s;
  const w=Math.floor((wx-50)/LI.ws)+1;
  return(w>=1&&w<=TW&&BUFW.includes(w))?w:0;
}
function allCk(c){const b=document.querySelectorAll('[data-ck^="ck-'+c+'-"]');let d=0;b.forEach(x=>{if(S[x.dataset.ck])d++});return{n:b.length,d:d}}
function toast2(msg){let t=document.getElementById('toast2');if(!t){t=document.createElement('div');t.id='toast2';document.body.appendChild(t)}t.textContent=msg;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),2400)}
function done(c){
  if(!c)return false;
  if(S['b-'+c]===true)return true;
  if(S['b-'+c]===false)return false;
  if(!window.BOARD_DATA)return false;
  if(!window.BOARD_DATA.find(n=>n[0]===c))return false;
  const b=document.querySelectorAll('[data-ck^="ck-'+c+'-"]');
  if(b.length===0)return false;
  let d=0;b.forEach(x=>{if(S[x.dataset.ck])d++});
  return d===b.length;
}
function save(){localStorage.setItem(LS,JSON.stringify(S));refresh();draw()}

// ===== CANVAS =====
const NW=70,NH=20,GY=8;
let V={x:10,y:35,s:1};
let P={},LI=null,drag=false,dX=0,dY=0,dM=0,hit=null,hov=null,nb=null,dim=0,dimT=0,raf=null;
let EO={},MO={};

function anim(){dim+=(dimT-dim)*.15;if(Math.abs(dimT-dim)<.01){dim=dimT;raf=null;draw();return}draw();raf=requestAnimationFrame(anim)}

function layout(nodes){
  P={};
  const sqm={};nodes.forEach(n=>{const q=parseInt(n[3][1])-1;const k=n[4]+':'+q;sqm[k]=(sqm[k]||0)+1});
  const qM={};for(let q=0;q<NQ;q++){let m=1;ST.forEach(s=>m=Math.max(m,sqm[s+':'+q]||1));qM[q]=m}
  const mx=Math.max(...Object.values(qM));
  const sqwk={};
  nodes.forEach(n=>{
    const sw2=parseInt(n[2].split('-')[0].replace('W',''));
    const qi2=Math.floor((sw2-1)/13);
    const wq2=sw2-qi2*13;
    const k2=n[4]+':'+qi2+':'+wq2;
    sqwk[k2]=(sqwk[k2]||0)+1;
  });
  let maxSameW=1;
  for(const v of Object.values(sqwk))maxSameW=Math.max(maxSameW,v);
  const ws=Math.max(NW+8,maxSameW*(NW+8),Math.ceil(mx*(NW+8)/QWn));
  const QW=QWn*ws;
  const qX={};for(let q=0;q<NQ;q++)qX[q]=50+q*QWn*ws;
  const cx=50+TW*ws;
  const sH={};ST.forEach(s=>{sH[s]=NH+25});
  const sY={};let wy=50;ST.forEach(s=>{sY[s]=wy;wy+=sH[s]+30});
  const si={};
  const sorted=[...nodes].sort((a,b)=>{
    if(a[4]!==b[4])return ST.indexOf(a[4])-ST.indexOf(b[4]);
    const qa=parseInt(a[3][1])-1,qb=parseInt(b[3][1])-1;
    if(qa!==qb)return qa-qb;
    if(b[5]&&b[5].includes(a[0]))return -1;
    if(a[5]&&a[5].includes(b[0]))return 1;
    return 0;
  });
  sorted.forEach(n=>{
    const parts=n[2].split('-');
    const sw=parseInt(parts[0].replace('W',''));
    const ew=parts.length>1?parseInt(parts[1].replace('W','')):sw;
    const qi=Math.floor((sw-1)/13);
    const wq=sw-qi*13;
    const dur=ew-sw+1;
    const key=n[4]+':'+qi;
    if(!si[key])si[key]=0;
    const col=si[key]++;
    const x=50+(sw-1)*ws;
    const w=Math.max(NW,dur*ws-5);
    // Коллизия: если пересекается с уже размещённым узлом того же потока → вниз
    let y=sY[n[4]]+8;
    let collision=true;
    while(collision){
      collision=false;
      for(const existing of Object.values(P)){
        if(existing.stream!==n[4])continue;
        // Проверяем пересечение по X
        if(x<existing.x+existing.w+3&&x+w+3>existing.x){
          // Пересекаются по X → проверяем Y
          if(y<existing.y+NH+4&&y+NH+4>existing.y){
            y+=NH+4;
            collision=true;
            break;
          }
        }
      }
    }
    P[n[0]]={x,y,w,name:n[1],weeks:n[2],stream:n[4],qi,wq,dur,col,pr:n[5]||''};
  });
  let maxX=0;for(const p of Object.values(P))maxX=Math.max(maxX,p.x+p.w+30);
  return{w:Math.max(cx,maxX),h:wy+30,sY,sH,qX,QW,ws};
}

function edges(nodes){
  EO={};MO={};
  const inc={},out={};
  nodes.forEach(n=>{
    const c=n[0],pr=n[5]||'';if(!pr)return;
    pr.split(',').forEach(p=>{
      p=p.trim();
      if(!inc[c])inc[c]=[];
      inc[c].push({f:p,t:c});
      if(!out[p])out[p]=[];
      out[p].push(p+'>'+c);
    });
  });
  for(const[c,eg]of Object.entries(inc)){
    const n=eg.length;
    eg.forEach((e,i)=>EO[e.f+'>'+e.t]=n===1?NH/2:4+(NH-8)*i/(n-1));
  }
  for(const[src,eg]of Object.entries(out)){
    const f=P[src];if(!f)continue;
    eg.forEach((ek,i)=>MO[ek]=f.x+f.w+10+i*15);
  }
}

function hood(c){
  if(!c||!window.BOARD_DATA)return null;
  const ns=new Set([c]),eg=[];
  const self=window.BOARD_DATA.find(n=>n[0]===c);
  if(self&&self[5])self[5].split(',').forEach(p=>{p=p.trim();ns.add(p);eg.push({f:p,t:c})});
  window.BOARD_DATA.forEach(n=>{
    if(n[5]&&n[5].split(',').map(x=>x.trim()).includes(c)){ns.add(n[0]);eg.push({f:c,t:n[0]})}
  });
  return{ns,eg};
}

const PART={};(window.BOARD_DATA||[]).forEach(n=>{if(n[6])for(const k in n[6])PART[n[0]+'|'+k]=n[6][k]});
let SEARCH='',HIDEDONE=false,CRIT=null;const FLASH={};
function critSet(){
  const curW=curWeek();
  const nb=BUFW.find(w=>w>=curW)||TW;
  const st=new Set();
  const rec=c=>{if(st.has(c))return;st.add(c);const pr=(P[c]&&P[c].pr)||'';pr.split(',').forEach(x=>{x=x.trim();if(x&&!done(x))rec(x)})};
  for(const c in P){const q=P[c];const sw=parseInt(q.weeks.split('-')[0].replace('W',''));if(!done(c)&&sw<=nb)rec(c)}
  return st;
}
function focusNode(code){
  const q=P[code];if(!q){toast2('Узел '+code+' не на канвасе');return}
  const cv=document.getElementById('dep-canvas');
  V.s=Math.max(V.s,1.6);
  V.x=(cv.clientWidth||830)/2-(q.x+q.w/2)*V.s;
  V.y=(cv.clientHeight||500)/2-(q.y+NH/2)*V.s;
  FLASH[code]=Date.now();
  draw();
  const t0=Date.now();
  const loop=()=>{if(Date.now()-t0<1600){draw();requestAnimationFrame(loop)}else{delete FLASH[code];draw()}};
  requestAnimationFrame(loop);
}
function mmDraw(){
  const mm=document.getElementById('mm-canvas');if(!mm||!LI)return;
  const dp=(window.devicePixelRatio||1);
  const mw=mm.clientWidth||600,mh=64;
  if(mm.width!==Math.round(mw*dp)||mm.height!==Math.round(mh*dp)){mm.width=Math.round(mw*dp);mm.height=Math.round(mh*dp)}
  const mc=mm.getContext('2d');mc.setTransform(dp,0,0,dp,0,0);
  mc.clearRect(0,0,mw,mh);
  const k=Math.min(mw/LI.w,mh/LI.h);
  const ox=(mw-LI.w*k)/2,oy=(mh-LI.h*k)/2;
  ST.forEach(st=>{
    mc.fillStyle=(SC[st]||'#999')+'22';
    mc.fillRect(ox,oy+LI.sY[st]*k,LI.w*k,LI.sH[st]*k);
  });
  for(const c2 in P){
    const q=P[c2];const d2=done(c2);
    mc.globalAlpha=d2?.95:.65;
    mc.fillStyle=d2?'#2e7d32':(SC[q.stream]||'#999');
    mc.fillRect(ox+q.x*k,oy+q.y*k,Math.max(1.5,q.w*k),Math.max(2,NH*k));
  }
  mc.globalAlpha=1;
  const cv=document.getElementById('dep-canvas');
  const vw=(cv.clientWidth||830)/V.s*k,vh=(cv.clientHeight||500)/V.s*k;
  const vx=ox+(-V.x/V.s)*k,vy=oy+(-V.y/V.s)*k;
  mc.strokeStyle='#1a365d';mc.lineWidth=1.5;
  mc.strokeRect(vx,vy,vw,vh);
}
function mmTo(e){
  const mm=document.getElementById('mm-canvas');if(!mm||!LI)return;
  const r=mm.getBoundingClientRect();
  const mw=mm.clientWidth,mh=64;
  const k=Math.min(mw/LI.w,mh/LI.h);
  const ox=(mw-LI.w*k)/2,oy=(mh-LI.h*k)/2;
  const wx=(e.clientX-r.left-ox)/k,wy=(e.clientY-r.top-oy)/k;
  const cv=document.getElementById('dep-canvas');
  V.x=(cv.clientWidth||830)/2-wx*V.s;V.y=(cv.clientHeight||500)/2-wy*V.s;
  draw();
}
function initMm(){
  const mm=document.getElementById('mm-canvas');if(!mm)return;
  let mdn=false;
  mm.addEventListener('mousedown',e=>{mdn=true;mmTo(e);e.preventDefault()});
  window.addEventListener('mousemove',e=>{if(mdn)mmTo(e)});
  window.addEventListener('mouseup',()=>{mdn=false});
}
function draw(){
  const cv=document.getElementById('dep-canvas');if(!cv||!window.BOARD_DATA)return;
  const nodes=window.BOARD_DATA;
  edges(nodes);
  const dpr=window.devicePixelRatio||1;
  const cw=cv.parentElement.clientWidth-24||830;
  const ch=Math.max(500,window.innerHeight*.7);
  cv.width=cw*dpr;cv.height=ch*dpr;cv.style.width=cw+'px';cv.style.height=ch+'px';
  const c=cv.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,cw,ch);
  LI=layout(nodes);
  if(V.s===1&&V.x===10){
    V.s=Math.max(1.8,Math.min(cw/LI.w,ch/LI.h,3));
    const curW=curWeek();
    let cx2=0,cy2=0,cnt=0;
    for(const q of Object.values(P)){
      const ws2=parseInt(q.weeks.split('-')[0].replace('W',''));
      const we2=q.weeks.includes('-')?parseInt(q.weeks.split('-')[1].replace('W','')):ws2;
      if(curW>=ws2&&curW<=we2){cx2+=q.x+q.w/2;cy2+=q.y+NH/2;cnt++}
    }
    if(cnt>0){cx2/=cnt;cy2/=cnt;V.x=cw/2-cx2*V.s;V.y=ch/2-cy2*V.s}
    else{V.x=(cw-LI.w*V.s)/2;V.y=Math.min(20,(ch-LI.h*V.s)/2)}
  }
  c.save();c.translate(V.x,V.y);c.scale(V.s,V.s);
  const dv=dim;
  const ih=x=>nb&&nb.ns.has(x);
  const eh=(f,t)=>nb&&nb.eg.some(e=>e.f===f&&e.t===t);

  // Quarters + week labels
  const ws=LI.ws;
  for(let q=0;q<NQ;q++){
    const qx=50+q*QWn*ws;const qw=QWn*ws;
    c.globalAlpha=1-dv*.95;
    // Чередующийся фон ПО НЕДЕЛЯМ (глобальная очерёдность)
    for(let w=0;w<QWn;w++){
      const wx2=qx+w*ws;
      c.fillStyle=(q*13+w)%2?'#eef2f7':'#f6f8fa';
      c.fillRect(wx2,32,ws,LI.h-47);
    }
    c.fillStyle='#1a365d';c.font='bold 14px Inter,sans-serif';c.textAlign='left';
    c.fillText(['Q1','Q2','Q3','Q4','Q5','Q6'][q],qx+3,16);
    c.fillStyle='#5a6a7a';c.font='7px Inter,sans-serif';c.textAlign='center';
    for(let w=0;w<QWn;w++)c.fillText('W'+(q*QWn+w+1),qx+(w+.5)*ws,28);
    c.strokeStyle='#b0b8c4';c.lineWidth=1;
    c.beginPath();c.moveTo(qx,32);c.lineTo(qx+qw,32);c.stroke();
    if(q>0){
      c.strokeStyle='#8a94a4';c.lineWidth=1.5;
      c.beginPath();c.moveTo(qx,32);c.lineTo(qx,LI.h-15);c.stroke();
    }
  }

  // Буферные недели (гейты G1–G6): жёлтая штриховка + бейдж
  for(let gi=0;gi<BUFW.length;gi++){
    const bw2=BUFW[gi];
    const bx=50+(bw2-1)*ws;
    c.save();
    c.beginPath();c.rect(bx,32,ws,LI.h-47);c.clip();
    c.fillStyle='rgba(245,158,11,.10)';
    c.fillRect(bx,32,ws,LI.h-47);
    c.strokeStyle='rgba(245,158,11,.28)';c.lineWidth=1;
    for(let hx=-LI.h;hx<ws;hx+=7){
      c.beginPath();c.moveTo(bx+hx,32);c.lineTo(bx+hx+LI.h,LI.h-15);c.stroke();
    }
    c.restore();
    c.strokeStyle='rgba(180,83,9,.5)';c.lineWidth=1.5;
    c.beginPath();c.moveTo(bx,32);c.lineTo(bx,LI.h-15);c.stroke();
    c.fillStyle='rgba(253,230,138,.95)';
    c.fillRect(bx+2,34,ws-4,13);
    c.strokeStyle='#b45309';c.lineWidth=1;
    c.strokeRect(bx+2,34,ws-4,13);
    c.fillStyle='#7c2d12';c.font='bold 8px Inter,sans-serif';c.textAlign='center';
    c.fillText('⚡G'+(gi+1),bx+ws/2,43.5);
  }

  // Пересчёт высоты потоков по фактическому содержимому
  for(const st of ST){
    let maxY=0;
    for(const p of Object.values(P))if(p.stream===st)maxY=Math.max(maxY,p.y+NH);
    LI.sH[st]=Math.max(NH+25,maxY-LI.sY[st]+15);
  }
  let cumY=50;
  for(const st of ST){
    const oldY=LI.sY[st];
    LI.sY[st]=cumY;
    const dy=cumY-oldY;
    if(dy!==0)for(const p of Object.values(P))if(p.stream===st)p.y+=dy;
    cumY+=LI.sH[st]+30;
  }
  LI.h=cumY+30;

  // Stream backgrounds
  ST.forEach(st=>{
    c.globalAlpha=1-dv*.6;
    const sc=SC[st]||'#5a6a7a';
    const r=parseInt(sc.slice(1,3),16),g=parseInt(sc.slice(3,5),16),b=parseInt(sc.slice(5,7),16);
    c.fillStyle='rgba('+r+','+g+','+b+',.05)';
    c.fillRect(15,LI.sY[st]-8,LI.w-30,LI.sH[st]+30);
    c.globalAlpha=1-dv*.85;
    const sy=LI.sY[st]+LI.sH[st]/2;
    c.save();c.translate(10,sy);c.rotate(-Math.PI/2);
    c.fillStyle=sc;c.font='bold 11px Inter,sans-serif';c.textAlign='center';
    c.fillText(SL[st]||st,0,0);c.restore();
    c.strokeStyle=sc+'40';c.setLineDash([3,5]);
    c.beginPath();c.moveTo(15,LI.sY[st]-8);c.lineTo(LI.w-15,LI.sY[st]-8);
    c.stroke();c.setLineDash([]);
  });

  // Edges
  nodes.forEach(n=>{
    const code=n[0],pr=n[5]||'';if(!pr)return;
    const to=P[code];if(!to)return;
    pr.split(',').forEach(p=>{
      p=p.trim();const from=P[p];if(!from)return;
      const pd=done(p);const hd=eh(p,code);
      c.globalAlpha=hd?1:(dv>0?1-dv*.96:1);
      const fx=from.x+from.w;
      const fy=from.y+(EO[p+'>'+code]||NH/2);
      const tx=to.x;const ty=to.y+(EO[p+'>'+code]||NH/2);
      const mx=MO[p+'>'+code]||fx+20;
      c.beginPath();
      if(Math.abs(fy-ty)<3){c.moveTo(fx,fy);c.lineTo(tx,ty)}
      else{
        const cr=Math.min(6,Math.abs(ty-fy)/2);
        c.moveTo(fx,fy);c.lineTo(mx-cr,fy);
        c.quadraticCurveTo(mx,fy,mx,fy+Math.sign(ty-fy)*cr);
        c.lineTo(mx,ty-Math.sign(ty-fy)*cr);
        c.quadraticCurveTo(mx,ty,mx+cr,ty);
        c.lineTo(tx,ty);
      }
      const pl=PART[code+'|'+p];
      if(pl){c.strokeStyle=pd?'#2e7d32':'#b45309';c.setLineDash([2,3]);c.lineWidth=hd?3:1.5;c.stroke();c.setLineDash([]);
        c.fillStyle='#7c2d12';c.font='bold 7px Inter,sans-serif';c.textAlign='center';c.fillText(pl,mx,(fy+ty)/2-3);}
      else if(pd){c.strokeStyle=hd?'rgba(46,125,50,.9)':'rgba(46,125,50,.35)';c.setLineDash(from.stream===to.stream?[]:[4,3]);c.lineWidth=hd?3:1.5}
      else{c.strokeStyle=hd?'rgba(220,20,60,.9)':'rgba(220,20,60,.45)';c.setLineDash([5,4]);c.lineWidth=hd?3:2}
      if(!pl){c.stroke();c.setLineDash([])}
    });
  });

  // Nodes
  nodes.forEach(n=>{
    const code=n[0];const p=P[code];if(!p)return;
    const d=done(code);
    let open=false;
    if(p.pr)p.pr.split(',').forEach(pr=>{if(!done(pr.trim()))open=true});
    const hd=ih(code);
    let al=(!hd&&dv>0)?1-dv*.88:1;
    if(SEARCH&&!(code.toLowerCase().includes(SEARCH)||((p.name||'')+'').toLowerCase().includes(SEARCH)))al*=.12;
    if(HIDEDONE&&d)al*=.1;
    c.globalAlpha=al;
    const x=p.x,y=p.y,w=p.w;
    const r=5;
    c.beginPath();
    c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+NH,r);c.arcTo(x+w,y+NH,x,y+NH,r);
    c.arcTo(x,y+NH,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();
    c.fillStyle=d?'#c8e6c9':(hd?'#e3ecf7':'#fff');c.fill();
    c.strokeStyle=SC[p.stream]||'#999';c.lineWidth=hd?3:2;c.stroke();
    const ins=1,ir=4;
    c.beginPath();
    c.moveTo(x+ins+ir,y+ins);c.arcTo(x+w-ins,y+ins,x+w-ins,y+NH-ins,ir);
    c.arcTo(x+w-ins,y+NH-ins,x+ins,y+NH-ins,ir);c.arcTo(x+ins,y+NH-ins,x+ins,y+ins,ir);
    c.arcTo(x+ins,y+ins,x+w-ins,y+ins,ir);c.closePath();
    if(d){c.strokeStyle='#2e7d32';c.lineWidth=1.5}
    else if(open){c.strokeStyle='#dc143c';c.lineWidth=1.5}
    else{c.strokeStyle='#f9a825';c.lineWidth=1.2}
    c.stroke();
    if(CRIT&&CRIT.has(code)){c.strokeStyle='rgba(245,158,11,.85)';c.lineWidth=2.2;c.setLineDash([5,3]);c.stroke();c.setLineDash([])}
    if(FLASH[code]){const ft=Date.now()-FLASH[code];if(ft<1500){c.strokeStyle='rgba(245,158,11,'+(1-ft/1500)+')';c.lineWidth=2.5;c.beginPath();c.arc(x+w/2,y+NH/2,NH*1.7+5*Math.sin(ft/110),0,6.3);c.stroke()}else delete FLASH[code]}
    // Text: код слева, недели справа
    c.save();
    c.beginPath();c.rect(x+1,y+1,w-2,NH-2);c.clip();
    c.fillStyle='#1a202c';c.font='bold 8px Inter,sans-serif';c.textAlign='left';
    c.fillText(code,x+5,y+14);
    c.font='6px Inter,sans-serif';c.fillStyle='#888';c.textAlign='right';
    let wk=p.weeks;
    if(c.measureText(wk).width>w*.4)wk=p.weeks.replace('W','');
    if(c.measureText(wk).width>w*.4)wk=''+p.wq;
    if(c.measureText(wk).width<=w*.4)c.fillText(wk,x+w-3,y+14);
    c.restore();
  });

  c.globalAlpha=1;c.restore();

  // Dual progress bars
  const bs=document.querySelectorAll('.ck'),bl=document.querySelectorAll('.blk-btn');
  let dd=0;bs.forEach(b=>{if(S[b.dataset.ck])dd++});bl.forEach(b=>{if(done(b.dataset.blk))dd++});
  const tt=bs.length+bl.length;
  const pp=tt?Math.round(dd/tt*100):0;
  const we=planWeek();
  const pe=Math.round(we/78*100);
  c.fillStyle='#e0e0e0';c.fillRect(8,ch-28,cw-16,8);
  c.fillStyle=pp>50?'#2e7d32':pp>20?'#f9a825':'#c62828';
  c.fillRect(8,ch-28,(cw-16)*pp/100,8);
  c.fillStyle='#d0d0d0';c.fillRect(8,ch-16,cw-16,4);
  c.fillStyle='#78909c';c.fillRect(8,ch-16,(cw-16)*pe/100,4);
  c.fillStyle='rgba(0,0,0,.6)';c.font='8px Inter,sans-serif';c.textAlign='left';
  c.fillText('Zoom: '+Math.round(V.s*100)+'% | Факт: '+dd+'/'+tt+' ('+pp+'%) | План: W'+we+'/'+TW+' ('+pe+'%)',8,ch-32);
}

// ===== INTERACTION =====
function hn(e,cv){
  const r=cv.getBoundingClientRect();
  const wx=(e.clientX-r.left-V.x)/V.s,wy=(e.clientY-r.top-V.y)/V.s;
  for(const[c,p]of Object.entries(P)){
    const pw=p.w||NW;
    if(wx>=p.x-2&&wx<=p.x+pw+2&&wy>=p.y-2&&wy<=p.y+NH+2)return c;
  }
  return null;
}
function he(e,cv){
  const r=cv.getBoundingClientRect();
  const wx=(e.clientX-r.left-V.x)/V.s,wy=(e.clientY-r.top-V.y)/V.s;
  if(!window.BOARD_DATA)return null;
  const tol=3/V.s;
  for(const n of window.BOARD_DATA){
    const c=n[0],pr=n[5]||'';if(!pr)continue;
    const to=P[c];if(!to)continue;
    for(const p of pr.split(',')){
      p=p.trim();const f=P[p];if(!f)continue;
      const fx=f.x+f.w,fy=f.y+(EO[p+'>'+c]||NH/2);
      const tx=to.x,ty=to.y+(EO[p+'>'+c]||NH/2);
      const mx=MO[p+'>'+c]||fx+20;
      if(Math.abs(wx-mx)<tol&&wy>Math.min(fy,ty)&&wy<Math.max(fy,ty)){
        let ins=false;
        for(const q of Object.values(P))if(wx>=q.x&&wx<=q.x+q.w&&wy>=q.y&&wy<=q.y+NH)ins=true;
        if(!ins)return{f:p,t:c};
      }
    }
  }
  return null;
}
function hm(){const m=document.getElementById('node-menu');if(m)m.remove()}
function co(code){
  const p=P[code];if(!p)return;
  const cv=document.getElementById('dep-canvas');
  const cw=cv.width/(window.devicePixelRatio||1);
  const ch=cv.height/(window.devicePixelRatio||1);
  V.x=cw/2-(p.x+(p.w||NW)/2)*V.s;
  V.y=ch/2-(p.y+NH/2)*V.s;
  hov=code;nb=hood(code);dimT=1;
  if(!raf)raf=requestAnimationFrame(anim);
  draw();
}
function sm(hit,sx,sy){
  hm();
  const m=document.createElement('div');m.id='node-menu';
  m.style.left=sx+'px';m.style.top=sy+'px';
  if(hit.t){ // edge
    const f=P[hit.f],t=P[hit.t];if(!f||!t)return;
    const fd=done(hit.f),td=done(hit.t);
    m.innerHTML='<div class="nm-header">'+hit.f+' \u2192 '+hit.t+'</div>'
      +'<div class="nm-sub">'+f.name+' \u2192 '+t.name+'</div>'
      +'<div class="nm-sub"><span style="color:'+(fd?'#2e7d32':'#c62828')+'">'+hit.f+(fd?' \u2713':' \u2717')+'</span> | <span style="color:'+(td?'#2e7d32':'#f9a825')+'">'+hit.t+(td?' \u2705':' \u2b1c')+'</span></div>'
      +'<div class="nm-action" data-c="'+hit.f+'">\u2190 \u041a '+hit.f+'</div>'
      +'<div class="nm-action" data-c="'+hit.t+'">\u2192 \u041a '+hit.t+'</div>';
  } else { // node
    const c=hit.c||hit.code;if(!c)return;
    const d=done(c);const p=P[c];if(!p)return;
    const bd=window.BOARD_DATA||[];
    let h='<div class="nm-header">'+c+' \u00b7 '+p.name+'</div>';
    h+='<div class="nm-sub">'+p.weeks+' \u00b7 \u043f\u043e\u0442\u043e\u043a '+p.stream+'</div>';
    if(p.pr){
      h+='<div class="nm-section">\u2190 \u0412\u0445\u043e\u0434\u044b:</div>';
      p.pr.split(',').forEach(pr=>{
        pr=pr.trim();const pp=P[pr];const pd=done(pr);
        if(pp)h+='<div class="nm-edge" data-c="'+pr+'"><span style="color:'+(pd?'#2e7d32':'#c62828')+'">'+(pd?'\u2713':'\u2717')+'</span> '+pr+' \u00b7 '+pp.name+'</div>';
      });
    }
    const deps=bd.filter(n=>n[5]&&n[5].split(',').map(x=>x.trim()).includes(c));
    if(deps.length){h+='<div class="nm-section">\u2192 \u0412\u044b\u0445\u043e\u0434\u044b:</div>';
      deps.forEach(dep=>{
        const dd2=done(dep[0]);const dp=P[dep[0]];
        if(dp)h+='<div class="nm-edge" data-c="'+dep[0]+'"><span style="color:'+(dd2?'#2e7d32':'#f9a825')+'">'+(dd2?'\u2705':'\u2b1c')+'</span> '+dep[0]+' \u00b7 '+dp.name+'</div>';
      });
    }
    h+='<div style="border-top:1px solid #e0e0e0"></div>';
    h+='<div class="nm-action" data-act="t">'+(d?'\u2610 \u0421\u043d\u044f\u0442\u044c':'\u2705 \u041e\u0442\u043c\u0435\u0442\u0438\u0442\u044c')+'</div>';
    h+='<div class="nm-action" data-act="g">\u2192 \u041a \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u044e</div>';
    m.innerHTML=h;
    m.querySelectorAll('[data-act]').forEach(el=>{
      el.onclick=()=>{
        if(el.dataset.act==='t'){
          if(d){S['b-'+c]=false}
          else{const a=allCk(c);
            if(a.n>0&&a.d<a.n){toast2('Блок '+c+': закрыто '+a.d+' из '+a.n+' пунктов — сначала закрой все')}
            else{S['b-'+c]=true}}
          save();
        }
        else{const t=document.getElementById('blk-'+c);if(t){t.scrollIntoView({behavior:'smooth',block:'start'});t.style.background='#fff3cd';setTimeout(()=>t.style.background='',2000)}}
        hm();
      };
    });
  }
  m.querySelectorAll('[data-c]').forEach(el=>{el.onclick=()=>{co(el.dataset.c);hm()}});
  document.body.appendChild(m);
  const mr=m.getBoundingClientRect();
  if(sx+mr.width>window.innerWidth)m.style.left=(window.innerWidth-mr.width-8)+'px';
  if(sy+mr.height>window.innerHeight)m.style.top=(window.innerHeight-mr.height-8)+'px';
  const closeH=e=>{if(!m.contains(e.target))hm();document.removeEventListener('click',closeH)};
  setTimeout(()=>document.addEventListener('click',closeH),50);
}

function zoomIn(){const cv=document.getElementById('dep-canvas');const cw=cv.clientWidth||830,ch=cv.clientHeight||500;const f=1.3;V.x=cw/2-(cw/2-V.x)*f;V.y=ch/2-(ch/2-V.y)*f;V.s=Math.min(5,V.s*f);draw()}
function zoomOut(){const cv=document.getElementById('dep-canvas');const cw=cv.clientWidth||830,ch=cv.clientHeight||500;const f=.75;V.x=cw/2-(cw/2-V.x)*f;V.y=ch/2-(ch/2-V.y)*f;V.s=Math.max(.15,V.s*f);draw()}
function zoomFit(){const cv=document.getElementById('dep-canvas');if(!cv||!LI)return;const cw=cv.clientWidth||830,ch=cv.clientHeight||500;V.s=Math.max(1.8,Math.min(cw/LI.w,ch/LI.h,3));V.x=(cw-LI.w*V.s)/2;V.y=Math.min(20,(ch-LI.h*V.s)/2);draw()}

function initCv(){
  const cv=document.getElementById('dep-canvas');if(!cv)return;
  cv.addEventListener('wheel',e=>{
    e.preventDefault();
    const r=cv.getBoundingClientRect();
    const mx=e.clientX-r.left,my=e.clientY-r.top;
    const f=e.deltaY<0?1.15:.87;
    V.x=mx-(mx-V.x)*f;V.y=my-(my-V.y)*f;
    V.s=Math.min(5,Math.max(.15,V.s*f));
    draw();
 },{passive:false});
  cv.addEventListener('mousedown',e=>{
    drag=true;dM=0;dX=e.clientX;dY=e.clientY;
    const nc=hn(e,cv);
    hit=nc?{c:nc}:he(e,cv);
    cv.style.cursor='grabbing';
  });
  window.addEventListener('mousemove',e=>{
    if(drag){
      const dx=e.clientX-dX,dy=e.clientY-dY;
      dM+=Math.abs(dx)+Math.abs(dy);
      V.x+=dx;V.y+=dy;dX=e.clientX;dY=e.clientY;
      draw();return;
    }
    if(e.target!==cv)return;
    const nc=hn(e,cv);
    if(nc){
      if(nc!==hov){hov=nc;nb=hood(nc);dimT=1;cv.style.cursor='pointer';if(!raf)raf=requestAnimationFrame(anim)}
    } else {
      cv.style.cursor=bufWk(e,cv)>0?'pointer':'grab';
      if(hov||nb){hov=null;nb=null;dimT=0;if(!raf)raf=requestAnimationFrame(anim)}
    }
  });
  window.addEventListener('mouseup',e=>{
    if(!drag)return;
    cv.style.cursor='grab';
    if(dM<5&&hit)sm(hit,e.clientX,e.clientY);
    else if(dM<5){
      hm();
      const wk2=bufWk(e,cv);
      if(wk2>0){
        const g=document.getElementById('gte-G'+(BUFW.indexOf(wk2)+1));
        if(g){g.scrollIntoView({behavior:'smooth',block:'start'});g.style.background='#fff3cd';setTimeout(()=>g.style.background='',2000)}
        else toast2('Буферная неделя W'+wk2+' — гейт G'+(BUFW.indexOf(wk2)+1));
      }
    }
    drag=false;hit=null;
  });
  window.addEventListener('resize',draw);
}

// ===== REFRESH =====
function refresh(){
  document.querySelectorAll('.ck').forEach(b=>b.checked=!!S[b.dataset.ck]);
  document.querySelectorAll('.blk-btn').forEach(b=>{
    const c=b.dataset.blk;const d=done(c);
    b.textContent=d? '\u2705':'\u2b1c';
    b.classList.toggle('done',d);
    const h=b.closest('h3');if(h)h.style.opacity=d?.6:1;
  });
  document.querySelectorAll('.xref[data-blk]').forEach(a=>{
    const c=a.dataset.blk;if(!c)return;
    a.classList.toggle('blk-done',done(c));
    a.classList.toggle('blk-todo',!done(c));
  });
  document.querySelectorAll('.kv b').forEach(b=>{
    if(b.textContent!=='\u0412\u0445\u043e\u0434:')return;
    const kv=b.parentElement;
    let r=kv.querySelector('.prereq-status');
    if(!r){r=document.createElement('span');r.className='prereq-status';kv.appendChild(r)}
    const refs=kv.querySelectorAll('.xref[data-blk]');
    const valid=Array.from(refs).filter(x=>window.BOARD_DATA&&window.BOARD_DATA.find(n=>n[0]===x.dataset.blk));
    if(valid.length>0){
      const all=valid.every(x=>done(x.dataset.blk));
      r.textContent=all?' \u2713':' \u2717';
      r.style.color=all?'#2e7d32':'#c62828';
    } else r.textContent='';
  });
  const bs=document.querySelectorAll('.ck'),bl=document.querySelectorAll('.blk-btn');
  let d=0;bs.forEach(b=>{if(S[b.dataset.ck])d++});bl.forEach(b=>{if(done(b.dataset.blk))d++});
  const t=bs.length+bl.length;
  const p=t?Math.round(d/t*100):0;
  const el=document.getElementById('progress');if(el)el.textContent=p+'%';
  const bar=document.getElementById('pbar');if(bar)bar.style.width=p+'%';
}

document.addEventListener('change',e=>{
  if(e.target.classList&&e.target.classList.contains('ck')){S[e.target.dataset.ck]=e.target.checked;save()}
});
document.addEventListener('click',e=>{
  if(e.target.classList&&e.target.classList.contains('blk-btn')){
    const c=e.target.dataset.blk;
    if(done(c)){S['b-'+c]=false;save()}
    else{
      const a=allCk(c);
      if(a.n>0&&a.d<a.n){toast2('Блок '+c+': закрыто '+a.d+' из '+a.n+' пунктов — сначала закрой все');e.target.classList.add('shake');setTimeout(()=>e.target.classList.remove('shake'),400)}
      else{S['b-'+c]=true;save()}
    }
  }
});
const _draw0=draw;
draw=function(){_draw0();mmDraw()};
(function(){
  const si=document.getElementById('cv-search');
  if(si)si.addEventListener('input',()=>{SEARCH=si.value.trim().toLowerCase();draw()});
  if(si)si.addEventListener('keydown',e=>{
    if(e.key==='Enter'){
      const ms=Object.keys(P).filter(c=>c.toLowerCase().includes(SEARCH)||(((P[c].name||'')+'').toLowerCase().includes(SEARCH)));
      if(ms.length){const idx=(si._i||0)%ms.length;si._i=(idx+1);focusNode(ms[idx]);toast2(ms[idx]+' ('+(idx+1)+'/'+ms.length+')')}
      e.preventDefault();
    }
    if(e.key==='Escape'){si.value='';SEARCH='';draw()}
  });
  const hd=document.getElementById('cv-hide-done');
  if(hd)hd.addEventListener('change',()=>{HIDEDONE=hd.checked;draw()});
  const cr=document.getElementById('cv-crit');
  if(cr)cr.addEventListener('change',()=>{CRIT=cr.checked?critSet():null;draw();if(cr.checked)toast2('Критический путь: '+CRIT.size+' узлов до ближайшего гейта')});
  const rs=document.getElementById('cv-reset');
  if(rs)rs.addEventListener('click',()=>{
    if(!confirm('Сбросить ВЕСЬ прогресс (все чекбоксы и блоки)?'))return;
    const prev=JSON.stringify(S);
    S={};save();
    let u=document.getElementById('undo2');
    if(u)u.remove();
    u=document.createElement('div');u.id='undo2';
    u.innerHTML='Прогресс сброшен. <button>Отменить</button>';
    document.body.appendChild(u);
    const h=setTimeout(()=>u.remove(),10000);
    u.querySelector('button').onclick=()=>{S=JSON.parse(prev);save();clearTimeout(h);u.remove();toast2('Восстановлено')};
  });
})();
document.addEventListener('click',e=>{if(e.target.classList&&e.target.classList.contains('cvf')){e.preventDefault();focusNode(e.target.dataset.blk)}});
document.addEventListener('DOMContentLoaded',()=>{
  const sw=document.getElementById('stat-weeks');if(sw)sw.textContent=TW;
  const ss=document.getElementById('stat-streams');if(ss)ss.textContent=ST.length;
  refresh();initCv();initMm();draw();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>draw())});
