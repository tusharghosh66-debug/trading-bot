@echo off
title Setup Alpha Trader on Laptop
color 0B
echo =====================================================================
echo          ANTIGRAVITY ALPHA TRADER - LAPTOP SETUP
echo =====================================================================
echo.
echo Installing Python libraries (pandas, yfinance, requests, tabulate, rich)...
python -m pip install pandas yfinance requests tabulate rich
echo.
echo =====================================================================
echo  SETUP FINISHED SUCCESSFULLY!
echo  Now double-click 'run_bot.bat' to start the bot on this laptop.
echo =====================================================================
pause
