import os
from datetime import datetime
import json
from typing import Any
from fastapi import FastAPI
from openai import OpenAI
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


class ChatRequest(BaseModel):
    session_id: str
    message: str


#  定义操作路径函数
@app.get('/')
def index():
    return FileResponse("static/index.html")


# 通过时间创建会话标识
def get_session_id():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# 新建会话
@app.post('/api/sessions')
def new_session() -> Result:
    print("创建会话")
    # 1.生成会话标识
    session_id = get_session_id()

    # 2.创建会话文件并保存
    session_data = {
        "current_session": session_id,
        "messages": []
    }
    with open(f"sessions/{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=4)

    # 3.返回会话数据
    return Result(code=200, message="创建会话成功", data=session_id)


# 系统提示词 - 适配DeepSeek V4
SYSTEM_PROMPT = """
# 角色定义
你是一个专门玩猜字谜的AI小助手，只进行字谜互动，不闲聊无关内容，全程纯文本交互，不使用表情符号。

## 核心能力
- 出字谜、判对错、给提示
- 记忆已用谜题，确保会话内不重复
- 简洁明快回应

## 出题规则（严格执行！）
1. 开场先友好打招呼，并随机出一道常见、简单、适合大众并必须符合逻辑推理的字谜，禁止使用生僻、低俗、网络烂梗。
2. 题目格式：“谜面”（打一字）。
3. 每次出题必须完全随机，禁止重复使用相同题目，也可以偶尔穿插使用，下面示例中的谜语。
4. 新出题目时, 不要提示, 用户需要提示时, 或者答错时, 再给予合理的提示。

## 判题规则（严格执行！）
1. 用户只回复一个字时，直接视为答案。
2. 答对：立即夸奖并揭晓谜底，格式如“太棒了！就是‘X’字！要不要再来一题？”
3. 答错：告知不对，可给一句简短提示，但不泄露答案。格式如“不对哦，再想想~”
4. 严禁在用户答错后直接公布答案！只有用户说“公布答案”或“不知道”等情况时才公布。

## 互动流程
1. 用户答对：夸奖 + 确认正确 + 询问“要不要再来一题？”
2. 用户答错：告知不对 + 简单提示 + 鼓励继续猜
3. 用户说“提示一下”：给出简短线索，不公布答案
4. 用户说“公布答案”或“不知道”：揭晓谜底并解释 + 询问“要不要再来一题？”
5. 用户说“换一题”“再来一题”：立即更换新字谜

## 回复风格约束
- 语气轻松有趣，但保持简洁
- 全程只围绕字谜，拒绝回答其他问题
- 回复不超过3句话
- **绝对不要在回复中说“这个出过了，我来个新的”或类似表述** — 直接给出新谜语即可
- 判题错误零容忍，不确定谜底时，先回复“我再想想”而不是乱判

## 常见谜语类型及谜底参考示例, 仅仅为参照示例
### 组合类
- 「一加一不是二」= 王
- 「二人不是天」= 夫
- 「十口不是田」= 古

### 包含类
- 「一人在内」= 肉
- 「口里有人」= 囚
- 「门里有口」= 问
- 「田里长草」= 苗
- 「心里有你」= 您
- 「山里有山」= 出
- 「王头上有人」= 全
- 「水上有石」= 泵

### 半取类
- 「半吃半拿」= 哈
- 「半真半假」= 值
- 「半青半紫」= 素
- 「半朋半友」= 有
- 「半推半就」= 扰
- 「半山半水」= 汕

### 象形类
- 「三人又重逢」= 众
- 「一口咬掉牛尾巴」= 告
- 「两座山」= 出
- 「三日又重逢」= 晶
"""


# 根据会话ID获取会话数据文件路径
def get_session_file_path(session_id: str) -> str:
    return f"sessions/{session_id}.json"


# 创建客户端对象
client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")


# 与AI交互
@app.post('/api/chat')
def chat(request: ChatRequest) -> Result:
    print(f"与AI交互[session_id:{request.session_id}]\n----->用户输入:{request.message}")
    # 1.加载文件中的会话数据
    session_file_path = get_session_file_path(request.session_id)
    with open(session_file_path, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # 2.构建大模型请求数据
    request_data = [{"role": "system", "content": SYSTEM_PROMPT}, *session_data["messages"],
                    {"role": "user", "content": request.message}]

    # 3.向AI大模型发起请求
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=request_data,
        stream=False
    )

    # 4.获取大模型响应数据
    ai_response = response.choices[0].message.content
    print(f"<-----AI回复:{ai_response}")

    # 5.更新会话列表数据
    session_data["messages"].append({"role": "user", "content": request.message})
    session_data["messages"].append({"role": "assistant", "content": ai_response})

    # 6.保存会话数据
    with open(session_file_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=4)
        print(f"保存会话数据成功:{session_file_path}")

    # 7.返回会话数据
    return Result(code=200, message="与AI交互成功", data=ai_response)


# 加载会话列表
@app.get('/api/sessions')
def get_session_list() -> Result:
    print("加载会话列表")
    # 1.获取session目录下的文件列表
    session_files = os.listdir("sessions")

    # 2.通过文件名获取session_id
    session_list = [file.split(".")[0] for file in session_files if file.endswith(".json")]
    session_list.sort(reverse=True)

    # 3.返回会话列表
    return Result(code=200, message="获取会话列表成功", data=session_list)


# 通过会话id加载会话数据
@app.get('/api/sessions/{session_id}')
def get_session_data(session_id: str) -> Result:
    print(f"加载会话数据[session_id:{session_id}]")
    # 1.获取会话数据文件路径
    session_file_path = get_session_file_path(session_id)

    # 2.判断文件是否存在
    if not os.path.exists(session_file_path):
        return Result(code=404, message="会话数据不存在", data=None)

    # 3.加载会话数据
    with open(session_file_path, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # 4.返回会话数据
    return Result(code=200, message="获取会话数据成功", data=session_data)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
