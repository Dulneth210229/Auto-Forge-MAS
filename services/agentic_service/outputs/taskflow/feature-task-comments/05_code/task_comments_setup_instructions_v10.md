# Setup Instructions

## Run the app

This project has a working Express server (`server/`) and a Vite+React client (`client/`) scaffolded from the start -- these commands work for every feature, not just this one.

```bash
npm run install:all   # installs server/ and client/ dependencies
cp server/.env.example server/.env   # first time only -- fill in real values
npm run dev           # boots the Express API (port 5000) and the Vite dev server (port 5173)
```

## New dependencies added by this feature

Already declared in the relevant `package.json` and installed by `npm run install:all` above; listed here for traceability:

- `tailwindcss`
- `autoprefixer`
- `postcss`
