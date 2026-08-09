// Wires the bar UI to Python via pywebview. All calls go through
// `pywebview.api` - no HTTP server involved.

const chat = document.getElementById("chat");
const promptInput = document.getElementById("prompt-input");
const sendButton = document.getElementById("send-button");
const modelSelect = document.getElementById("model-select");
const keyButton = document.getElementById("key-button");

let busy = false;          // true while the AI is still typing
let currentBubble = null;  // the bubble receiving the streamed reply
let status = null;         // { models: [...], has_key: bool } from Python
let initialized = false;

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

// The bar shows exactly one message: the latest one. The window height
// wraps around it (see scheduleHeightSync).
function showMessage(role, text) {
  chat.innerHTML = "";
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  if (text) {
    bubble.textContent = text;
  }
  chat.appendChild(bubble);
  scheduleHeightSync();
  return bubble;
}

function setBusy(value) {
  busy = value;
  promptInput.disabled = value;
  sendButton.disabled = value;
  promptInput.focus();
}

// ---------------------------------------------------------------------------
// Height sync: ask Python to size the window to the current message.
// Debounced, because streaming appends a token at a time.
// ---------------------------------------------------------------------------

let heightTimer = null;

function syncHeight() {
  heightTimer = null;
  const bubble = chat.querySelector(".message, .hint");
  const contentHeight = bubble ? bubble.offsetHeight : 0;
  const desired =
    document.querySelector(".topbar").offsetHeight +
    contentHeight +
    document.querySelector(".inputbar").offsetHeight;
  pywebview.api.resize_window(desired);
}

function scheduleHeightSync() {
  if (heightTimer) clearTimeout(heightTimer);
  heightTimer = setTimeout(syncHeight, 60);
}

// ---------------------------------------------------------------------------
// Key prompt and hints
// ---------------------------------------------------------------------------

function setupKeyPrompt() {
  chat.innerHTML = "";

  const wrapper = document.createElement("div");
  wrapper.className = "message hint";
  wrapper.innerHTML = `
    <p>Paste a free Gemini API key and hit Save.</p>
    <input id="key-input" type="password" placeholder="API key..." autocomplete="off">
    <button id="key-save">Save</button>
  `;

  const input = wrapper.querySelector("#key-input");
  const save = wrapper.querySelector("#key-save");

  const finish = () => {
    const value = input.value.trim();
    if (value) {
      pywebview.api.save_api_key(value);
      status.has_key = true;
      setupHint();
    }
  };

  save.addEventListener("click", finish);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") finish();
  });

  chat.appendChild(wrapper);
  scheduleHeightSync();
  input.focus();
}

function setupHint() {
  showMessage(
    "hint",
    "All set. Type below and press Enter - answers stream into this bar. " +
    "The window is hidden from screen captures."
  );
}

function setupMissingKeyHint() {
  showMessage(
    "hint",
    'No Gemini key yet - click "API Key" in the top bar to add one.'
  );
}

// ---------------------------------------------------------------------------
// Sending messages
// ---------------------------------------------------------------------------

function send() {
  if (busy) return;

  const text = promptInput.value.trim();
  if (!text) return;

  promptInput.value = "";
  // One message at a time: this bubble gets replaced by the streaming
  // reply, which grows the window to wrap it.
  currentBubble = showMessage("assistant");
  currentBubble.classList.add("cursor");

  setBusy(true);
  pywebview.api.send_message(text, modelSelect.value);
}

sendButton.addEventListener("click", send);
promptInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") send();
});

document.getElementById("close-button").addEventListener("click", () => {
  pywebview.api.quit();
});

// ---------------------------------------------------------------------------
// Callbacks invoked by Python (via window.evaluate_js)
// ---------------------------------------------------------------------------

window.on_token = (token) => {
  if (currentBubble) {
    currentBubble.textContent += token;
    scheduleHeightSync();
  }
};

window.on_error = (message) => {
  currentBubble = null;
  showMessage("error", message);
};

window.on_done = () => {
  currentBubble = null;
  setBusy(false);
  scheduleHeightSync();
};

// ---------------------------------------------------------------------------
// Startup
// ---------------------------------------------------------------------------

keyButton.addEventListener("click", setupKeyPrompt);

async function init() {
  if (initialized) return;
  if (!window.pywebview || !pywebview.api) {
    showMessage(
      "error",
      "pywebview is not available - open this page from main.py instead."
    );
    return;
  }
  initialized = true;

  status = await pywebview.api.get_status();

  modelSelect.innerHTML = "";
  for (const model of status.models) {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    modelSelect.appendChild(option);
  }
  modelSelect.value = status.models[0];

  if (!status.has_key) {
    setupKeyPrompt();
  } else {
    setupHint();
  }
}

// pywebview fires this once the JS bridge is ready.
window.addEventListener("pywebviewready", init);
