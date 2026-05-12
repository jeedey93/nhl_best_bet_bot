(function () {
  if (document.getElementById('pd-chat-widget')) return;

  const style = document.createElement('style');
  style.textContent = `
    #pd-chat-widget * { box-sizing: border-box; margin: 0; padding: 0; }

    #pd-chat-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 52px; height: 52px; border-radius: 50%;
      background: #c8102e; border: none; cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
      display: flex; align-items: center; justify-content: center;
      font-size: 22px; transition: transform 0.2s, background 0.2s;
    }
    #pd-chat-btn:hover { background: #e0122e; transform: scale(1.08); }

    #pd-chat-panel {
      position: fixed; bottom: 88px; right: 24px; z-index: 9999;
      width: 360px; height: 500px;
      background: #07111f;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 14px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.7);
      display: flex; flex-direction: column;
      font-family: 'Barlow Condensed', sans-serif;
      overflow: hidden;
      transition: opacity 0.2s, transform 0.2s;
    }
    #pd-chat-panel.hidden { opacity: 0; pointer-events: none; transform: translateY(12px); }

    #pd-chat-header {
      background: #0d1e30;
      padding: 12px 16px;
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    #pd-chat-header-title {
      font-size: 1rem; font-weight: 700; letter-spacing: 1px;
      color: #fff; text-transform: uppercase;
    }
    #pd-chat-header-sub {
      font-size: 0.75rem; color: #64748b; margin-top: 1px;
    }
    #pd-chat-close {
      background: none; border: none; cursor: pointer;
      color: #64748b; font-size: 18px; line-height: 1;
      padding: 2px 6px; border-radius: 4px;
      transition: color 0.15s;
    }
    #pd-chat-close:hover { color: #fff; }

    #pd-chat-messages {
      flex: 1; overflow-y: auto; padding: 14px 12px;
      display: flex; flex-direction: column; gap: 10px;
      scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent;
    }

    .pd-msg {
      max-width: 82%; padding: 8px 12px;
      border-radius: 10px; font-size: 0.9rem; line-height: 1.45;
      word-break: break-word; white-space: pre-wrap;
    }
    .pd-msg-user {
      align-self: flex-end;
      background: #c8102e; color: #fff;
      border-bottom-right-radius: 3px;
    }
    .pd-msg-bot {
      align-self: flex-start;
      background: rgba(255,255,255,0.07); color: #e2e8f0;
      border-bottom-left-radius: 3px;
    }
    .pd-msg-bot strong { color: #ffb81c; }

    .pd-typing {
      align-self: flex-start;
      background: rgba(255,255,255,0.07);
      border-radius: 10px; border-bottom-left-radius: 3px;
      padding: 10px 14px; display: flex; gap: 5px; align-items: center;
    }
    .pd-typing span {
      width: 7px; height: 7px; border-radius: 50%;
      background: #64748b; display: inline-block;
      animation: pd-bounce 1.2s infinite ease-in-out;
    }
    .pd-typing span:nth-child(2) { animation-delay: 0.2s; }
    .pd-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes pd-bounce {
      0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
      40% { transform: scale(1.2); opacity: 1; }
    }

    #pd-chat-input-row {
      padding: 10px 12px;
      border-top: 1px solid rgba(255,255,255,0.08);
      display: flex; gap: 8px;
    }
    #pd-chat-input {
      flex: 1; background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 8px; padding: 8px 12px;
      color: #fff; font-family: 'Barlow Condensed', sans-serif;
      font-size: 0.95rem; outline: none;
      transition: border-color 0.2s;
    }
    #pd-chat-input:focus { border-color: rgba(200,16,46,0.6); }
    #pd-chat-input::placeholder { color: #475569; }
    #pd-chat-send {
      background: #c8102e; border: none; border-radius: 8px;
      padding: 8px 14px; color: #fff; cursor: pointer;
      font-family: 'Barlow Condensed', sans-serif;
      font-size: 0.95rem; font-weight: 700; letter-spacing: 0.5px;
      transition: background 0.2s;
    }
    #pd-chat-send:hover { background: #e0122e; }
    #pd-chat-send:disabled { opacity: 0.5; cursor: not-allowed; }

    @media (max-width: 420px) {
      #pd-chat-panel { width: calc(100vw - 16px); right: 8px; bottom: 80px; }
      #pd-chat-btn { bottom: 16px; right: 16px; }
    }
  `;
  document.head.appendChild(style);

  const widget = document.createElement('div');
  widget.id = 'pd-chat-widget';
  widget.innerHTML = `
    <button id="pd-chat-btn" title="Ask about today's picks">💬</button>
    <div id="pd-chat-panel" class="hidden">
      <div id="pd-chat-header">
        <div>
          <div id="pd-chat-header-title">🏒 Picks Assistant</div>
          <div id="pd-chat-header-sub">Ask about today's bets</div>
        </div>
        <button id="pd-chat-close">✕</button>
      </div>
      <div id="pd-chat-messages"></div>
      <div id="pd-chat-input-row">
        <input id="pd-chat-input" type="text" placeholder="Ask about today's picks…" maxlength="400" autocomplete="off">
        <button id="pd-chat-send">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(widget);

  const panel    = document.getElementById('pd-chat-panel');
  const btn      = document.getElementById('pd-chat-btn');
  const closeBtn = document.getElementById('pd-chat-close');
  const messages = document.getElementById('pd-chat-messages');
  const input    = document.getElementById('pd-chat-input');
  const sendBtn  = document.getElementById('pd-chat-send');

  let history = [];
  let open = false;

  function togglePanel() {
    open = !open;
    panel.classList.toggle('hidden', !open);
    if (open) {
      input.focus();
      if (messages.children.length === 0) {
        addMessage('bot', "Hi! I can answer questions about today's NHL and NBA picks. What would you like to know?");
      }
    }
  }

  function addMessage(role, text) {
    const el = document.createElement('div');
    el.className = `pd-msg pd-msg-${role}`;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function showTyping() {
    const el = document.createElement('div');
    el.className = 'pd-typing';
    el.id = 'pd-typing-indicator';
    el.innerHTML = '<span></span><span></span><span></span>';
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('pd-typing-indicator');
    if (el) el.remove();
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    sendBtn.disabled = true;
    input.disabled = true;

    addMessage('user', text);
    showTyping();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();
      hideTyping();
      const reply = data.reply || 'Sorry, I could not get a response.';
      addMessage('bot', reply);
      history.push({ role: 'user', content: text });
      history.push({ role: 'assistant', content: reply });
      if (history.length > 12) history = history.slice(-12);
    } catch (e) {
      hideTyping();
      addMessage('bot', 'Connection error. Please try again.');
    }

    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }

  btn.addEventListener('click', togglePanel);
  closeBtn.addEventListener('click', togglePanel);
  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
})();
