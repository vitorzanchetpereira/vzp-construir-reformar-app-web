@echo off
REM Inicia o Construir e Reformar. Dois cliques neste arquivo e abra http://localhost:5000
cd /d "%~dp0"
if not exist ".venv" (
  echo Criando ambiente virtual...
  py -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
echo.
echo ============================================================
echo   Construir e Reformar rodando em:  http://localhost:5000
echo   Para parar: feche esta janela ou aperte Ctrl+C
echo ============================================================
echo.
.venv\Scripts\python.exe app.py
pause
