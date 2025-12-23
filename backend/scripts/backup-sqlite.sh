#!/bin/bash

###############################################################################
# QZ·TalentLens SQLite 数据库备份脚本
# 用途：自动备份 SQLite 数据库文件
# 使用：./backup-sqlite.sh [backup_dir]
###############################################################################

set -e  # 遇到错误立即退出

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DB_FILE="$PROJECT_ROOT/backend/hr.db"
BACKUP_DIR="${1:-/backup/talentlens}"  # 默认备份目录
RETENTION_DAYS=30  # 保留天数

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印信息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查数据库文件是否存在
if [ ! -f "$DB_FILE" ]; then
    log_error "数据库文件不存在: $DB_FILE"
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名
BACKUP_FILE="$BACKUP_DIR/hr.db.$(date +%Y%m%d_%H%M%S)"

# 执行备份
log_info "开始备份数据库..."
log_info "源文件: $DB_FILE"
log_info "目标文件: $BACKUP_FILE"

cp "$DB_FILE" "$BACKUP_FILE"

# 验证备份
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "备份成功! 文件大小: $BACKUP_SIZE"
else
    log_error "备份失败!"
    exit 1
fi

# 清理旧备份（保留指定天数）
log_info "清理超过 $RETENTION_DAYS 天的旧备份..."
find "$BACKUP_DIR" -name "hr.db.*" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

OLD_BACKUP_COUNT=$(find "$BACKUP_DIR" -name "hr.db.*" | wc -l)
log_info "当前保留备份数量: $OLD_BACKUP_COUNT"

# 列出最近的备份
log_info "最近的5个备份："
ls -lht "$BACKUP_DIR/hr.db."* 2>/dev/null | head -5 || log_warn "暂无其他备份文件"

log_info "备份完成! ✓"

# 返回备份文件路径（供其他脚本使用）
echo "$BACKUP_FILE"

