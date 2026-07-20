@echo off
chcp 65001 > nul

echo ===========================
echo Starting DcaTp System
echo ===========================


REM ===========================
REM activate venv
REM ===========================

call venv\Scripts\activate


REM ===========================
REM Start LONG strategy
REM ===========================

echo [1/5] Starting LONG strategy...

start "DcaTp LONG" cmd /k ^
"call venv\Scripts\activate && cd freqtrade && freqtrade trade --config user_data/config_long.json --strategy DcaTpLong --logfile logs/long.log"


timeout /t 5 > nul


REM ===========================
REM Start SHORT strategy
REM ===========================

echo [2/5] Starting SHORT strategy...

start "DcaTp SHORT" cmd /k ^
"call venv\Scripts\activate && cd freqtrade && freqtrade trade --config user_data/config_short.json --strategy DcaTpShort --logfile logs/short.log"


timeout /t 5 > nul


REM ===========================
REM Start backend
REM ===========================

echo [3/5] Starting backend...


start "DcaTp Backend" cmd /k ^
"call venv\Scripts\activate && cd backend && uvicorn app.main:app --reload --port 9000"


timeout /t 5 > nul


REM ===========================
REM Start frontend
REM ===========================

echo [4/5] Starting frontend...


start "DcaTp Frontend" cmd /k ^
"cd frontend && npm run dev"


echo ===========================
echo DcaTp Started
echo ===========================


pause