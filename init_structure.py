import os
import pathlib

# 定义前端项目的根路径
BASE_DIR = pathlib.Path("frontend/src")

# 1. 需要创建的文件夹列表
directories = [
    "api",
    "components/Charts",
    "views/user",
    "views/auditor",
    "views/admin",
    "store",
    "router"
]

# 2. 需要创建的文件列表
files = [
    "api/auth.js",
    "api/task.js",
    "api/monitor.js",
    "components/MediaViewer.vue",
    "views/Login.vue",
    "views/user/Upload.vue",
    "views/auditor/Review.vue",
    "views/admin/Dashboard.vue",
    "views/admin/UserManage.vue",
]

def create_structure():
    if not BASE_DIR.exists():
        print(f"❌ 错误: 找不到 {BASE_DIR} 目录。请确保你已经先运行了 npm create vue@latest frontend")
        return

    print(f"🚀 开始在 {BASE_DIR} 下构建目录结构...")

    # 创建文件夹
    for folder in directories:
        target_path = BASE_DIR / folder
        if not target_path.exists():
            os.makedirs(target_path)
            print(f"   📂 创建目录: {folder}")
    
    # 创建文件
    for file in files:
        target_path = BASE_DIR / file
        if not target_path.exists():
            # 创建空文件
            with open(target_path, 'w', encoding='utf-8') as f:
                # 如果是 .vue 文件，写入一个最基础的模板，防止编辑器报错
                if file.endswith('.vue'):
                    component_name = file.split('/')[-1].replace('.vue', '')
                    f.write(f"<template>\n  <div>\n    <h1>{component_name} Page</h1>\n  </div>\n</template>\n\n<script setup>\n</script>")
                else:
                    f.write("// TODO: Implement logic here")
            print(f"   📄 创建文件: {file}")
        else:
            print(f"   ⏩ 跳过已存在: {file}")

    print("\n✅ 结构构建完成！你现在可以去 frontend 目录下安装依赖了。")

if __name__ == "__main__":
    create_structure()