# mxwerk.github.io

Personal portfolio built with [Quartz 4](https://quartz.jzhao.xyz/).

Live: https://mxwerk.github.io/ (noindex — reachable by link only)

## Content

- `content/index.md` — home page
- `content/projects/` — project writeups

## Local preview

```bash
npm ci
npx quartz build --serve -d content
```

## Deploy

Push to `main` → GitHub Actions (`.github/workflows/deploy.yml`) builds Quartz and publishes to Pages.

> Quartz is MIT-licensed — see `LICENSE.txt`.
