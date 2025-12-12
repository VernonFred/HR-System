# 🌐 Ngrok 配置记录

> **更新时间**: 2025年12月12日  
> **用途**: 临时外网测试，供HR和候选人访问

---

## 📍 当前获得的地址

| 服务 | Ngrok 地址 | 状态 | 备注 |
|------|-----------|------|------|
| **前端** | `https://linda-incorporeal-unmeaningly.ngrok-free.dev` | ✅ 已获取 | 用于HR和候选人访问 |
| **后端** | 待配置 | ⏳ 需要启动 | 执行 `ngrok http 9000` |

---

## 🚀 快速配置（3步完成）

### 第1步: 启动后端Ngrok

```bash
# 打开新终端
ngrok http 9000

# 你会看到类似输出:
# Forwarding  https://xxxxx.ngrok-free.app -> http://localhost:9000
#                          ↑
#                  记录这个地址！
```

**记录你获得的后端地址**: `_____________________`

### 第2步: 配置前端API地址

```bash
cd /Users/Python项目/HR人事/frontend

# 创建环境变量文件（替换为你实际的后端地址）
echo "VITE_API_BASE_URL=https://你的后端地址/api" > .env.development.local

# 示例:
# echo "VITE_API_BASE_URL=https://backend-abc.ngrok-free.app/api" > .env.development.local
```

### 第3步: 重启前端

```bash
# 在前端运行的终端按 Ctrl+C
# 然后重新启动
npm run dev
```

---

## ✅ 验证配置

### 1. 访问前端

```
打开浏览器: https://linda-incorporeal-unmeaningly.ngrok-free.dev
```

- 首次访问会显示 "Visit Site" 按钮 → 点击继续
- 登录页面 → 输入 `admin` / `admin123`
- 如果能成功登录 → ✅ 配置正确！

### 2. 如果无法登录，检查：

```bash
# 检查后端是否运行
curl http://localhost:9000/docs

# 检查前端环境变量
cd /Users/Python项目/HR人事/frontend
cat .env.development.local

# 应该显示:
# VITE_API_BASE_URL=https://你的后端地址/api
```

---

## 📱 给HR的测试链接

### 系统访问

```
🌐 访问地址: https://linda-incorporeal-unmeaningly.ngrok-free.dev

👤 测试账号:
用户名: admin
密码: admin123

📝 使用步骤:
1. 打开链接，点击 "Visit Site"
2. 登录系统
3. 创建测评、生成二维码
4. 用手机扫码测试答题
```

### 测评链接格式

```
示例: https://linda-incorporeal-unmeaningly.ngrok-free.dev/assessment/ABC123

说明:
- HR在系统中创建测评后，会自动生成这个链接
- 链接和二维码会自动使用当前域名
- 候选人可以直接扫码或点击链接答题
```

---

## ⚠️ 重要提示

### 限制

- ❌ **地址会变**: 每次重启 ngrok，地址都不一样
- ❌ **有请求限制**: 免费版每分钟40个请求
- ❌ **不能长期使用**: 仅用于临时测试

### 适用场景

- ✅ 临时给HR测试（1-2天）
- ✅ 远程演示（几小时）
- ✅ 小规模测试（5-10人）

### 如果需要长期使用

建议申请公司正式域名，部署到生产服务器。

---

## 🔧 完整服务启动清单

### 检查清单

- [ ] 后端服务已启动（终端1）
  ```bash
  cd /Users/Python项目/HR人事/backend
  export PATH="$HOME/.local/bin:$PATH"
  poetry shell
  uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
  ```

- [ ] 后端Ngrok已启动（终端2）
  ```bash
  ngrok http 9000
  # 记录地址: https://________.ngrok-free.app
  ```

- [ ] 前端已配置后端地址（终端3）
  ```bash
  cd /Users/Python项目/HR人事/frontend
  echo "VITE_API_BASE_URL=https://后端地址/api" > .env.development.local
  npm run dev
  ```

- [x] 前端Ngrok已启动（已完成）
  ```
  地址: https://linda-incorporeal-unmeaningly.ngrok-free.dev
  ```

---

## 📞 故障排查

### 问题1: 前端访问显示 "无法连接到服务器"

**原因**: 前端没有正确配置后端Ngrok地址

**解决**:
```bash
cd /Users/Python项目/HR人事/frontend
cat .env.development.local  # 检查配置
# 确保是: VITE_API_BASE_URL=https://你的后端地址/api
```

### 问题2: 登录后显示 CORS 错误

**原因**: 后端CORS配置没有包含Ngrok域名

**解决**: 后端代码已经配置了 `allow_origins=["*"]`，应该不会有此问题。如果出现，检查后端日志。

### 问题3: Ngrok 显示 "ERR_NGROK_108"

**原因**: Ngrok账户限制或网络问题

**解决**:
```bash
# 重新登录 ngrok
ngrok config add-authtoken YOUR_TOKEN

# 重启 ngrok
ngrok http 5173
```

---

## 📝 配置记录表

| 时间 | 前端地址 | 后端地址 | 状态 | 备注 |
|------|---------|---------|------|------|
| 2025-12-12 | https://linda-incorporeal-unmeaningly.ngrok-free.dev | 待配置 | 进行中 | 给HR测试 |
| | | | | |
| | | | | |

---

## 相关文档

- [本地开发与测试部署指南](./docs/本地开发与测试部署指南.md)
- [项目交付指南](./docs/项目交付指南.md)

