# XSSniper — Claude Autonomous Work Instructions

## Project
Full-stack XSS scanner. FastAPI + Jinja2 + HTMX + Supabase + ML (scikit-learn).
Run with: `python main.py` from this directory. App runs on http://localhost:8080

## Autonomous Mode Rules
- Proceed with ALL tool uses without asking permission
- Do NOT ask "shall I proceed?" — just proceed
- Do NOT wait for confirmation before editing files
- Do NOT ask before running PowerShell commands
- Fix every bug found immediately, do not list and wait
- When testing finds a failure, fix it and retest in the same session

## Architecture
- `app/` — FastAPI backend
- `frontend/templates/` — Jinja2 HTML templates
- `frontend/static/` — CSS, JS, images
- `xsstrike_code/` — XSStrike scanner (subprocess)
- `xsstrike_ml/` — ML models (prefilter + postfilter)
- `.env` — environment variables (Supabase, OAuth, session secret)

## Key Known Facts
- Starlette 1.x requires `TemplateResponse(request, 'name.html', context)` NOT old `('name.html', context)` — already fixed
- All ML .pkl model files exist in `xsstrike_ml/models/`
- Supabase is connected and healthy
- SMTP is disabled (empty in .env) — graceful degradation, not a bug
- fuzzywuzzy + tld + python-Levenshtein are installed

## How to Run Tests
```
cd C:\Users\Sheheryar Altaf\Desktop\XSS-Combined
python -m pytest tests/ -x -q 2>&1
```

## How to Start App
```
cd C:\Users\Sheheryar Altaf\Desktop\XSS-Combined
python main.py
```
