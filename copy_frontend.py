import os
import shutil

src_dir = r'stress/stress  test'
dst_dir = r'android/app/src/main/assets/www'

os.makedirs(dst_dir, exist_ok=True)

for item in os.listdir(src_dir):
    src_path = os.path.join(src_dir, item)
    dst_path = os.path.join(dst_dir, item)
    if os.path.isfile(src_path):
        shutil.copy2(src_path, dst_path)
        print('Copied:', item)

print('Done!')
