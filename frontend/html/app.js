// Kairos frontend: plain JavaScript, no build step. All API calls go through Nginx at /api.
"use strict";

const TOKEN_KEY = "kairos-token";
const $ = (id) => document.getElementById(id);
let hobbies = new Map(); // hobby id -> hobby, for showing names on session cards

const token = () => sessionStorage.getItem(TOKEN_KEY);

function show(message, isError = false) {
  $("message").textContent = message;
  $("message").className = isError ? "error" : "";
}

// Creates an element. textContent (never innerHTML) keeps user text as plain text, not HTML.
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

// Calls the API with the login token. Throws an Error with the service's message on failure.
async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  if (token()) headers.Authorization = `Bearer ${token()}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token()) logout();
    const detail = data?.detail;
    // 422 validation errors are a list of problems; other errors are a plain string.
    const text = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new Error(text || `Something went wrong (${response.status})`);
  }
  return data;
}

// Wraps a handler: stops the browser's default form submit and shows any error on the page.
function guarded(handler) {
  return async (event) => {
    event?.preventDefault();
    try {
      await handler(event);
    } catch (error) {
      show(error.message, true);
    }
  };
}

const formData = (form) => Object.fromEntries(new FormData(form));
const hobbyLabel = (hobby) => (hobby ? `${hobby.emoji ?? ""} ${hobby.name}`.trim() : "A hobby");

function showView(loggedIn) {
  $("auth-view").hidden = loggedIn;
  $("app-view").hidden = !loggedIn;
  $("whoami").hidden = !loggedIn;
}

function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
  showView(false);
}

async function loadHobbies() {
  const list = await api("/hobbies");
  hobbies = new Map(list.map((hobby) => [hobby.id, hobby]));
  $("hobby-list").replaceChildren(...list.map((hobby) => el("li", hobbyLabel(hobby))));
  document.querySelector("#park-form select").replaceChildren(
    ...list.map((hobby) => {
      const option = el("option", hobbyLabel(hobby));
      option.value = hobby.id;
      return option;
    }),
  );
}

function sessionCard(session) {
  const card = el("li");
  const resume = el("button", "Resume");
  resume.addEventListener(
    "click",
    guarded(async () => {
      await api(`/sessions/${session.id}/resume`, { method: "POST" });
      show(`Welcome back. Your next tiny step: ${session.next_tiny_step}`);
      await loadParked();
    }),
  );
  card.append(
    el("p", hobbyLabel(hobbies.get(session.hobby_id)), "hobby"),
    el("p", session.next_tiny_step, "next-step"),
    el("p", `Where you stopped: ${session.where_i_stopped}`, "muted"),
    el("p", `Parked ${new Date(session.parked_at).toLocaleString()}`, "muted small"),
    resume,
  );
  return card;
}

async function loadParked() {
  const sessions = await api("/sessions?parked=true");
  $("no-parked").hidden = sessions.length > 0;
  $("parked-list").replaceChildren(...sessions.map(sessionCard));
}

async function start() {
  if (!token()) return showView(false);
  const me = await api("/me"); // also checks that the saved token is still valid
  $("user-email").textContent = me.email;
  showView(true);
  await loadHobbies();
  await loadParked();
}

$("auth-form").addEventListener(
  "submit",
  guarded(async (event) => {
    const credentials = formData(event.target);
    if (event.submitter.value === "register") {
      await api("/users", { method: "POST", body: credentials });
    }
    const { access_token } = await api("/login", { method: "POST", body: credentials });
    sessionStorage.setItem(TOKEN_KEY, access_token);
    event.target.reset();
    show("");
    await start();
  }),
);

$("hobby-form").addEventListener(
  "submit",
  guarded(async (event) => {
    const { name, emoji } = formData(event.target);
    await api("/hobbies", { method: "POST", body: { name, emoji: emoji || null } });
    event.target.reset();
    await loadHobbies();
  }),
);

$("park-form").addEventListener(
  "submit",
  guarded(async (event) => {
    const data = formData(event.target);
    await api("/sessions", { method: "POST", body: { ...data, hobby_id: Number(data.hobby_id) } });
    event.target.reset();
    show("Parked. It will be here when you're ready.");
    await loadParked();
  }),
);

$("logout").addEventListener("click", guarded(logout));

guarded(start)();
