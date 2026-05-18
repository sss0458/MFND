# 局域网一键启动说明

## 使用方式

在主机电脑上：

1. 双击 [start_lan.command](/Users/sunhongzheng/Downloads/MFND/DeepFake_Detection_System/start_lan.command)
2. 等待终端输出访问地址
3. 在同一局域网其他电脑浏览器中打开：
   - `http://主机IP:5173`

停止服务时：

1. 双击 [stop_lan.command](/Users/sunhongzheng/Downloads/MFND/DeepFake_Detection_System/stop_lan.command)

## 运行前提

- 后端虚拟环境已存在：`backend/venv`
- 前端依赖已安装：`frontend/node_modules`
- 主机电脑和访问电脑处于同一局域网
- 主机电脑系统防火墙允许 `5173` 和 `8000` 端口访问

## 日志位置

- 后端日志：`.lan_runtime/backend.log`
- 前端日志：`.lan_runtime/frontend.log`

## 当前模式说明

- 前端通过 Vite 局域网开发服务开放到 `0.0.0.0:5173`
- 后端通过 FastAPI/Uvicorn 开放到 `0.0.0.0:8000`
- 浏览器侧统一通过 `/api` 访问后端
- 任务媒体资源和显著图链接会自动跟随当前访问主机地址生成

