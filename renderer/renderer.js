(() => {
  let api = 'http://localhost:4000';
  let socket = null;
  let currentChannel = null;

  const $ = id => document.getElementById(id);

  async function loadChannels(){
    if (!api) return alert('Server not connected');
    const r = await fetch(api + '/api/channels');
    const arr = await r.json();
    const wrap = $('channels'); wrap.innerHTML = '';
    arr.forEach(c=>{
      const el = document.createElement('div');
      el.className = 'channel';
      el.textContent = c.name + ' (' + c.id + ')';
      el.onclick = ()=>{ joinChannel(c.id, c.name); };
      wrap.appendChild(el);
    });
  }

  async function createChannel(){
    const name = $('chanName').value.trim();
    if(!name) return alert('name');
    await fetch(api + '/api/channels', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ name })});
    $('chanName').value='';
    loadChannels();
  }

  function leaveChannel(){
    if (!currentChannel) return;
    if (!socket) return;
    socket.emit('leaveChannel', { channelId: currentChannel, userId: 'local-user' });
    currentChannel = null;
    $('chanTitle').textContent = 'No channel';
    $('notes').innerHTML = '';
  }

  function connectServer(){
    const url = $('serverUrl').value.trim();
    if(!url) return alert('Enter server URL');
    api = url.replace(/\/$/, '');
    if (socket) socket.close();
    socket = io(api);
    socket.on('connect', ()=>{
      console.log('connected to', api);
      loadChannels();
    });
    socket.on('disconnect', ()=>console.log('socket disconnected'));
    socket.on('notesList', notes=>{
      // relay to existing handler
      const w = $('notes'); w.innerHTML = '';
      notes.forEach(n=>{
        const d = document.createElement('div'); d.className='note';
        d.innerHTML = `<div class="meta">${new Date(n.createdAt).toLocaleString()} ${n.author||''}</div><div>${n.content}</div>`;
        const del = document.createElement('button'); del.textContent='Delete'; del.onclick=()=>socket.emit('deleteNote',{channelId: n.channelId, noteId: n.id});
        d.appendChild(del);
        w.appendChild(d);
      });
    });
    socket.on('noteAdded', n=>{
      if (n.channelId !== currentChannel) return;
      const w = $('notes'); const d = document.createElement('div'); d.className='note';
      d.innerHTML = `<div class="meta">${new Date(n.createdAt).toLocaleString()} ${n.author||''}</div><div>${n.content}</div>`;
      const del = document.createElement('button'); del.textContent='Delete'; del.onclick=()=>socket.emit('deleteNote',{channelId: n.channelId, noteId: n.id});
      d.appendChild(del); w.appendChild(d);
    });
    socket.on('noteDeleted', id=>{
      Array.from(document.querySelectorAll('.note')).forEach(el=>{ if (el.dataset.id===id) el.remove(); });
    });
  }

  function joinChannel(id, name){
    currentChannel = id;
    $('chanTitle').textContent = name + ' — ' + id;
    socket.emit('joinChannel', { channelId: id, userId: 'local-user' });
  }

  $('createChan').addEventListener('click', createChannel);
  $('connectServer').addEventListener('click', connectServer);
  // add leave button
  const leaveBtn = document.createElement('button'); leaveBtn.textContent='Leave Channel'; leaveBtn.onclick = leaveChannel;
  document.querySelector('.right').insertBefore(leaveBtn, document.querySelector('.right').children[1]);
  $('connectServer').addEventListener('click', connectServer);

  $('saveNote').addEventListener('click', ()=>{
    const content = $('noteInput').value.trim();
    if(!content) return;
    const ttl = parseInt($('ttl').value) || 0;
    const persistent = !!$('persistent').checked;
    socket.emit('saveNote', { channelId: currentChannel, content, ttlSeconds: ttl, author: 'local-user', persistent });
    $('noteInput').value='';
  });

  socket.on('notesList', notes=>{
    const w = $('notes'); w.innerHTML = '';
    notes.forEach(n=>{
      const d = document.createElement('div'); d.className='note';
      d.innerHTML = `<div class="meta">${new Date(n.createdAt).toLocaleString()} ${n.author||''}</div><div>${n.content}</div>`;
      const del = document.createElement('button'); del.textContent='Delete'; del.onclick=()=>socket.emit('deleteNote',{channelId: n.channelId, noteId: n.id});
      d.appendChild(del);
      w.appendChild(d);
    });
  });

  socket.on('noteAdded', n=>{
    if (n.channelId !== currentChannel) return;
    const w = $('notes'); const d = document.createElement('div'); d.className='note';
    d.innerHTML = `<div class="meta">${new Date(n.createdAt).toLocaleString()} ${n.author||''}</div><div>${n.content}</div>`;
    const del = document.createElement('button'); del.textContent='Delete'; del.onclick=()=>socket.emit('deleteNote',{channelId: n.channelId, noteId: n.id});
    d.appendChild(del); w.appendChild(d);
  });

  socket.on('noteDeleted', id=>{
    Array.from(document.querySelectorAll('.note')).forEach(el=>{ if (el.dataset.id===id) el.remove(); });
    // reload simple
    loadChannels();
  });

  loadChannels();
})();
