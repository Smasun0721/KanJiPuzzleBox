import os
from datetime import datetime
import json
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

# 创建FastAPI实例
app = FastAPI(title="汉字迷盒")
# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 创建会话数据存放目录
if not os.path.exists("sessions"):
    os.mkdir("sessions")


# 数据模型
class Result(BaseModel):
    code: int
    message: str
    data: Any


#  定义操作路径函数
@app.get('/')
def index():
    return FileResponse("static/index.html")


# 新建会话
def get_session_id():
    # 通过时间创建会话标识
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


@app.post('/api/sessions')
def new_session() -> Result:
    print("创建会话")
    # 1.生成会话标识
    session_id = get_session_id()

    # 2.创建会话文件并保存
    session_data = {
        "current_session": session_id,
        "message": []
    }
    with open(f"sessions/{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=4)

    # 3.返回会话数据
    return Result(code=200, message="创建会话成功", data={"session_id": session_id})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
