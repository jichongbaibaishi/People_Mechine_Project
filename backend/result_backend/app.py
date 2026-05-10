# -*- coding: utf-8 -*-
import os
import uuid
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import jwt
from datetime import datetime

# ===================== 配置 =====================
SECRET_KEY = "8f9d6b7e8a0c9d8e7f6a5b4c3d2e1f0a"
JSON_AS_ASCII = False
JWT_ALGORITHM = "HS256"

SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 初始化应用
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['JSON_AS_ASCII'] = JSON_AS_ASCII
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

CORS(
    app,
    supports_credentials=True,  # 允许跨域携带自定义头
    expose_headers=["Anonymous-ID"],  # 暴露自定义头
    allow_headers=["Authorization", "Anonymous-ID", "Content-Type"]  # 允许接收的自定义头
)
db = SQLAlchemy(app)

# ===================== 数据库模型（兼容登录+匿名） =====================
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    create_time = db.Column(db.DateTime, default=datetime.now)

# 🔥 关键修改：支持 user_id（登录） + anonymous_id（匿名） 双字段
class EvalRecord(db.Model):
    __tablename__ = "eval_record"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)  # 登录用户ID
    anonymous_id = db.Column(db.String(50), nullable=True)  # 匿名用户唯一ID
    title = db.Column(db.String(100))
    desc = db.Column(db.Text)
    radar = db.Column(db.JSON)
    visual = db.Column(db.JSON)
    score = db.Column(db.Float)
    create_time = db.Column(db.DateTime, default=datetime.now)


def get_user_identity():
    # 1. 优先获取登录用户
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return {"type": "user", "id": payload["user_id"]}
        except Exception as e:
            print(f"Token解析失败：{e}")
            pass
    # 2. 获取匿名用户ID
    anonymous_id = request.headers.get("Anonymous-ID")
    print(f"后端接收到的Anonymous-ID：{anonymous_id}")  # 关键日志
    if anonymous_id:
        return {"type": "anonymous", "id": anonymous_id}
    return None
# ===================== 通用查询条件 =====================
def get_record_query(identity):
    if identity["type"] == "user":
        return EvalRecord.user_id == identity["id"]
    return EvalRecord.anonymous_id == identity["id"]

# ===================== 接口（全自动适配双模式） =====================
@app.route("/api/record/save", methods=["POST"])
def save_record():
    identity = get_user_identity()
    if not identity:
        return jsonify({"code":401,"msg":"请登录或使用匿名模式"})

    d = request.json
    record = EvalRecord(
        user_id=identity["id"] if identity["type"]=="user" else None,
        anonymous_id=identity["id"] if identity["type"]=="anonymous" else None,
        title=d["title"], desc=d.get("desc",""),
        radar=d["radar"], visual=d["visual"], score=d["score"]
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"code":200,"msg":"保存成功","data":{"id":record.id}})

@app.route("/api/record/list", methods=["GET"])
def get_list():
    identity = get_user_identity()
    if not identity:
        return jsonify({"code":401,"msg":"请登录或使用匿名模式"})

    records = EvalRecord.query.filter(get_record_query(identity)).order_by(EvalRecord.create_time.desc()).all()
    data = [{
        "id":r.id,"title":r.title,"score":r.score,
        "create_time":r.create_time.strftime("%Y-%m-%d %H:%M")
    } for r in records]
    return jsonify({"code":200,"data":data})

@app.route("/api/record/detail/<int:id>")
def get_detail(id):
    identity = get_user_identity()
    if not identity:
        return jsonify({"code":401,"msg":"请登录或使用匿名模式"})

    r = EvalRecord.query.filter(EvalRecord.id==id, get_record_query(identity)).first()
    if not r:
        return jsonify({"code":400,"msg":"记录不存在"})
    return jsonify({"code":200,"data":{
        "radar":r.radar,"visual":r.visual,"title":r.title,"score":r.score
    }})

@app.route("/api/record/delete/<int:id>", methods=["DELETE"])
def delete(id):
    identity = get_user_identity()
    if not identity:
        return jsonify({"code":401,"msg":"请登录或使用匿名模式"})

    r = EvalRecord.query.filter(EvalRecord.id==id, get_record_query(identity)).first()
    if r: db.session.delete(r)
    db.session.commit()
    return jsonify({"code":200,"msg":"删除成功"})

@app.route("/api/record/clear", methods=["DELETE"])
def clear():
    identity = get_user_identity()
    if not identity:
        return jsonify({"code":401,"msg":"请登录或使用匿名模式"})

    EvalRecord.query.filter(get_record_query(identity)).delete()
    db.session.commit()
    return jsonify({"code":200,"msg":"清空成功"})

@app.route("/api/record/compare", methods=["GET"])
def compare():
    identity = get_user_identity()
    if not identity:
        return jsonify({"code":401,"msg":"请登录或使用匿名模式"})

    ids = request.args.getlist("ids", type=int)
    data = [{
        "id":r.id,"title":r.title,"radar":r.radar,"score":r.score
    } for r in EvalRecord.query.filter(EvalRecord.id.in_(ids), get_record_query(identity))]
    return jsonify({"code":200,"data":data})

# ===================== 启动 =====================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5001, debug=True)