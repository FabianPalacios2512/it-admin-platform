cd backend
$env:PYTHONIOENCODING = "utf-8"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --reload