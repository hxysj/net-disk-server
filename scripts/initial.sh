#!/bin/bash

# 设置项目根目录路径
PROJECT_DIR=$(pwd)

# 查找所有应用的 migrations 目录并删除 initial 文件
find $PROJECT_DIR -path "*/migrations/0001_initial.py" -type f -exec rm -f {} \;

echo "所有 initial 文件已删除"

python manage.py makemigrations
python manage.py migrate

echo "初始化仓库成功！"

python manage.py loaddata utils/initial_data.json
