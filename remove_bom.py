# Remove BOM from MainActivity.java
file_path = r'c:\Users\ASUS\Documents\trae_projects\People_Mechine_Project\android\app\src\main\java\com\example\stressassessment\MainActivity.java'

with open(file_path, 'rb') as f:
    content = f.read()

# Remove UTF-8 BOM if present
if content.startswith(b'\xef\xbb\xbf'):
    content = content[3:]
    with open(file_path, 'wb') as f:
        f.write(content)
    print('BOM removed successfully')
else:
    print('No BOM found')
