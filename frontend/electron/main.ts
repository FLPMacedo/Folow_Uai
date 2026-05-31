import { app, BrowserWindow, shell } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

// __dirname pra ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// VITE_DEV_SERVER_URL injetado pelo vite-plugin-electron em modo dev
const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL;
const APP_ROOT = path.join(__dirname, "..");
const DIST_RENDERER = path.join(APP_ROOT, "dist");

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: "FollowUai",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // abrir links externos no browser do sistema, não dentro do app
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });

  if (DEV_SERVER_URL) {
    void mainWindow.loadURL(DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    void mainWindow.loadFile(path.join(DIST_RENDERER, "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

void app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
