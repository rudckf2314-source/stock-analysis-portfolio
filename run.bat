@echo off
chcp 65001 > nul
cls

echo ========================================
echo FDGE Terminal Pro - AI 투자 분석 시스템
echo ========================================
echo.

REM 현재 디렉토리 저장
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/4] 환경 확인 중...
echo.

REM Python 설치 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo Python을 설치한 후 다시 실행하세요.
    pause
    exit /b 1
)

echo ✅ Python 환경 확인 완료
echo.

echo [2/4] 가상환경 확인 중...
echo.

REM 가상환경 존재 확인
if not exist "myenv312\Scripts\activate" (
    echo ⚠️  가상환경이 존재하지 않습니다.
    echo 📦 가상환경을 생성합니다...
    python -m venv myenv312
    if errorlevel 1 (
        echo ❌ 가상환경 생성 실패
        pause
        exit /b 1
    )
    echo ✅ 가상환경 생성 완료
) else (
    echo ✅ 가상환경 확인 완료
)

echo.
echo [3/4] 필수 패키지 확인 중...
echo.

REM 가상환경 활성화 후 패키지 확인
call myenv312\Scripts\activate

REM FastAPI가 설치되어 있는지 확인
python -c "import fastapi" > nul 2>&1
if errorlevel 1 (
    echo 📦 필수 패키지를 설치합니다...
    echo.
    pip install -q fastapi uvicorn[standard] python-multipart pandas yfinance pykrx pydantic google-generativeai python-dotenv crewai crewai-tools
    if errorlevel 1 (
        echo ❌ 패키지 설치 실패
        pause
        exit /b 1
    )
    echo ✅ 패키지 설치 완료
) else (
    echo ✅ 필수 패키지 확인 완료
)

echo.
echo [4/4] 서버 실행 중...
echo.
echo 🚀 FastAPI 서버가 시작됩니다...
echo 📍 주소: http://localhost:8001
echo 📚 API 문서: http://localhost:8001/docs
echo 🎯 Fund Manager: http://localhost:8001/fund_manager
echo.
echo ⚠️  이 창을 닫으면 서버가 종료됩니다!
echo 🌐 브라우저가 자동으로 열립니다...
echo.
echo ========================================
echo.

REM 브라우저 열기 (3초 후)
timeout /t 3 > nul
start "" "http://localhost:8001"

REM 서버 실행
uvicorn api:app --host 0.0.0.0 --port 8001 --reload

REM 서버 종료 시 메시지
echo.
echo ========================================
echo 서버가 종료되었습니다.
echo ========================================
pause
