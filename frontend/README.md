# Frontend — FollowUai

Painel desktop em Electron + Vite + React + TypeScript.

## Dev
```powershell
cd Folow_Uai\frontend
npm install
npm run dev
```

O Vite + Electron sobem juntos. Vite serve em `http://localhost:5173`, Electron
abre janela carregando essa URL. HMR funciona pra mudanças no React.

**Pré-req:** backend rodando em `http://localhost:8000` (via `uvicorn backend.main:app`).

## Build prod
```powershell
npm run build           # TS check + Vite build (dist/ + dist-electron/)
npm run electron:build  # + electron-builder → release/Setup.exe
```

## Configurar API URL
Por padrão bate em `http://localhost:8000/api`. Pra mudar:
```powershell
$env:VITE_API_BASE="http://outro-host:8000/api"
npm run dev
```

## Layout
```
frontend/
├── electron/main.ts         # Electron main process
├── src/
│   ├── main.tsx             # React entry
│   ├── App.tsx              # Sidebar + Routes
│   ├── index.css            # Estilos globais minimal
│   ├── api/
│   │   ├── client.ts        # fetch wrapper + ApiError
│   │   ├── types.ts         # Tipos espelhando schemas backend
│   │   └── endpoints.ts     # Funções tipadas por endpoint
│   ├── components/
│   │   ├── HealthBadge.tsx  # Status backend no sidebar
│   │   ├── Modal.tsx
│   │   └── ErrorBanner.tsx
│   └── pages/
│       ├── ClientesPage.tsx    # CRUD + import/export Excel
│       ├── TelefonesPage.tsx   # CRUD + connect WhatsApp (QR)
│       ├── TemplatesPage.tsx   # CRUD
│       ├── RelatoriosPage.tsx  # stats + envios recentes
│       └── AdminPage.tsx       # backup + dispatch manual
├── package.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```
