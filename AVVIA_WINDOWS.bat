@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo Creazione ambiente Python locale...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto errore
)
echo Installazione dipendenze, se necessaria...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto errore
echo Generazione dati e caricamento database...
".venv\Scripts\python.exe" prepare.py
if errorlevel 1 goto errore
echo Apertura dashboard nel browser...
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto errore
goto fine
:errore
echo ERRORE. Controlla di avere Python 3.11–3.15 e una connessione per le dipendenze.
pause
:fine
endlocal
