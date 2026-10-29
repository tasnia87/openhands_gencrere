const $ = id => document.getElementById(id);
let user, room=null, stream=new MediaStream(), peers=new Map(), cursor=0, timer, polling=false;
function notice(text=''){ $('notice').textContent=text; $('notice').hidden=!text; }
async function api(path, data){
 const r=await fetch('/api'+path, data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const result=await r.json(); if(!r.ok) throw Error(result.error||'Request failed.'); return result;
}
function el(tag, cls, text){const n=document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n;}
async function dashboard(){
 user=await api('/me'); $('login').hidden=true; $('dashboard').hidden=false; $('meeting').hidden=true;
 $('identity').replaceChildren(el('span','',user.name+' · '+user.role));
 const out=el('button','','Sign out');out.onclick=async()=>{await api('/logout',{});location.reload();};$('identity').append(out);
 $('new-button').hidden=user.role!=='host';
 const rooms=await api('/webinars');$('room-count').textContent=rooms.length;$('rooms').replaceChildren();
 for(const r of rooms){
  const card=el('article','card'), art=el('div','card-art');art.append(el('span','pill',r.online?r.online+' in the room':'Open room'),el('span','room-symbol','◉'));
  const body=el('div','card-body');body.append(el('h2','',r.title),el('p','',r.description||'A space for your next conversation.'));
  const foot=el('div','card-footer'), join=el('button','primary','Join room ↗');join.onclick=async()=>{join.disabled=true;try{await joinRoom(r);}catch(e){notice(e.message);}finally{join.disabled=false;}};
  foot.append(el('small','','Hosted by '+r.host_name),join);body.append(foot);card.append(art,body);$('rooms').append(card);
 }
}
$('login-form').onsubmit=async e=>{e.preventDefault();try{await api('/login',{email:$('email').value,password:$('password').value});notice();await dashboard();}catch(e){notice(e.message);}};
$('new-button').onclick=()=>$('create-dialog').showModal();$('cancel').onclick=()=>$('create-dialog').close();
$('create-form').onsubmit=async e=>{e.preventDefault();try{await api('/webinars',{title:$('title').value,description:$('description').value});$('create-dialog').close();e.target.reset();await dashboard();notice();}catch(e){notice(e.message);}};
async function joinRoom(r){
 const joined=await api('/webinars/'+r.id+'/join',{});room={...r,pid:joined.participant_id};cursor=0;notice();
 $('dashboard').hidden=true;$('meeting').hidden=false;$('meeting-title').textContent=r.title;
 $('connection-status').textContent='You’re in. Waiting for others to join.';
 timer=setInterval(poll,1200);await poll();
}
function base(){return '/webinars/'+room.id;}
async function send(id,payload){if(room)await api(base()+'/signals',{participant_id:room.pid,recipient:id,payload});}
function createPeer(person){
 const pc=new RTCPeerConnection({iceServers:[]});
 const tile=el('div','video-tile');tile.append(el('div','avatar',person.name.split(' ').map(s=>s[0]).join('')));
 const video=el('video');video.autoplay=true;video.playsInline=true;tile.append(video,el('span','video-label',person.name));$('videos').append(tile);
 const p={pc,tile,video,queue:[],audio:pc.addTransceiver('audio',{direction:'sendrecv'}),videoTx:pc.addTransceiver('video',{direction:'sendrecv'})};peers.set(person.id,p);
 for(const track of stream.getTracks()){(track.kind==='audio'?p.audio:p.videoTx).sender.replaceTrack(track);}
 pc.onicecandidate=e=>{if(e.candidate)send(person.id,{type:'ice',candidate:e.candidate.toJSON()}).catch(e=>notice(e.message));};
 pc.ontrack=e=>{if(!video.srcObject)video.srcObject=new MediaStream();video.srcObject.addTrack(e.track);video.play().catch(()=>notice('Click in the room if your browser blocks audio playback.'));};
 pc.onconnectionstatechange=()=>{if(pc.connectionState==='failed')notice('Video connection failed. This prototype supports local testing; leave and rejoin to retry.');};
 return p;
}
async function poll(){
 if(!room||polling)return;polling=true;
 try{
  const current=room;
  const result=await api(base()+'/signals?participant_id='+room.pid+'&after='+cursor);
  if(room!==current)return;
  $('people').replaceChildren();$('people-count').textContent=result.peers.length;
  for(const person of result.peers){const row=el('div','person'), info=el('div','',person.name+(person.id===room.pid?' (you)':''));info.append(el('small','',person.role));row.append(el('span','person-icon',person.name[0]),info);$('people').append(row);
   if(person.id!==room.pid&&!peers.has(person.id)){
    const p=createPeer(person);
    if(room.pid<person.id){await p.pc.setLocalDescription(await p.pc.createOffer());await send(person.id,{type:'offer',sdp:p.pc.localDescription.sdp});}
   }
  }
  for(const [id,p] of peers){if(!result.peers.some(x=>x.id===id)){p.pc.close();p.tile.remove();peers.delete(id);}}
  for(const signal of result.signals){
   const p=peers.get(signal.sender), data=signal.payload;
   if(p){
    if(data.type==='ice'){if(p.pc.remoteDescription)await p.pc.addIceCandidate(data.candidate);else p.queue.push(data.candidate);}
    else{await p.pc.setRemoteDescription({type:data.type,sdp:data.sdp});for(const c of p.queue)await p.pc.addIceCandidate(c);p.queue=[];
     if(data.type==='offer'){await p.pc.setLocalDescription(await p.pc.createAnswer());await send(signal.sender,{type:'answer',sdp:p.pc.localDescription.sdp});}}
   }
   cursor=signal.id;
  }
  $('connection-status').textContent=result.peers.length===1?'You’re in. Waiting for others to join.':result.peers.length+' people in this room';
 }catch(e){notice(e.message);}finally{polling=false;}
}
async function toggle(kind){
 const button=$(kind==='audio'?'mic':'camera');button.disabled=true;
 try{
  let track=stream.getTracks().find(t=>t.kind===kind&&t.readyState==='live');
  if(track){track.enabled=!track.enabled;}
  else{
   if(!navigator.mediaDevices)throw Error('Camera and microphone require localhost or HTTPS.');
   const media=await navigator.mediaDevices.getUserMedia(kind==='audio'?{audio:true}:{video:true});
   if(!room){media.getTracks().forEach(t=>t.stop());return;}
   track=media.getTracks()[0];stream.addTrack(track);$('local-video').srcObject=stream;
   for(const p of peers.values())await (kind==='audio'?p.audio:p.videoTx).sender.replaceTrack(track);
  }
  button.textContent=(track.enabled?'Disable ':'Enable ')+(kind==='audio'?'microphone':'camera');notice();
 }catch(e){notice('Could not enable media: '+e.message);}finally{button.disabled=false;}
}
$('mic').onclick=()=>toggle('audio');$('camera').onclick=()=>toggle('video');
async function leave(){
 if(!room)return;const current=room;room=null;clearInterval(timer);
 for(const p of peers.values()){p.pc.close();p.tile.remove();}peers.clear();
 stream.getTracks().forEach(t=>t.stop());stream=new MediaStream();$('local-video').srcObject=null;
 $('mic').textContent='Enable microphone';$('camera').textContent='Enable camera';
 try{await api('/webinars/'+current.id+'/leave',{participant_id:current.pid});await dashboard();notice();}catch(e){notice(e.message);}
}
$('leave').onclick=leave;
window.addEventListener('pagehide',()=>{if(room){fetch('/api'+base()+'/leave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({participant_id:room.pid}),keepalive:true});stream.getTracks().forEach(t=>t.stop());}});
api('/me').then(dashboard).catch(()=>{});
