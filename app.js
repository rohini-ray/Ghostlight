const form = document.querySelector('#composeForm');
const input = document.querySelector('#promptInput');
const conversation = document.querySelector('#conversation');
const sendButton = document.querySelector('#sendButton');
const modelStatus = document.querySelector('#modelStatus');
const statusText = document.querySelector('#statusText');
const modelHint = document.querySelector('#modelHint');
const settingsPanel = document.querySelector('#settingsPanel');
const panelBackdrop = document.querySelector('#panelBackdrop');
const gemmaKeyInput = document.querySelector('#gemmaKeyInput');
const elevenKeyInput = document.querySelector('#elevenKeyInput');
const GEMMA_KEY_SLOT = 'ghostlight-gemma-key';
const ELEVEN_KEY_SLOT = 'ghostlight-eleven-key';
let online = false;
let busy = false;

function setConnection(ok, message = '') {
  online = ok;
  modelStatus.classList.toggle('offline', !ok);
  statusText.textContent = message || (ok ? 'GEMMA · READY' : 'GOOGLE AI KEY NEEDED');
  modelHint.textContent = ok ? 'Gemma replies · ElevenLabs voice on request' : 'add a Gemma key in settings';
}
function openSettings() {
  gemmaKeyInput.value = sessionStorage.getItem(GEMMA_KEY_SLOT) || '';
  elevenKeyInput.value = sessionStorage.getItem(ELEVEN_KEY_SLOT) || '';
  settingsPanel.classList.add('open'); panelBackdrop.classList.add('open'); settingsPanel.setAttribute('aria-hidden','false');
}
function closeSettings() { settingsPanel.classList.remove('open'); panelBackdrop.classList.remove('open'); settingsPanel.setAttribute('aria-hidden','true'); }
function addMessage(kind, text, stamp = 'just now') {
  const article = document.createElement('article'); article.className = `message ${kind}-message`;
  const speaker = document.createElement('div'); speaker.className = 'speaker';
  const icon = document.createElement('span'); icon.className = 'ghost-icon'; icon.textContent = kind === 'ghost' ? '✳' : '◇';
  const name = document.createElement('span'); name.textContent = kind === 'ghost' ? 'THE GHOST' : 'YOU';
  const time = document.createElement('time'); time.textContent = stamp;
  const body = document.createElement('div'); body.className = 'message-body'; body.textContent = text;
  speaker.append(icon,name,time); article.append(speaker,body); conversation.append(article); conversation.scrollTop = conversation.scrollHeight; return body;
}
async function checkStatus() {
  try {
    const response = await fetch('/api/status');
    const data = await response.json();
    const gemmaReady = Boolean(sessionStorage.getItem(GEMMA_KEY_SLOT) || data.ok);
    const voiceReady = Boolean(sessionStorage.getItem(ELEVEN_KEY_SLOT) || data.voice);
    setConnection(gemmaReady, gemmaReady ? `GEMMA · ${data.model.toUpperCase()}` : 'GOOGLE AI KEY NEEDED');
    if (gemmaReady && !voiceReady) modelHint.textContent = 'Gemma ready · add an ElevenLabs key for voice';
  } catch { setConnection(false); }
}
async function send(text) {
  const prompt = text.trim(); if (!prompt || busy) return;
  document.querySelector('#promptIdeas')?.remove(); addMessage('user',prompt);
  const reply = addMessage('ghost','The room is listening…'); reply.classList.add('thinking');
  busy = true; sendButton.disabled = true; modelStatus.classList.add('busy'); input.value = '';
  try {
    const response = await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,gemma_api_key:sessionStorage.getItem(GEMMA_KEY_SLOT) || ''})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The room went quiet. Check your Google AI key and Gemma model setting.');
    reply.textContent = data.reply; reply.classList.remove('thinking'); setConnection(true);
    const listen = document.createElement('button'); listen.className = 'listen-button'; listen.type = 'button'; listen.textContent = '▶  Listen'; listen.setAttribute('aria-label','Listen to the ghost reply');
    listen.addEventListener('click', async () => {
      listen.disabled = true; listen.textContent = '◌  Calling the voice…';
      try {
        const audioResponse = await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:data.reply,elevenlabs_api_key:sessionStorage.getItem(ELEVEN_KEY_SLOT) || ''})});
        if (!audioResponse.ok) { const errorData = await audioResponse.json(); throw new Error(errorData.error || 'Voice service unavailable.'); }
        const audioUrl = URL.createObjectURL(await audioResponse.blob());
        const player = new Audio(audioUrl); player.onended = () => URL.revokeObjectURL(audioUrl); await player.play();
        listen.textContent = '▶  Listen again';
      } catch (error) { listen.textContent = error.message; }
      finally { listen.disabled = false; }
    });
    reply.after(listen);
  } catch (error) {
    reply.textContent = error.message;
    reply.classList.remove('thinking'); setConnection(false);
  } finally { busy = false; sendButton.disabled = false; modelStatus.classList.remove('busy'); input.focus(); }
}
form.addEventListener('submit', event => { event.preventDefault(); send(input.value); });
input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight,90)}px`; });
document.querySelectorAll('.idea-chip').forEach(button => button.addEventListener('click', () => { input.value = button.dataset.prompt; input.focus(); input.dispatchEvent(new Event('input')); }));
document.querySelector('#settingsToggle').addEventListener('click',openSettings);
document.querySelector('#roomSettingsToggle').addEventListener('click',openSettings);
document.querySelector('#settingsClose').addEventListener('click',closeSettings);
panelBackdrop.addEventListener('click',closeSettings);
document.querySelector('#saveSettings').addEventListener('click', async () => {
  const gemmaKey = gemmaKeyInput.value.trim();
  const elevenKey = elevenKeyInput.value.trim();
  if (gemmaKey) sessionStorage.setItem(GEMMA_KEY_SLOT, gemmaKey); else sessionStorage.removeItem(GEMMA_KEY_SLOT);
  if (elevenKey) sessionStorage.setItem(ELEVEN_KEY_SLOT, elevenKey); else sessionStorage.removeItem(ELEVEN_KEY_SLOT);
  closeSettings();
  await checkStatus();
});
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeSettings(); });
checkStatus();
