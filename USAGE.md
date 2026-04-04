# 使用说明

这份文档只讲一件事：把当前项目跑起来。

## 你会得到什么

跑通后，这套系统会完成下面这条链路：

1. `tool/douyinLive-windows-amd64.exe` 抓取抖音直播间消息
2. `client.py` 连接本地 WebSocket 服务并转发事件
3. `backend/` 接收事件，写入 SQLite / 可选 Redis / 可选 Chroma
4. 在线 `Qwen` 生成提词建议，失败时自动回退到规则
5. `frontend/` 实时显示提词内容、模型状态、消息流

## 环境要求

- Windows
- Python 3.11+，当前仓库已在本机 Python 环境跑通过
- Node.js 16+，当前前端依赖已兼容 Node 16
- 可选：Redis
- 可选：Chroma
- 在线 Qwen API Key

## 第一步：准备配置

在项目根目录执行：

```powershell
copy .env.example .env
```

然后编辑 `.env`，最少保证这几项可用：

```env
ROOM_ID=你的直播间标识
LLM_MODE=qwen
DASHSCOPE_API_KEY=你的百炼APIKey
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus-latest
LLM_TIMEOUT_SECONDS=6
```

说明：

- `ROOM_ID` 不是房间标题，是直播间标识
- `DASHSCOPE_API_KEY` 不要提交到 git
- 如果你不想用模型，可以把 `LLM_MODE=heuristic`

## 第二步：准备抖音抓取服务

启动：

```powershell
tool\douyinLive-windows-amd64.exe
```

默认会在本地启动 WebSocket 服务，地址是：

```text
ws://127.0.0.1:1088/ws/直播间标识
```

如果服务端需要登录态，可以编辑：

- [tool/config.yaml](D:/总的ai分析/确定版/tool/config.yaml)

注意：

- 这里只能填你自己的本地 Cookie
- 仓库里的默认值已经被清空
- 不要把真实 Cookie 再提交进仓库

## 第三步：安装依赖

Python 依赖：

```powershell
pip install -r requirements.txt
```

前端依赖：

```powershell
cd frontend
"C:\Program Files\nodejs\node.exe" "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js" install
cd ..
```

## 第四步：启动系统

最简单方式：

```powershell
.\start_all.ps1
```

这个脚本会分别打开：

- 后端
- 前端
- 采集客户端

如果你想分开启动：

启动后端：

```powershell
.\start_backend_qwen.ps1
```

启动前端：

```powershell
.\start_frontend.ps1
```

启动采集客户端：

```powershell
python client.py
```

## 第五步：打开页面

前端默认地址：

```text
http://127.0.0.1:5173/
```

你应该能看到：

- 顶部状态条
- 中间主提词卡片
- 右侧消息流

## 怎么判断现在是不是正常工作

### 1. 看顶部状态

顶部会显示：

- `Connection`
- `Model`
- `Comments`
- `Total Events`

其中 `Model` 会显示类似：

- `qwen-plus-latest / ok`
- `qwen-plus-latest / fallback`
- `heuristic / heuristic`

含义：

- `ok`：在线 Qwen 正常生成
- `fallback`：Qwen 失败，改走规则兜底
- `heuristic`：当前就只用规则

### 2. 看提词卡片来源标签

每条建议会带来源标签：

- `模型生成`
- `规则兜底`
- `规则生成`

含义：

- `模型生成`：这条建议来自在线 Qwen
- `规则兜底`：本来想走 Qwen，但失败了，退回规则
- `规则生成`：系统本身就在纯规则模式运行

### 3. 看数据库

SQLite 默认文件：

- `data/live_prompter.db`

这里会保存：

- 事件
- 建议
- 用户画像雏形

## 调试方式

如果你想先看原始消息结构，运行：

```powershell
python debug_client.py
```

它会：

- 打印完整 JSON
- 写日志到 `logs/`

适合确认：

- 直播间是否真有消息
- 当前消息字段长什么样
- 采集层有没有正常连上

## 最常见问题

### 1. 页面打开了，但没有建议

先检查：

- `tool/douyinLive-windows-amd64.exe` 是否已启动
- `.env` 里的 `ROOM_ID` 是否正确
- 直播间是否真的开播
- `client.py` 是否已运行

### 2. 顶部显示 `fallback`

说明 Qwen 调用失败了，系统正在用规则兜底。

优先检查：

- `DASHSCOPE_API_KEY` 是否正确
- 网络是否能访问百炼
- 是否触发超时或限流

### 3. 顶部显示 `heuristic`

说明当前没在走模型，一般是：

- `.env` 里设成了 `LLM_MODE=heuristic`
- 或者你没有正确加载 `.env`

### 4. 前端打不开

检查：

- `start_frontend.ps1` 是否正常启动
- `5173` 端口是否被占用

### 5. 后端启动了但没写入数据

先看：

- `python client.py` 是否已运行
- `BACKEND_EVENT_URL` 是否是 `http://127.0.0.1:8000/api/events`

## 当前版本定位

这不是“全功能直播运营平台”，而是一个已经能跑通的最简版本：

- 能采集
- 能存储
- 能调在线 Qwen
- 能实时出提词
- 能在前端展示状态和来源

如果你后面要继续扩，优先级建议是：

1. 真实直播场景试跑
2. 根据效果调 Prompt 和模型参数
3. 再决定要不要加更复杂的交互和反馈闭环
