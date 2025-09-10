# AI Life Assistant

Web: Flask API + Streamlit frontend.

## Local dev

1. Python 3.12
2. Create venv and install deps
   - macOS/Linux:
     - `python3 -m venv venv && source venv/bin/activate`
     - `pip install -r requirements.txt`
3. Env
   - create `.env` with `GEMINI_API_KEY=...`
4. Run API
   - `python ai_life_assistant/app.py`
5. Run Streamlit
   - `streamlit run ai_life_assistant/dashboard.py`

## Deploy overview

- API: host on Render/Heroku/Fly.io (uses `Procfile` with gunicorn)
- Frontend: host on Streamlit Community Cloud

### Deploy API on Render (free tier)

1. Push this folder to GitHub (see below).
2. Create new Web Service on Render
   - Repo: your GitHub repo
   - Runtime: Python 3.12
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -w 2 -b 0.0.0.0:$PORT ai_life_assistant.app:app`
   - Environment variables: `GEMINI_API_KEY`
3. After deploy, note the base URL (e.g., `https://your-api.onrender.com`).

### Deploy Streamlit on Streamlit Community Cloud

1. Push code to public GitHub repo.
2. In Streamlit Cloud, create new app
   - Repo: your GitHub repo
   - Branch: main
   - File: `ai_life_assistant/dashboard.py`
   - Environment variables: set `BASE_URL` to your API URL
3. Save and deploy.

### GitHub: create and push repo

```bash
# From /Users/muhammadafzal/Downloads/ai_life_assistant
git init
git add .
git commit -m "AI Life Assistant initial deploy"
# Create a repo on GitHub (via website), then:
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

### .env (local only)

```env
GEMINI_API_KEY=your_key_here
```

For Streamlit Cloud, put this in the Secrets manager or environment variables. For Render, add it in the service env.

### Configure Streamlit BASE_URL

If API URL is `https://your-api.onrender.com`, set in Streamlit secrets or env:

```env
BASE_URL=https://your-api.onrender.com
```

## Notes

- CORS is enabled on the API.
- Use `health` at `/health` to verify API.
- Chat streaming endpoint is `/chat/stream`.

---

Optional:

- Render one-click (use local `render.yaml`):

```bash
curl -fsSL https://render.com/deploy | bash
```

- Streamlit config (local dev): see `.streamlit/config.toml`.
