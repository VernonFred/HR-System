# 数据库管理脚本使用说明

## 📁 脚本列表

| 脚本 | 用途 | 使用场景 |
|------|------|----------|
| `backup-sqlite.sh` | SQLite 数据库备份 | 定期备份、迁移前备份 |
| `restore-sqlite.sh` | SQLite 数据库恢复 | 数据恢复、回滚操作 |

---

## 🔧 使用方法

### 1. 数据库备份

#### 手动备份
```bash
cd /opt/talentlens/backend/scripts
./backup-sqlite.sh
```

#### 指定备份目录
```bash
./backup-sqlite.sh /your/custom/backup/path
```

#### 定时备份（每天凌晨2点）
```bash
# 编辑 crontab
crontab -e

# 添加以下行
0 2 * * * /opt/talentlens/backend/scripts/backup-sqlite.sh /backup/talentlens >> /var/log/talentlens-backup.log 2>&1
```

### 2. 数据库恢复

#### 查看可用备份
```bash
ls -lht /backup/talentlens/hr.db.*
```

#### 恢复指定备份
```bash
cd /opt/talentlens/backend/scripts
./restore-sqlite.sh /backup/talentlens/hr.db.20251212_140530
```

#### 安全提示
- ⚠️ 恢复前会自动创建当前数据库的安全备份
- ⚠️ 建议在恢复前停止后端服务
- ⚠️ 恢复后会自动验证数据库完整性

---

## 🗄️ PostgreSQL 数据库管理

如果使用 PostgreSQL，请使用以下命令：

### 备份 PostgreSQL
```bash
# 完整备份
pg_dump -h localhost -U talentlens_user -d talentlens_prod \
    -F c -f /backup/talentlens_$(date +%Y%m%d).dump

# 仅备份数据（不含表结构）
pg_dump -h localhost -U talentlens_user -d talentlens_prod \
    --data-only -F c -f /backup/talentlens_data_$(date +%Y%m%d).dump

# 仅备份表结构（不含数据）
pg_dump -h localhost -U talentlens_user -d talentlens_prod \
    --schema-only -F c -f /backup/talentlens_schema_$(date +%Y%m%d).dump
```

### 恢复 PostgreSQL
```bash
# 完整恢复（会先删除现有数据）
pg_restore -h localhost -U talentlens_user -d talentlens_prod \
    -c /backup/talentlens_20251212.dump

# 仅恢复数据
pg_restore -h localhost -U talentlens_user -d talentlens_prod \
    --data-only /backup/talentlens_data_20251212.dump
```

---

## 📊 数据库维护

### 检查数据库大小
```bash
# SQLite
ls -lh /opt/talentlens/backend/hr.db

# PostgreSQL
psql -h localhost -U talentlens_user -d talentlens_prod \
    -c "SELECT pg_size_pretty(pg_database_size('talentlens_prod'));"
```

### 检查数据库完整性
```bash
# SQLite
sqlite3 /opt/talentlens/backend/hr.db "PRAGMA integrity_check;"

# PostgreSQL
vacuumdb -h localhost -U talentlens_user -d talentlens_prod --analyze
```

### 清理数据库（释放空间）
```bash
# SQLite
sqlite3 /opt/talentlens/backend/hr.db "VACUUM;"

# PostgreSQL
vacuumdb -h localhost -U talentlens_user -d talentlens_prod --full
```

---

## 🚨 应急处理

### 数据库损坏
```bash
# 1. 立即备份当前数据库（即使损坏）
cp /opt/talentlens/backend/hr.db /backup/hr.db.corrupted

# 2. 尝试恢复最近的备份
./restore-sqlite.sh /backup/talentlens/hr.db.YYYYMMDD_HHMMSS

# 3. 如果无备份，尝试修复（可能丢失部分数据）
sqlite3 /opt/talentlens/backend/hr.db ".recover" > /tmp/recovered.sql
sqlite3 /opt/talentlens/backend/hr.db.new < /tmp/recovered.sql
```

### 误删数据
```bash
# 1. 立即停止服务
systemctl stop talentlens-backend

# 2. 恢复最近的备份
./restore-sqlite.sh /backup/talentlens/hr.db.YYYYMMDD_HHMMSS

# 3. 启动服务
systemctl start talentlens-backend
```

---

## 📝 最佳实践

### 1. 备份策略
- ✅ 每天自动备份（凌晨2点）
- ✅ 保留最近 30 天的备份
- ✅ 重要操作前手动备份（如升级、迁移）
- ✅ 定期测试恢复流程

### 2. 监控建议
```bash
# 监控数据库文件大小
watch -n 60 'du -h /opt/talentlens/backend/hr.db'

# 监控磁盘空间
df -h /opt/talentlens
```

### 3. 安全建议
- 🔒 备份文件权限设置为 600（仅所有者可读写）
- 🔒 备份目录与数据库文件不在同一磁盘
- 🔒 定期异地备份（云存储、其他服务器）
- 🔒 加密敏感备份文件

---

## ❓ 常见问题

### Q: 备份文件可以直接使用吗？
A: 是的，SQLite 备份就是数据库文件的副本，可以直接复制使用。

### Q: 多久备份一次合适？
A: 根据数据重要性：
- 高频使用：每天1次
- 低频使用：每周1次
- 重要操作前：立即手动备份

### Q: 如何迁移到新服务器？
A: 
1. 在旧服务器备份：`./backup-sqlite.sh /tmp/backup`
2. 复制到新服务器：`scp /tmp/backup/hr.db.* newserver:/opt/talentlens/backend/hr.db`
3. 在新服务器启动服务

### Q: 如何从 SQLite 迁移到 PostgreSQL？
A: 请参考 `docs/04_部署交付文档.md` 的"数据库切换"章节。

---

## 📞 技术支持

如有疑问，请联系技术团队或查看完整文档：
- 部署文档：`docs/04_部署交付文档.md`
- 维护文档：`docs/05_后续维护文档.md`

