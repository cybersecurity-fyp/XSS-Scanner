@echo off
echo [XSSniper] Installing dependencies...
pip install -r requirements.txt
echo.
echo [XSSniper] Starting server at http://localhost:8080
echo [XSSniper] Press Ctrl+C to stop
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
