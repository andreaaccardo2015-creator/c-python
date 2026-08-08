const vscode = require("vscode");
const path = require("path");
const http = require("http");

const DAEMON = { host: "127.0.0.1", port: 39271 };

function getLogoUri(webview, extensionUri) {
  const logoPath = vscode.Uri.joinPath(extensionUri, "media", "logo.png");
  return webview.asWebviewUri(logoPath);
}

function notifyDaemon(filePath, event) {
  try {
    const data = JSON.stringify({ path: filePath, event: event || "open", language: "cpython" });
    const req = http.request(
      {
        host: DAEMON.host,
        port: DAEMON.port,
        path: "/notify-cpy",
        method: "POST",
        headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
        timeout: 1500,
      },
      () => {}
    );
    req.on("error", () => {});
    req.write(data);
    req.end();
  } catch (_) {}
}

function ensureCpythonLanguage(doc) {
  if (!doc || doc.uri.scheme !== "file") return;
  const ext = path.extname(doc.fileName || "").toLowerCase();
  if (ext !== ".cpy" && ext !== ".cp") return;
  // Forza C Python anche se VS Code/Cursor l'ha aperto come python
  if (doc.languageId !== "cpython") {
    vscode.languages.setTextDocumentLanguage(doc, "cpython").then(
      () => {},
      () => {}
    );
  }
  notifyDaemon(doc.fileName, "open");
}

function welcomeHtml(logoSrc) {
  return `<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root {
      --bg: #f7f9fc;
      --text: #0f2744;
      --accent: #3b6fbf;
      --muted: #5a6b82;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #121820;
        --text: #e8eef8;
        --accent: #6b9ae8;
        --muted: #9aabbf;
      }
    }
    html, body {
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", system-ui, sans-serif;
    }
    .wrap {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      box-sizing: border-box;
      text-align: center;
    }
    img.logo {
      width: min(180px, 40vw);
      height: auto;
      margin-bottom: 1.25rem;
    }
    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      margin: 0 0 0.5rem;
      letter-spacing: -0.02em;
    }
    p {
      color: var(--muted);
      max-width: 28rem;
      line-height: 1.5;
      margin: 0;
    }
    code {
      background: rgba(59, 111, 191, 0.12);
      padding: 0.1em 0.35em;
      border-radius: 4px;
      font-size: 0.95em;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <img class="logo" src="${logoSrc}" alt="C Python" />
    <h1>C Python</h1>
    <p>Crea file <code>.cpy</code> — evidenziazione automatica. Esegui con <code>cpy run file.cpy</code>.</p>
  </div>
</body>
</html>`;
}

class WelcomeViewProvider {
  constructor(extensionUri) {
    this.extensionUri = extensionUri;
  }

  resolveWebviewView(webviewView) {
    webviewView.webview.options = {
      enableScripts: false,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };
    const logo = getLogoUri(webviewView.webview, this.extensionUri);
    webviewView.webview.html = welcomeHtml(logo.toString());
  }
}

function showWelcomePanel(context) {
  const panel = vscode.window.createWebviewPanel(
    "cpythonWelcome",
    "C Python",
    vscode.ViewColumn.One,
    {
      enableScripts: false,
      localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, "media")],
      retainContextWhenHidden: true,
    }
  );
  const logo = getLogoUri(panel.webview, context.extensionUri);
  panel.webview.html = welcomeHtml(logo.toString());
  try {
    panel.iconPath = {
      light: vscode.Uri.joinPath(context.extensionUri, "media", "icon.png"),
      dark: vscode.Uri.joinPath(context.extensionUri, "media", "icon.png"),
    };
  } catch (_) {}
}

async function runCurrentFile(uri) {
  let file = null;
  if (uri && uri.fsPath) {
    file = uri.fsPath;
  } else {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage("Nessun file C Python aperto.");
      return;
    }
    file = editor.document.fileName;
    await editor.document.save();
  }
  const ext = path.extname(file).toLowerCase();
  if (ext !== ".cpy" && ext !== ".cp") {
    vscode.window.showWarningMessage("Apri un file .cpy");
    return;
  }
  notifyDaemon(file, "run");

  const term =
    vscode.window.terminals.find((t) => t.name === "C Python") ||
    vscode.window.createTerminal({
      name: "C Python",
      shellPath: process.platform === "win32" ? "cmd.exe" : undefined,
    });
  term.show(true);
  // Path con spazi (cartella "c python"): passa sempre da cmd /c su Windows
  const safe = String(file).replace(/"/g, "");
  if (process.platform === "win32") {
    term.sendText(`cmd /c cpy run "${safe}"`);
  } else {
    term.sendText(`cpy run "${safe}"`);
  }
}

function activate(context) {
  const provider = new WelcomeViewProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("cpython.welcomeView", provider)
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("cpython.showWelcome", () => showWelcomePanel(context))
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("cpython.runCurrentFile", (uri) => runCurrentFile(uri))
  );

  // Tema Seti + logo C Python SOLO su .cpy/.cp (non toglie le altre icone)
  const wb = vscode.workspace.getConfiguration("workbench");
  const theme = wb.get("iconTheme");
  if (!theme || theme === "cpython-file-icons" || theme === "vs-seti" || theme === "vs-minimal") {
    wb.update("iconTheme", "cpython-seti", vscode.ConfigurationTarget.Global);
  }

  // Appena apri/crei .cpy → linguaggio C Python + segnale demone + icona linguaggio
  for (const doc of vscode.workspace.textDocuments) {
    ensureCpythonLanguage(doc);
  }
  if (vscode.window.activeTextEditor) {
    ensureCpythonLanguage(vscode.window.activeTextEditor.document);
  }
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((doc) => ensureCpythonLanguage(doc))
  );
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((ed) => {
      if (ed) ensureCpythonLanguage(ed.document);
    })
  );
  context.subscriptions.push(
    vscode.workspace.onDidCreateFiles((e) => {
      for (const uri of e.files) {
        const ext = path.extname(uri.fsPath).toLowerCase();
        if (ext === ".cpy" || ext === ".cp") {
          notifyDaemon(uri.fsPath, "created");
          vscode.workspace.openTextDocument(uri).then((doc) => ensureCpythonLanguage(doc));
        }
      }
    })
  );

  const key = "cpython.welcomeShown";
  const shown = context.workspaceState.get(key);
  if (!shown) {
    showWelcomePanel(context);
    context.workspaceState.update(key, true);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
