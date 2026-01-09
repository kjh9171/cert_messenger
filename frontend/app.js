(() => {
  const socket = io();
  let currentChannel = null;
  const $ = id => document.getElementById(id);

  function formatNote(n){
    const d = new Date(n.createdAt);
      (function() {
        // Connect explicitly to backend socket server (port 3100)
        const backendHost = (location.hostname || 'localhost');
        const backendProto = location.protocol === 'https:' ? 'https:' : 'http:';
        const socketUrl = `${backendProto}//${backendHost}:3100`;
        const socket = io(socketUrl);
      ${n.expiresAt?`<div>Expires: ${new Date(n.expiresAt).toLocaleString()}</div>`:''}
      <button onclick="(function(id){window.deleteNote(id)})(\'${n.id}\')">삭제</button>
    </div>`;
  }

  window.deleteNote = (noteId) => {
    if (!currentChannel) return alert('채널 없음');
    socket.emit('deleteNote', { channelId: currentChannel, noteId });
  };

  $('joinBtn').addEventListener('click', () => {
    let id = $('channelId').value.trim();
    if (!id) return alert('채널 ID를 입력하세요');
    // if link, try to extract last segment
    try { const u = new URL(id); id = u.pathname.split('/').pop(); } catch(e){}
    const userId = $('userId').value.trim() || 'guest-' + Math.floor(Math.random()*1000);
    currentChannel = id;
    socket.emit('joinChannel', { channelId: id, userId });
    document.getElementById('controls').style.display = 'block';
  });

  $('saveNote').addEventListener('click', () => {
    const content = $('content').value.trim();
    if (!content) return alert('내용 필요');
    const type = $('type').value;
    const ttl = parseInt($('ttl').value) || 0;
    socket.emit('saveNote', { channelId: currentChannel, content, type, ttlSeconds: ttl, author: $('userId').value || 'web' });
    $('content').value = '';
  });

  socket.on('notesList', notes => {
    const wrap = $('notes'); wrap.innerHTML = '';
    notes.forEach(n => wrap.insertAdjacentHTML('beforeend', formatNote(n)));
  });
  socket.on('noteAdded', n => {
    $('notes').insertAdjacentHTML('beforeend', formatNote(n));
  });
  socket.on('noteDeleted', id => {
    const el = document.querySelector(`[data-id="${id}"]`);
    if (el) el.remove();
  });
  socket.on('roomFull', d => alert(d.message || 'room full'));
  socket.on('updateMembers', members => console.log('members', members));
})();

// E2E key generation and registration
(() => {
  const $ = id => document.getElementById(id);
  let keyPair = null;
  $('genKey').addEventListener('click', () => {
    keyPair = nacl.box.keyPair();
    const pub = nacl.util.encodeBase64(keyPair.publicKey);
    $('pubKey').textContent = pub;
    console.log('keypair generated');
  });

  $('registerKey').addEventListener('click', async () => {
    const token = $('authToken').value.trim();
    if (!keyPair) return alert('Generate keypair first');
    const pub = nacl.util.encodeBase64(keyPair.publicKey);
    try {
      const res = await fetch('/api/keys', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': token ? `Bearer ${token}` : '' }, body: JSON.stringify({ publicKey: pub }) });
      const j = await res.json();
      if (!res.ok) return alert('Error: ' + JSON.stringify(j));
      alert('Public key registered');
    } catch (e) {
      alert('Network error');
    }
  });
})();
