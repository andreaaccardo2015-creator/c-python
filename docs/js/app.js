(function () {
  const I = window.CpyI18n;
  if (!I) return;

  const KEY_ACCOUNTS = "cpy.accounts.v1";
  const KEY_SESSION = "cpy.session.v1";
  const KEY_GH_WAIT = "cpy.gh.wait.v1";
  const USER_RE = /^[A-Za-z0-9_]{3,20}$/;
  const GH_REPO = "andreaaccardo2015-creator/c-python";
  const GH_WAIT_MS = 180000;

  function t(key) {
    return I.t(key);
  }

  function readJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (raw == null || raw === "") return fallback;
      const v = JSON.parse(raw);
      return v == null ? fallback : v;
    } catch (e) {
      return fallback;
    }
  }

  function accounts() {
    const map = readJson(KEY_ACCOUNTS, {});
    return map && typeof map === "object" && !Array.isArray(map) ? map : {};
  }

  function saveAccounts(map) {
    try {
      localStorage.setItem(KEY_ACCOUNTS, JSON.stringify(map));
    } catch (e) {
      throw e;
    }
  }

  function session() {
    const s = readJson(KEY_SESSION, null);
    return s && typeof s === "object" ? s : null;
  }

  function setSession(user) {
    try {
      if (user) localStorage.setItem(KEY_SESSION, JSON.stringify(user));
      else localStorage.removeItem(KEY_SESSION);
    } catch (e) {
      authError = t("auth.err.store");
    }
    document.dispatchEvent(new CustomEvent("cpy-auth"));
  }

  function bytesToHex(buf) {
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function hashPass(password, salt) {
    if (!window.crypto || !crypto.subtle) throw new Error("subtle");
    const data = new TextEncoder().encode(salt + "\n" + password);
    return bytesToHex(await crypto.subtle.digest("SHA-256", data));
  }

  function randomSalt() {
    const a = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(a);
    return bytesToHex(a);
  }

  let settingsTab = "page";
  let authError = "";
  let settingsOpen = false;
  let ghWait = null;
  let ghTimer = null;
  let ghPollBusy = false;

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
      ? `<img src="${escapeHtml(user.github.avatar)}" alt="">`
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
        : githubConnectHtml();
      account = `
        <p>${t("auth.hello")} <strong>${escapeHtml(user.username)}</strong></p>
        ${userChipHtml(user)}
        ${gh}
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
          ${githubConnectHtml()}
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

  function githubConnectHtml() {
    if (ghWait) {
      return `<p>${t("auth.github.wait")}</p>
        <a class="btn btn-win" href="${escapeHtml(ghWait.url)}" target="_blank" rel="noopener">${t("auth.github.open")}</a>
        <button type="button" class="btn btn-ghost" data-act="cancel-gh">${t("auth.github.cancel")}</button>`;
    }
    return `<p class="muted">${t("auth.github.note")}</p>
      <button type="button" class="btn btn-win" data-act="start-gh">${t("auth.github.open")}</button>`;
  }

  function githubIssueUrl(nonce) {
    const title = "[cpy-verify] " + nonce;
    const body = "Non cambiare il titolo. Pubblica questa issue: GitHub conferma cosi' che sei tu. Si chiude da sola.\n\nDo not edit the title. Submit this issue so GitHub can confirm it is you. It closes by itself.";
    return "https://github.com/" + GH_REPO + "/issues/new?title=" +
      encodeURIComponent(title) + "&body=" + encodeURIComponent(body);
  }

  function stopGithubWait() {
    if (ghTimer) clearInterval(ghTimer);
    ghTimer = null;
    ghWait = null;
    try { sessionStorage.removeItem(KEY_GH_WAIT); } catch (e) { /* ignore */ }
  }

  function applyGithubIdentity(gh) {
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
  }

  async function pollGithubWait() {
    if (ghPollBusy || !ghWait) return;
    if (Date.now() - ghWait.startedAt > GH_WAIT_MS) {
      stopGithubWait();
      authError = t("auth.github.timeout");
      openSettings("account");
      return;
    }
    ghPollBusy = true;
    try {
      const res = await fetch(
        "https://api.github.com/repos/" + GH_REPO + "/issues?state=all&sort=created&direction=desc&per_page=50",
        { headers: { Accept: "application/vnd.github+json" } }
      );
      if (res.status === 403 || res.status === 429) {
        authError = t("auth.err.net");
        if (settingsOpen) renderSettings();
        return;
      }
      if (!res.ok) return;
      const issues = await res.json();
      if (!Array.isArray(issues) || !ghWait) return;
      const want = "[cpy-verify] " + ghWait.nonce;
      const hit = issues.find((issue) =>
        issue && !issue.pull_request && issue.title === want && issue.user && issue.user.login
      );
      if (!hit) return;
      const created = Date.parse(hit.created_at);
      if (!created || created < ghWait.startedAt - 30000) return;
      const profile = await fetch(
        "https://api.github.com/users/" + encodeURIComponent(hit.user.login),
        { headers: { Accept: "application/vnd.github+json" } }
      );
      const data = profile.ok ? await profile.json() : hit.user;
      const gh = {
        login: data.login || hit.user.login,
        id: data.id || hit.user.id,
        avatar: data.avatar_url || hit.user.avatar_url,
        name: data.name || data.login || hit.user.login,
      };
      stopGithubWait();
      authError = "";
      applyGithubIdentity(gh);
      settingsTab = "account";
      openSettings("account");
    } catch (e) {
      /* keep waiting */
    } finally {
      ghPollBusy = false;
    }
  }

  function startGithubWait() {
    authError = "";
    try {
      const nonce = randomSalt().slice(0, 24);
      const url = githubIssueUrl(nonce);
      ghWait = { nonce, url, startedAt: Date.now() };
      try { sessionStorage.setItem(KEY_GH_WAIT, JSON.stringify(ghWait)); } catch (e) { /* ignore */ }
      settingsTab = "account";
      window.open(url, "_blank", "noopener");
      if (ghTimer) clearInterval(ghTimer);
      ghTimer = setInterval(pollGithubWait, 5000);
      pollGithubWait();
      renderSettings();
    } catch (e) {
      fail("auth.err.store");
    }
  }

  function resumeGithubWait() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(KEY_GH_WAIT) || "null");
      if (!saved || !saved.nonce || Date.now() - saved.startedAt > GH_WAIT_MS) {
        sessionStorage.removeItem(KEY_GH_WAIT);
        return;
      }
      ghWait = saved;
      if (ghTimer) clearInterval(ghTimer);
      ghTimer = setInterval(pollGithubWait, 5000);
      pollGithubWait();
    } catch (e) {
      sessionStorage.removeItem(KEY_GH_WAIT);
    }
  }

  async function handleForm(act, form) {
    authError = "";
    const user = (form.user.value || "").trim();
    const pass = form.pass.value || "";
    try {
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
        if (!rec || !rec.salt || !rec.hash) return fail("auth.err.login");
        const hash = await hashPass(pass, rec.salt);
        if (hash !== rec.hash) return fail("auth.err.login");
        setSession({ kind: "local", username: rec.username, github: rec.github || null });
        renderSettings();
      }
    } catch (e) {
      fail("auth.err.store");
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
      stopGithubWait();
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
    if (act === "start-gh") {
      authError = "";
      startGithubWait();
      return;
    }
    if (act === "cancel-gh") {
      stopGithubWait();
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
    if (!on) document.getElementById("ok")?.classList.remove("show");
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
  resumeGithubWait();
  window.CpyApp = { openSettings, session };
})();
