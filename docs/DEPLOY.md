# CI/CD 部署指南

## 一、Gitee Actions 配置

### 1. 配置仓库秘钥

进入 Gitee 仓库 → 设置 → 安全设置 → 仓库秘钥，添加以下秘钥：

| 秘钥名称 | 说明 |
|---------|------|
| `SERVER_HOST` | 服务器IP地址 |
| `SERVER_USER` | SSH登录用户名（如ubuntu） |
| `SERVER_SSH_KEY` | SSH私钥内容（~/.ssh/id_rsa的内容） |
| `SERVER_PORT` | SSH端口（默认22） |

### 2. 生成SSH密钥对

```bash
# 在本地生成密钥对
ssh-keygen -t rsa -b 4096 -C "gitee-actions"

# 将公钥添加到服务器的 ~/.ssh/authorized_keys
cat ~/.ssh/id_rsa.pub | ssh ubuntu@your-server "cat >> ~/.ssh/authorized_keys"

# 测试SSH连接
ssh -i ~/.ssh/id_rsa ubuntu@your-server
```

---

## 二、服务器初始化

### 1. 基础环境安装

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 安装PostgreSQL 15
sudo apt install -y postgresql postgresql-contrib

# 安装Nginx
sudo apt install -y nginx

# 安装Git
sudo apt install -y git
```

### 2. 项目目录初始化

```bash
# 创建项目目录
sudo mkdir -p /opt/video-ai
sudo chown ubuntu:ubuntu /opt/video-ai

# 克隆代码
cd /opt/video-ai
git clone https://gitee.com/MaoZhiqin/video-ai.git .

# 创建Python虚拟环境
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 数据库配置

```bash
# 切换到postgres用户
sudo su - postgres

# 创建数据库和用户
psql
CREATE DATABASE video_ai;
CREATE USER video_ai_user WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE video_ai TO video_ai_user;
\q

# 退出postgres用户
exit

# 初始化数据库表
cd /opt/video-ai/backend
source venv/bin/activate
DATABASE_URL=postgresql+asyncpg://video_ai_user:your_strong_password@localhost:5432/video_ai python init_db.py
```

### 4. 配置systemd服务

```bash
# 复制服务文件
sudo cp /opt/video-ai/deploy/video-ai.service /etc/systemd/system/

# 修改服务文件中的密码和路径
sudo nano /etc/systemd/system/video-ai.service

# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务并设置开机自启
sudo systemctl enable --now video-ai

# 查看服务状态
sudo systemctl status video-ai
```

### 5. 配置Nginx

```bash
# 复制Nginx配置
sudo cp /opt/video-ai/deploy/nginx.conf /etc/nginx/sites-available/video-ai

# 修改域名配置
sudo nano /etc/nginx/sites-available/video-ai

# 启用站点
sudo ln -s /etc/nginx/sites-available/video-ai /etc/nginx/sites-enabled/

# 测试Nginx配置
sudo nginx -t

# 重载Nginx
sudo systemctl reload nginx
```

---

## 三、CI/CD 流程说明

### 触发条件
- 代码 push 到 `master` 分支
- PR 提交到 `master` 分支（仅运行测试，不部署）

### CI阶段
1. 检出最新代码
2. 安装Python依赖（缓存加速）
3. flake8代码格式检查
4. 启动PostgreSQL测试数据库
5. 初始化测试表结构
6. 运行pytest单元测试
7. 生成覆盖率报告

### CD阶段（仅master分支）
1. SSH连接到生产服务器
2. git pull拉取最新代码
3. 安装新增Python依赖
4. 执行数据库初始化/迁移
5. systemctl restart重启服务
6. curl健康检查确认服务正常

---

## 四、常用运维命令

```bash
# 查看服务日志
sudo journalctl -u video-ai -f

# 重启服务
sudo systemctl restart video-ai

# 查看Nginx访问日志
sudo tail -f /var/log/nginx/access.log

# 查看Nginx错误日志
sudo tail -f /var/log/nginx/error.log

# 手动部署（紧急情况）
cd /opt/video-ai
git pull origin master
sudo systemctl restart video-ai
```

---

## 五、故障排查

### 1. 测试失败
- 查看Actions日志，定位具体失败的测试用例
- 本地运行 `pytest tests/ -v` 复现问题
- 检查数据库连接和表结构是否正确

### 2. 部署失败
- 确认SSH秘钥配置正确
- 检查服务器磁盘空间和内存
- 查看服务日志 `journalctl -u video-ai -n 100`
- 手动执行部署脚本中的命令排查

### 3. 服务启动失败
- 检查虚拟环境路径是否正确
- 确认DATABASE_URL环境变量配置正确
- 检查端口8000是否被占用
