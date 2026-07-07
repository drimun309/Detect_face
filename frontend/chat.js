/* detect_face_chat widget - vanilla JS, no deps */
(() => {
  "use strict";

  // auto-detect backend: если виджет открыт на :9876 (наш standalone),
  // ходим на тот же origin. Если встроен в detect_face (:8081), ходим
  // на http://localhost:9876
  const API_BASE = (location.port === "9876")
    ? ""  // same-origin
    : "http://localhost:9876";  // detect_face frontend -> chat backend

  let history = [];
  let busy = false;

  const el = {
    root: null,
    log: null,
    input: null,
    send: null,
    toggle: null,
    badge: null,
  };

  function make(tag, props = {}, ...kids) {
    const n = document.createElement(tag);
    for (const k in props) {
      if (k === "class") n.className = props[k];
      else if (k === "html") n.innerHTML = props[k];
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), props[k]);
      else n.setAttribute(k, props[k]);
    }
    for (const kid of kids) {
      if (kid == null) continue;
      n.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
    }
    return n;
  }

  function renderMsg(role, text) {
    const wrap = make("div", { class: "msg msg-" + role });
    const bubble = make("div", { class: "bubble" });
    bubble.textContent = text;
    const time = make("div", { class: "ts" });
    const d = new Date();
    time.textContent = d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    wrap.appendChild(bubble);
    wrap.appendChild(time);
    return wrap;
  }

  function appendMsg(role, text) {
    const m = renderMsg(role, text);
    el.log.appendChild(m);
    el.log.scrollTop = el.log.scrollHeight;
  }

  function setBusy(b) {
    busy = b;
    el.send.disabled = b;
    el.input.disabled = b;
    el.send.textContent = b ? "..." : "Send";
  }

  async function send() {
    if (busy) return;
    const msg = el.input.value.trim();
    if (!msg) return;
    el.input.value = "";
    history.push({ role: "user", text: msg });
    appendMsg("user", msg);
    setBusy(true);
    el.toggle.setAttribute("data-busy", "1");
    try {
      const r = await fetch(API_BASE + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const data = await r.json();
      if (!r.ok) {
        appendMsg("error", "Error: " + (data.error || r.statusText));
        el.toggle.removeAttribute("data-busy");
        return;
      }
      history.push({ role: "assistant", text: data.reply });
      appendMsg("assistant", data.reply);
    } catch (e) {
      appendMsg("error", "Network: " + e.message);
    } finally {
      setBusy(false);
      el.toggle.removeAttribute("data-busy");
      el.input.focus();
    }
  }

  function buildPanel() {
    el.root = make("div", { id: "df-chat-root" });
    el.root.innerHTML = `
      <style id="df-chat-style">
#df-chat-root{position:fixed;bottom:20px;right:20px;z-index:99999;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px}
#df-chat-toggle{width:56px;height:56px;border-radius:50%;background:#2563eb;color:#fff;border:none;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);font-size:24px;display:flex;align-items:center;justify-content:center;transition:transform .15s}
#df-chat-toggle:hover{transform:scale(1.05)}
#df-chat-toggle[data-open="1"]{background:#1e40af}
#df-chat-toggle[data-busy="1"]::after{content:"";position:absolute;width:12px;height:12px;background:#fbbf24;border-radius:50%;top:6px;right:6px;border:2px solid #2563eb;animation:df-chat-pulse 1s infinite}
@keyframes df-chat-pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.3);opacity:.6}}
#df-chat-panel{position:absolute;bottom:70px;right:0;width:380px;height:540px;max-height:80vh;background:#1e293b;color:#e2e8f0;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.35);display:none;flex-direction:column;overflow:hidden;border:1px solid #334155}
#df-chat-panel[data-open="1"]{display:flex}
#df-chat-header{padding:12px 16px;background:#0f172a;border-bottom:1px solid #334155;display:flex;align-items:center;gap:10px}
#df-chat-header .dot{width:8px;height:8px;border-radius:50%;background:#22c55e}
#df-chat-header .title{font-weight:600;flex:1}
#df-chat-header .sub{font-size:12px;color:#94a3b8}
#df-chat-log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:#0f172a}
.msg{display:flex;flex-direction:column;max-width:85%}
.msg-user{align-self:flex-end}
.msg-assistant{align-self:flex-start}
.msg-error{align-self:center}
.bubble{padding:10px 14px;border-radius:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}
.msg-user .bubble{background:#2563eb;color:#fff;border-bottom-right-radius:4px}
.msg-assistant .bubble{background:#334155;color:#e2e8f0;border-bottom-left-radius:4px}
.msg-error .bubble{background:#7f1d1d;color:#fecaca}
.ts{font-size:11px;color:#64748b;margin-top:2px;padding:0 4px}
.msg-user .ts{align-self:flex-end}
.msg-assistant .ts{align-self:flex-start}
#df-chat-form{padding:10px;border-top:1px solid #334155;background:#1e293b;display:flex;gap:8px}
#df-chat-input{flex:1;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:10px 12px;border-radius:8px;font-size:14px;outline:none;font-family:inherit;resize:none;max-height:120px}
#df-chat-input:focus{border-color:#3b82f6}
#df-chat-input:disabled{opacity:.5}
#df-chat-send{background:#2563eb;color:#fff;border:none;padding:0 16px;border-radius:8px;font-weight:600;cursor:pointer;font-size:14px}
#df-chat-send:hover{background:#1d4ed8}
#df-chat-send:disabled{background:#475569;cursor:not-allowed}
      </style>
    `;
    el.toggle = make("button", {
      id: "df-chat-toggle",
      title: "AI assistant",
      onclick: (e) => {
        e.stopPropagation();
        const open = el.panel.getAttribute("data-open") === "1";
        if (open) el.panel.removeAttribute("data-open");
        else {
          el.panel.setAttribute("data-open", "1");
          el.input.focus();
        }
        el.toggle.setAttribute("data-open", open ? "0" : "1");
      },
    });
    el.toggle.textContent = "AI";

    el.panel = make("div", { id: "df-chat-panel" });
    const header = make("div", { id: "df-chat-header" },
      make("div", { class: "dot" }),
      make("div", { class: "title" }, "AI-ассистент цеха"),
      make("div", { class: "sub" }, "Local · "),
    );
    el.log = make("div", { id: "df-chat-log" });
    el.log.appendChild(make("div", { class: "msg msg-assistant" },
      make("div", { class: "bubble" },
        "Привет! Я AI-ассистент. Спрашивай что угодно про отчёты, ROI-зоны, статистику.")
    ));
    el.input = make("textarea", {
      id: "df-chat-input",
      placeholder: "Спросить что-нибудь... (Shift+Enter = новая строка)",
      rows: "2",
      onkeydown: (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          send();
        }
      },
    });
    el.send = make("button", { id: "df-chat-send", onclick: send }, "Send");

    const form = make("div", { id: "df-chat-form" }, el.input, el.send);
    el.panel.appendChild(header);
    el.panel.appendChild(el.log);
    el.panel.appendChild(form);

    el.root.appendChild(el.panel);
    el.root.appendChild(el.toggle);

    document.body.appendChild(el.root);
  }

  function init() {
    if (document.getElementById("df-chat-root")) return;
    buildPanel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();