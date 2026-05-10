# -*- coding: utf-8 -*-
import os
from datetime import timedelta

# 基础目录（默认当前文件目录）
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# 自定义加密密钥（替换为自己生成的）
SECRET_KEY = "8f9d6b7e8a0c9d8e7f6a5b4c3d2e1f0a"
# 开启JSON中文支持
JSON_AS_ASCII = False

# 数据库（SQLite，文件名为 db.sqlite3）
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# JWT配置（Token 1天过期，算法HS256）
JWT_EXPIRES = timedelta(days=1)
JWT_ALGORITHM = "HS256"