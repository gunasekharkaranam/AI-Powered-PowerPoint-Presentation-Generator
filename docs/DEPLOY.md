# Deploy

## 1. Get an API key (free)

Google AI Studio → https://aistudio.google.com/apikey → Create API key.
Put it in `.env` locally, or in your host's **secrets**. Never in code.

## 2. Hugging Face Spaces (recommended, free, 16 GB RAM, previews work)

1. huggingface.co → **New Space** → SDK **Docker** → Public.
2. Push this repo to the Space (`git remote add space https://huggingface.co/spaces/<you>/slidegen && git push space main`).
3. The Space's README must start with:
   ```yaml
   ---
   title: SlideGen
   sdk: docker
   app_port: 7860
   ---
   ```
4. **Settings → Variables and secrets** → add secret `GEMINI_API_KEY`.

## 3. Render (Docker)

**New → Blueprint** → choose the repo (`render.yaml`) → set `GEMINI_API_KEY`.
The free plan has 512 MB RAM. If previews make it crash, build with `WITH_PREVIEW=0` (Docker build arg).

## 4. Anywhere with Docker

```bash
docker build -t slidegen .                         # with previews
docker build --build-arg WITH_PREVIEW=0 -t slidegen-lite .
docker run -p 7860:7860 --env-file .env slidegen
```
