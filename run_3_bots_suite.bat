@echo off
title 3 Master Bots Quantitative Suite
echo Starting 3 Master Bots Suite (9 Quant Strategies)...
cd /d "%~dp0bots_suite"
python suite_runner.py --bot all
echo.
echo Dashboard generated at: %~dp0bots_suite\suite_dashboard.html
pause
