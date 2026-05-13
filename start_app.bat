@echo off
cd /d "c:\Users\ASUS\Documents\trae_projects\People_Mechine_Project"
if not exist "backend\data" mkdir "backend\data"
python backend/app.py
pause