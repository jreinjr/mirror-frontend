# comfystream-mirror

A standalone [Next.js](https://nextjs.org) frontend for a remotely running
[comfystream](https://github.com/yondonfu/comfystream) instance. It connects to
the comfystream server over WebRTC and provides the streaming UI (webcam input,
video/audio output, recording, text output, and stream settings).

This repo was copied from `comfystream/ui` and decoupled from the comfystream
codebase — it has no dependency on the parent project and is meant to be evolved
independently as a pure frontend.

## Getting Started

Install dependencies and run the dev server:

```bash
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

## Connecting to a comfystream instance

The frontend talks to a comfystream server's `/offer` endpoint (proxied through
this app's `/api/offer` route). The default server URL is `http://localhost:8889`.

You can change it two ways:

- **At runtime:** open the Settings dialog in the UI and edit the stream URL.
- **As a default:** set `NEXT_PUBLIC_DEFAULT_STREAM_URL` in `.env.local`
  (see `.env.example`).

## Scripts

- `npm run dev` — start the dev server on port 3000
- `npm run dev:https` — dev server over HTTPS (needed for some WebRTC/camera setups)
- `npm run build` — production build
- `npm run start` — serve the production build
- `npm run lint` / `npm run format`
