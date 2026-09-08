const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const form=$("#planner-form"), error=$("#error"), start=$("#start-date"), end=$("#end-date");
const custom=$("#custom-style"), count=$("#count"), submit=$("#submit");
let styles=[], map, line, markers=[], lastBounds=null;

$$(".chips button").forEach(b=>b.onclick=()=>{const s=b.dataset.style;if(styles.includes(s)){styles=styles.filter(x=>x!==s);b.classList.remove("selected")}else{styles.push(s);b.classList.add("selected")}});
custom.oninput=()=>count.textContent=custom.value.length;
const today=new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10); start.min=today;end.min=today;
start.onchange=()=>{end.min=start.value||today;if(end.value<end.min)end.value=end.min};

function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function fmt(s){const d=new Date(s+"T00:00:00");return `${d.getMonth()+1}월 ${d.getDate()}일`}

function render(data){
  const total=data.days.reduce((n,d)=>n+d.places.length,0);
  const valid=data.days.reduce((n,d)=>n+d.places.filter(p=>p.lat!=null&&p.lng!=null&&Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lng))).length,0);
  $("#title").textContent=`${data.destination.name} ${data.days.length-1}박 ${data.days.length}일`;
  $("#summary").textContent=`${data.destination.reason||"AI가 여행 스타일에 맞춰 구성한 일정입니다."} (지도에 표시된 장소: ${valid}/${total})`;
  const days=data.days.map(day=>`<article class="day"><div class="day-head"><b>DAY ${day.day}</b><span>${fmt(day.date)}</span></div>
  ${day.places.map(p=>`<div class="place"><time>${esc(p.start_time||"")}</time><div><h4>${esc(p.name)}</h4><p>${esc(p.category||"추천 장소")} · ${esc(p.address||"주소 확인 필요")}</p><p>${esc(p.reason||"")}</p>${!p.lat?`<p style="color:#9C4A22">⚠ 실제 장소 확인 실패 — 지도에 표시되지 않음</p>`:""}${p.place_url?`<a target="_blank" rel="noopener" href="${esc(p.place_url)}">카카오맵에서 보기 ↗</a>`:""}</div></div>`).join("")}</article>`).join("");
  $(".days").innerHTML=days;
  location.hash="result";
  requestAnimationFrame(()=>requestAnimationFrame(()=>drawMap(data)));
}

function initMap(){
  if(!window.kakao||!kakao.maps){$("#map").innerHTML="<div class='empty'><b>Kakao Maps를 불러오지 못했습니다.</b><br>JavaScript 키와 도메인 설정을 확인해주세요.</div>";return}
  kakao.maps.load(()=>{
    map=new kakao.maps.Map(document.getElementById("map"),{center:new kakao.maps.LatLng(36.2,127.9),level:13}); // 대한민국 전체 뷰
  });
}

function drawMap(data){
  const places=data.days.flatMap(d=>d.places).filter(p=>p.lat!=null&&p.lng!=null&&Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lng)));
  markers.forEach(m=>m.setMap(null));markers=[];
  if(line){line.setMap(null);line=null}
  if(!places.length){
    if(map)map.relayout();
    const note=document.createElement("div");
    note.className="empty";note.id="map-note";
    note.style.cssText="position:absolute;inset:0;z-index:5;background:#F1ECDFcc";
    note.innerHTML="<strong>⚠</strong><h3>표시할 장소가 없습니다</h3><p>AI가 만든 장소들을 실제 위치로 확인하지 못했습니다. 일정을 다시 만들어보세요.</p>";
    const old=document.getElementById("map-note");if(old)old.remove();
    document.querySelector(".map").appendChild(note);
    return;
  }
  const old=document.getElementById("map-note");if(old)old.remove();
  if(!map)return;
  const bounds=new kakao.maps.LatLngBounds(), path=[];
  places.forEach(p=>{const pos=new kakao.maps.LatLng(+p.lat,+p.lng);bounds.extend(pos);path.push(pos);markers.push(new kakao.maps.Marker({map,position:pos,title:p.name}))});
  line=new kakao.maps.Polyline({map,path,strokeWeight:4,strokeColor:"#214d3a",strokeOpacity:.75});
  lastBounds=bounds;
  map.relayout();
  map.setBounds(bounds,50,50,50,50);
  setTimeout(()=>{map.relayout();map.setBounds(bounds,50,50,50,50)},150);
}

document.addEventListener("visibilitychange",()=>{
  if(!document.hidden&&map){
    map.relayout();
    if(lastBounds)map.setBounds(lastBounds,50,50,50,50);
  }
});

document.addEventListener("DOMContentLoaded",initMap);
form.onsubmit=async e=>{
  e.preventDefault();error.hidden=true;
  if(!start.value||!end.value){error.textContent="여행 시작일과 종료일을 선택해주세요.";error.hidden=false;return}
  const n=Math.round((new Date(end.value)-new Date(start.value))/86400000)+1;
  if(n<1||n>7){error.textContent="여행 기간은 1~7일로 설정해주세요.";error.hidden=false;return}
  submit.disabled=true;submit.querySelector(".spinner").hidden=false;
  try{
    const r=await fetch("/api/plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({start_date:start.value,end_date:end.value,styles,custom_style:custom.value.trim()})});
    const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||"여행 계획을 만들지 못했습니다.");render(d);
  }catch(err){error.textContent=err.message||"잠시 후 다시 시도해주세요.";error.hidden=false}
  finally{submit.disabled=false;submit.querySelector(".spinner").hidden=true}
};

window.testMap=()=>render({
  destination:{name:"서울",reason:"테스트용 더미 데이터입니다."},
  days:[{day:1,date:new Date().toISOString().slice(0,10),places:[
    {name:"서울시청",category:"관광",start_time:"09:30",end_time:"10:30",reason:"테스트",address:"서울 중구",lat:37.5665,lng:126.9780},
    {name:"광화문",category:"관광",start_time:"11:00",end_time:"12:00",reason:"테스트",address:"서울 종로구",lat:37.5759,lng:126.9769},
    {name:"경복궁",category:"관광",start_time:"12:30",end_time:"14:00",reason:"테스트",address:"서울 종로구",lat:37.5796,lng:126.9770}
  ]}]
});
