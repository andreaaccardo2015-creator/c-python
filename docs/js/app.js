(function () {
  const I = window.CpyI18n;
  if (!I) return;

  const KEY_ACCOUNTS = "cpy.accounts.v1";
  const KEY_SESSION = "cpy.session.v1";
  const USER_RE = /^[A-Za-z0-9_]{3,20}$/;
  const GH_RE = /^[A-Za-z0-9-]{1,39}$/;

  function t(key) {
    return I.t(key);
  }

  function readJson(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || "") || fallback;
    } catch (e) {
      return fallback;
    }
  }

  function accounts() {
    return readJson(KEY_ACCOUNTS, {});
  }

  function saveAccounts(map) {
    localStorage.setItem(KEY_ACCOUNTS, JSON.stringify(map));
  }

  function session() {
    return readJson(KEY_SESSION, null);
  }

  function setSession(user) {
    if (user) localStorage.setItem(KEY_SESSION, JSON.stringify(user));
    else localStorage.removeItem(KEY_SESSION);
    document.dispatchEvent(new CustomEvent("cpy-auth"));
  }

  function bytesToHex(buf) {
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function hashPass(password, salt) {
    const data = new TextEncoder().encode(salt + "\n" + password);
    return bytesToHex(await crypto.subtle.digest("SHA-256", data));
  }

  function randomSalt() {
    const a = new Uint8Array(16);
    crypto.getRandomValues(a);
    return bytesToHex(a);
  }

  let settingsTab = "page";
  let pendingGithub = null;
  let authError = "";
  let settingsOpen = false;
  let lastGhUser = "";

  function gearSvg() {
    return '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.2 7.2 0 0 0-1.63-.94l-.36-2.54A.5.5 0 0 0 13.9 2h-3.8a.5.5 0 0 0-.5.42l-.36 2.54c-.58.22-1.13.54-1.63.94l-2.39-.96a.5.5 0 0 0-.6.22L2.8 8.48a.5.5 0 0 0 .12.64L4.95 10.7c-.04.31-.06.63-.06.94s.02.63.06.94L2.92 14.16a.5.5 0 0 0-.12.64l1.92 3.32c.14.24.43.34.7.22l2.39-.96c.5.4 1.05.72 1.63.94l.36 2.54c.05.24.26.42.5.42h3.8c.24 0 .45-.18.5-.42l.36-2.54c.58-.22 1.13-.54 1.63-.94l2.39.96c.27.12.56.02.7-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.03-1.58ZM12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7Z"/></svg>';
  }

  function mountChrome() {
    const brand = document.querySelector(".sitebar .brand");
    if (brand && !brand.parentElement.classList.contains("brand-cluster")) {
      const wrap = document.createElement("div");
      wrap.className = "brand-cluster";
      brand.replaceWith(wrap);
      wrap.appendChild(brand);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "settings-btn";
      btn.setAttribute("data-i18n-aria", "settings.open");
      btn.innerHTML = gearSvg();
      btn.addEventListener("click", () => openSettings());
      wrap.appendChild(btn);
    }
    if (!document.getElementById("cpy-settings")) {
      const box = document.createElement("div");
      box.id = "cpy-settings";
      box.className = "settings-overlay";
      box.hidden = true;
      document.body.appendChild(box);
      box.addEventListener("click", (e) => {
        if (e.target === box) closeSettings();
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && settingsOpen) closeSettings();
    });
  }

  function openSettings(tab) {
    settingsTab = tab || settingsTab || "page";
    settingsOpen = true;
    authError = "";
    pendingGithub = null;
    renderSettings();
    const box = document.getElementById("cpy-settings");
    if (box) box.hidden = false;
  }

  function closeSettings() {
    settingsOpen = false;
    const box = document.getElementById("cpy-settings");
    if (box) box.hidden = true;
  }

  function userChipHtml(user) {
    if (!user) return "";
    const name = user.github && user.github.login ? user.github.login : user.username;
    const img = user.github && user.github.avatar
      ? `<img src="${user.github.avatar}" alt="">`
      : `<span class="chip-letter">${(name || "?").slice(0, 1).toUpperCase()}</span>`;
    return `<div class="user-chip">${img}<span>${escapeHtml(name)}</span></div>`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderSettings() {
    const box = document.getElementById("cpy-settings");
    if (!box) return;
    const prefs = I.readPrefs();
    const detected = I.detectSystemLang();
    const user = session();
    const err = authError ? `<p class="auth-err">${escapeHtml(authError)}</p>` : "";
    const detectLine = detected.ok
      ? `${t("settings.detected")} <strong>${escapeHtml(detected.raw || detected.lang)}</strong>`
      : t("settings.detected.fail");

    let account = "";
    if (user) {
      const gh = user.github
        ? `<p class="muted">${t("auth.github.linked")}: <strong>@${escapeHtml(user.github.login)}</strong></p>
           <button type="button" class="btn btn-ghost" data-act="unlink-gh">${t("auth.github.unlink")}</button>`
        : `<div class="auth-block">
             <label>${t("auth.github.user")}<input id="gh-user" autocomplete="username" value="${escapeHtml(lastGhUser)}"></label>
             <button type="button" class="btn btn-ghost" data-act="lookup-gh">${t("auth.github.go")}</button>
           </div>`;
      account = `
        <p>${t("auth.hello")} <strong>${escapeHtml(user.username)}</strong></p>
        ${userChipHtml(user)}
        ${gh}
        ${pendingGithubCard()}
        <button type="button" class="btn btn-primary" data-act="logout">${t("auth.logout")}</button>`;
    } else {
      account = `
        <p class="muted">${t("auth.local.note")}</p>
        <div class="auth-grid">
          <form data-act="login" class="auth-form">
            <h3>${t("auth.login")}</h3>
            <label>${t("auth.user")}<input name="user" autocomplete="username" required></label>
            <label>${t("auth.pass")}<input name="pass" type="password" autocomplete="current-password" required></label>
            <button class="btn btn-primary" type="submit">${t("auth.login")}</button>
          </form>
          <form data-act="signup" class="auth-form">
            <h3>${t("auth.signup")}</h3>
            <label>${t("auth.user")}<input name="user" autocomplete="username" required></label>
            <label>${t("auth.pass")}<input name="pass" type="password" autocomplete="new-password" required></label>
            <label>${t("auth.pass2")}<input name="pass2" type="password" autocomplete="new-password" required></label>
            <button class="btn btn-ghost" type="submit">${t("auth.signup")}</button>
          </form>
        </div>
        <div class="auth-form">
          <h3>${t("auth.github")}</h3>
          <label>${t("auth.github.user")}<input id="gh-user" autocomplete="username" value="${escapeHtml(lastGhUser)}"></label>
          <button type="button" class="btn btn-win" data-act="lookup-gh">${t("auth.github.go")}</button>
          ${pendingGithubCard()}
        </div>`;
    }

    box.innerHTML = `
      <div class="settings-panel" role="dialog" aria-modal="true" aria-labelledby="set-title">
        <div class="settings-head">
          <h2 id="set-title">${t("settings.title")}</h2>
          <button type="button" class="settings-x" data-act="close" aria-label="${t("settings.close")}">×</button>
        </div>
        <div class="settings-tabs">
          <button type="button" class="${settingsTab === "page" ? "active" : ""}" data-act="tab-page">${t("settings.tab.page")}</button>
          <button type="button" class="${settingsTab === "account" ? "active" : ""}" data-act="tab-account">${t("settings.tab.account")}</button>
        </div>
        <div class="settings-body" ${settingsTab === "page" ? "" : "hidden"}>
          <label>${t("settings.lang")}
            <select id="set-lang">
              <option value="auto" ${(!prefs.langMode || prefs.langMode === "auto") ? "selected" : ""}>${t("settings.lang.auto")}</option>
              <option value="it" ${prefs.langMode === "it" ? "selected" : ""}>${t("settings.lang.it")}</option>
              <option value="en" ${prefs.langMode === "en" ? "selected" : ""}>${t("settings.lang.en")}</option>
            </select>
          </label>
          <p class="muted">${detectLine}</p>
          <p class="note">${t("settings.lang.note")}</p>
          <label>${t("settings.theme")}
            <select id="set-theme">
              <option value="dark" ${prefs.theme !== "light" ? "selected" : ""}>${t("settings.theme.dark")}</option>
              <option value="light" ${prefs.theme === "light" ? "selected" : ""}>${t("settings.theme.light")}</option>
            </select>
          </label>
        </div>
        <div class="settings-body" ${settingsTab === "account" ? "" : "hidden"}>
          ${err}
          ${account}
        </div>
      </div>`;

    box.querySelector("#set-lang")?.addEventListener("change", (e) => {
      I.writePrefs({ langMode: e.target.value });
      refresh();
      renderSettings();
    });
    box.querySelector("#set-theme")?.addEventListener("change", (e) => {
      I.writePrefs({ theme: e.target.value });
      I.applyChrome();
    });
    box.querySelectorAll("[data-act]").forEach((el) => {
      const act = el.getAttribute("data-act");
      if (el.tagName === "FORM") {
        el.addEventListener("submit", (ev) => {
          ev.preventDefault();
          handleForm(act, el);
        });
      } else {
        el.addEventListener("click", () => handleAct(act));
      }
    });
  }

  function pendingGithubCard() {
    if (!pendingGithub) return "";
    return `<div class="gh-card">
      <img src="${pendingGithub.avatar}" alt="">
      <div>
        <strong>${escapeHtml(pendingGithub.name || pendingGithub.login)}</strong>
        <div class="muted">@${escapeHtml(pendingGithub.login)}</div>
      </div>
      <button type="button" class="btn btn-primary" data-act="confirm-gh">${t("auth.github.confirm")}</button>
    </div>`;
  }

  async function handleForm(act, form) {
    authError = "";
    const user = (form.user.value || "").trim();
    const pass = form.pass.value || "";
    if (act === "signup") {
      const pass2 = form.pass2.value || "";
      if (!USER_RE.test(user)) return fail("auth.err.user");
      if (pass.length < 6) return fail("auth.err.pass");
      if (pass !== pass2) return fail("auth.err.match");
      const map = accounts();
      const key = user.toLowerCase();
      if (map[key]) return fail("auth.err.exists");
      const salt = randomSalt();
      map[key] = { username: user, salt, hash: await hashPass(pass, salt), github: null };
      saveAccounts(map);
      setSession({ kind: "local", username: user, github: null });
      settingsTab = "account";
      renderSettings();
      return;
    }
    if (act === "login") {
      const map = accounts();
      const rec = map[user.toLowerCase()];
      if (!rec) return fail("auth.err.login");
      const hash = await hashPass(pass, rec.salt);
      if (hash !== rec.hash) return fail("auth.err.login");
      setSession({ kind: "local", username: rec.username, github: rec.github || null });
      renderSettings();
    }
  }

  function fail(key) {
    authError = t(key);
    renderSettings();
  }

  async function handleAct(act) {
    if (act === "close") return closeSettings();
    if (act === "tab-page") {
      settingsTab = "page";
      renderSettings();
      return;
    }
    if (act === "tab-account") {
      settingsTab = "account";
      renderSettings();
      return;
    }
    if (act === "logout") {
      setSession(null);
      pendingGithub = null;
      renderSettings();
      return;
    }
    if (act === "unlink-gh") {
      const cur = session();
      if (!cur) return;
      if (cur.kind === "github") {
        setSession(null);
      } else {
        const map = accounts();
        const rec = map[cur.username.toLowerCase()];
        if (rec) {
          rec.github = null;
          saveAccounts(map);
        }
        setSession({ kind: "local", username: cur.username, github: null });
      }
      renderSettings();
      return;
    }
    if (act === "lookup-gh") {
      const input = document.getElementById("gh-user");
      const login = (input && input.value || "").trim().replace(/^@/, "");
      lastGhUser = login;
      if (!login || !GH_RE.test(login)) return fail("auth.err.needuser");
      authError = "";
      try {
        const res = await fetch("https://api.github.com/users/" + encodeURIComponent(login));
        if (res.status === 404) return fail("auth.err.gh");
        if (!res.ok) return fail("auth.err.net");
        const data = await res.json();
        pendingGithub = {
          login: data.login,
          id: data.id,
          avatar: data.avatar_url,
          name: data.name || data.login,
        };
        renderSettings();
      } catch (e) {
        fail("auth.err.net");
      }
      return;
    }
    if (act === "confirm-gh") {
      if (!pendingGithub) return;
      const gh = pendingGithub;
      pendingGithub = null;
      const cur = session();
      if (cur && cur.kind === "local") {
        const map = accounts();
        const rec = map[cur.username.toLowerCase()];
        if (rec) {
          rec.github = gh;
          saveAccounts(map);
        }
        setSession({ kind: "local", username: cur.username, github: gh });
      } else {
        setSession({ kind: "github", username: gh.login, github: gh });
      }
      renderSettings();
    }
  }

  function refreshFeedback() {
    const lock = document.getElementById("fb-lock");
    const form = document.getElementById("form");
    const extra = document.getElementById("fb-extra");
    const user = session();
    if (!lock || !form) return;
    const on = !!user;
    lock.hidden = on;
    form.hidden = !on;
    if (extra) extra.hidden = !on;
    form.querySelectorAll("input, select, textarea, button").forEach((el) => {
      el.disabled = !on;
    });
  }

  function bindFeedback() {
    const form = document.getElementById("form");
    if (!form) return;
    const openBtn = document.querySelector("[data-open-settings]");
    if (openBtn) openBtn.addEventListener("click", () => openSettings("account"));
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const user = session();
      if (!user) {
        openSettings("account");
        return;
      }
      const tipo = form.tipo.value;
      const titolo = form.titolo.value.trim();
      const os = form.os.value;
      const nome = form.nome.value.trim();
      const msg = form.msg.value.trim();
      const body = [
        msg,
        "",
        "---",
        "Inviato da: pagina feedback C Python",
        "Tipo: " + tipo,
        os ? "Sistema: " + os : null,
        nome ? "Nome: " + nome : null,
        "Account sito: " + user.username,
        user.github ? "GitHub: @" + user.github.login : "GitHub: non collegato",
        "Versione sito: 0.3.5",
      ].filter(Boolean).join("\n");
      const url = "https://github.com/andreaaccardo2015-creator/c-python/issues/new?title=" +
        encodeURIComponent("[" + tipo + "] " + titolo) +
        "&body=" + encodeURIComponent(body);
      window.open(url, "_blank", "noopener");
      document.getElementById("ok")?.classList.add("show");
    });
  }

  function refresh() {
    I.applyI18n();
    const btn = document.querySelector(".settings-btn");
    if (btn) btn.setAttribute("aria-label", t("settings.open"));
    refreshFeedback();
    if (settingsOpen) renderSettings();
  }

  document.addEventListener("cpy-auth", refreshFeedback);

  mountChrome();
  I.applyI18n();
  bindFeedback();
  refreshFeedback();
  window.CpyApp = { openSettings, session };
})();
