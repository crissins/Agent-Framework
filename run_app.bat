@echo off
REM Run Streamlit using the project virtual environment
"%~dp0.venv\Scripts\python.exe" -m streamlit run app.py %*
