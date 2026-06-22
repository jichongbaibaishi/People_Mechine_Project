import os

file_path = r'c:\Users\ASUS\Documents\trae_projects\People_Mechine_Project\android\app\src\main\java\com\example\stressassessment\MainActivity.java'

with open(file_path, 'rb') as f:
    content = f.read()

# Remove BOM
content = content.lstrip(b'\xef\xbb\xbf')

with open(file_path, 'wb') as f:
    f.write(content)

print('BOM removed successfully')
