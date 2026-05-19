# Docker Compose 一键部署

这套部署会把系统拆成 3 个容器：

- `frontend`：`Nginx` 提供前端页面，并把 `/api` 和 `/static` 代理到后端
- `backend`：`FastAPI` 服务，负责登录、检测、审核、导出等接口
- `db`：`MySQL 8`，存放用户、任务、审核结果

## 1. 前置条件

- 服务器已安装 Docker
- 服务器已安装 Docker Compose 插件
- 服务器可以访问外网，首次启动需要拉镜像并可能下载 Hugging Face 模型

## 2. 准备环境变量

在项目根目录执行：

```bash
cp .env.docker.example .env.docker
```

然后至少修改这些配置：

- `APP_PORT`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- FAST 双模型融合配置
  默认已恢复为双模型联合判别：`Arko007/fact-check1-v1` + `divyanshu-chauhan-7786/fake-news-roberta`。这套配置会按最早线上表现较好的策略允许加载 PyTorch `.bin` 权重；如果服务器模型下载慢，可以先在本地预热 Hugging Face 缓存，或保持 `HF_ENDPOINT` 为可访问镜像。
- PRO 大模型 API 配置
  如果 Gemini 因地区不可用，推荐使用阿里云百炼 DashScope 的 OpenAI 兼容多模态接口：

```env
PRO_API_PROVIDER=openai_compatible
PRO_API_KEY=你的百炼APIKey
PRO_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PRO_MODEL_NAME=qwen-vl-plus
```

  如果继续使用 Gemini，则设置：

```env
PRO_API_PROVIDER=gemini
GEMINI_API_KEY=你的GeminiKey
```

  如果暂时不用 `Pro` 引擎，可以把这些 Key 留空，前端会显示 PRO 离线。

已有服务器部署如果已经存在 `.env.docker`，模板不会自动覆盖它；请手动同步上面的 FAST/PRO 配置后再重启容器。

## 3. 启动服务

在项目根目录执行：

```bash
docker compose --env-file .env.docker up -d --build
```

启动完成后，通过下面的地址访问：

```text
http://服务器IP:APP_PORT
```

如果 `APP_PORT=80`，就可以直接用：

```text
http://服务器IP
```

## 3.1 服务器一键发布

如果你已经把项目放到服务器上，后续更新推荐直接执行：

```bash
chmod +x deploy_server.sh
./deploy_server.sh
```

这个脚本会自动完成这些事：

- 检查 Docker 和 Docker Compose 是否可用
- 如果缺少 `.env.docker`，自动从模板复制一份
- 在 Git 仓库干净时自动执行 `git fetch` 和 `git pull --ff-only`
- 自动执行 `docker compose --env-file .env.docker up -d --build --remove-orphans`
- 输出当前容器状态和可访问地址

如果服务器上的代码目录有本地改动，不想自动 `git pull`，可以这样执行：

```bash
SKIP_GIT_PULL=true ./deploy_server.sh
```

## 4. 常用运维命令

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

停止服务：

```bash
docker compose down
```

保留数据库数据并重新构建：

```bash
docker compose --env-file .env.docker up -d --build
```

如果要连同数据库卷一起清空：

```bash
docker compose down -v
```

## 5. 部署说明

- 上传文件、检测结果图保存在宿主机 `./data`
- MySQL 数据保存在 Docker 卷 `mysql_data`
- Hugging Face 模型缓存保存在 Docker 卷 `hf_cache`
- 前端现在通过同域名访问后端，所以部署后不需要再改前端接口地址

## 6. 首次启动可能较慢

首次启动时，后端可能会自动下载这些模型：

- `Arko007/fact-check1-v1`
- `divyanshu-chauhan-7786/fake-news-roberta`
- `google/vit-base-patch16-224-in21k`
- `IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment`

如果服务器网络较差，可以提前准备模型缓存，或把 `HF_ENDPOINT` 改成你们可用的镜像地址。

## 7. 建议

- 正式公网部署时，建议再加一层服务器级 `Nginx` 和 HTTPS
- 如果要绑定域名，可以把域名解析到这台服务器，再让外层 `Nginx` 反代到 `APP_PORT`
- 如果模型推理负载较高，建议使用更高配置服务器，必要时加 GPU
