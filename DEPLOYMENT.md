# UNMAPPED — Deployment Guide

## Quick Deploy to Streamlit Cloud ⚡

### Prerequisites
- GitHub account (you have one: `8atellojose-droid`)
- Repository on GitHub ✓

### Steps

1. **Go to Streamlit Cloud**
   ```
   https://share.streamlit.io
   ```

2. **Sign in with GitHub**
   - Use your GitHub credentials
   - Authorize Streamlit Cloud to access your repos

3. **Deploy Your App**
   - Click "New app"
   - Select your repo: `unmapped-5`
   - Branch: `main`
   - File: `app.py`
   - Click "Deploy"

4. **Your App is Live!**
   - Streamlit generates a unique URL like: `https://unmapped-5.streamlit.app`
   - Share this link with anyone

---

## Why Streamlit Cloud?

✅ **Free** (with limitations)  
✅ **Built for Streamlit** — no config needed  
✅ **Auto-deploys** from GitHub  
✅ **Custom domain** available (paid)  
✅ **Authentication** available (Streamlit Community Cloud Pro)  

---

## Alternative: Deploy to Railway

If Streamlit Cloud is unavailable or you want more control:

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Link to your project
railway link

# 4. Deploy
railway up
```

Railway provides a persistent URL and $5/month free credit.

---

## Environment Variables (if needed)

If you add secrets later, create `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml (DO NOT COMMIT)
[database]
url = "your-secret-url"

[api]
key = "your-api-key"
```

Then access in your app:
```python
import streamlit as st
db_url = st.secrets["database"]["url"]
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| App takes too long to load | Streamlit Cloud has `maxUploadSize=200MB` by default |
| Data files not loading | Ensure `data/` directory is committed to git |
| Dependencies missing | Check `requirements.txt` is complete |
| App crashes on deploy | Check logs in Streamlit Cloud dashboard |

---

## Local Development

To test locally before deploying:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open: `http://localhost:8501`

---

**Good to go!** Use the Streamlit Cloud link after deployment. 🚀
