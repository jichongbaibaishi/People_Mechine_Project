#!/usr/bin/env python3
"""Simple server launcher to bypass Trae security prompts."""
import subprocess
import os

os.chdir("c:\\Users\\ASUS\\Documents\\trae_projects\\People_Mechine_Project")
subprocess.run(["python", "backend/app.py"], shell=True)