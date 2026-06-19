@echo off
cd /d "D:\ASUS\Desktop\2026\People_Mechine_Project"
if not exist "backend\data" mkdir "backend\data"
python backend/app.py --port 8000
pause