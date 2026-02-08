@echo off
REM ======================================
REM arXiv論文日次収集＆Shorts動画生成バッチ
REM 毎日08:00自動実行
REM ======================================

cd /d "C:\Users\yke\Projects\entropic-aurora"

REM 仮想環境有効化
call .venv\Scripts\activate.bat

REM ログファイル設定
set LOGFILE=logs\batch_%date:~0,4%%date:~5,2%%date:~8,2%.log

REM メイン処理実行
echo [%date% %time%] Batch started >> %LOGFILE%
python main.py >> %LOGFILE% 2>&1

REM Shorts動画生成（VOICEVOX起動が必要）
echo [%date% %time%] Shorts video generation >> %LOGFILE%
python test_moviepy_e2e.py >> %LOGFILE% 2>&1

echo [%date% %time%] Batch completed >> %LOGFILE%
