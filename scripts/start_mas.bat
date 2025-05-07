@echo off
setlocal

REM Activate virtual environment
call .\.venv\Scripts\activate

REM Set environment variables
set PYTHONPATH=%CD%
set MAS_ENV=development

REM Start the MAS
python -m mycosoft_mas.run_mas

endlocal 