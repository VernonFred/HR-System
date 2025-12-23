#!/bin/bash

###############################################################################
# QZ·TalentLens SQLite 数据库恢复脚本
# 用途：从备份文件恢复数据库
# 使用：./restore-sqlite.sh <backup_file>
###############################################################################

set -e  # 遇到错误立即退出

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DB_FILE="$PROJECT_ROOT/backend/hr.db"
BACKUP_FILE="$1"

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

# 检查参数
if [ -z "$BACKUP_FILE" ]; then
    log_error "用法: $0 <backup_file>"
    echo ""
    echo "示例:"
    echo "  $0 /backup/talentlens/hr.db.20251212_140530"
    exit 1
fi

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "备份文件不存在: $BACKUP_FILE"
    exit 1
fi

# 显示当前数据库信息
if [ -f "$DB_FILE" ]; then
    CURRENT_SIZE=$(du -h "$DB_FILE" | cut -f1)
    CURRENT_MTIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$DB_FILE" 2>/dev/null || stat -c "%y" "$DB_FILE" 2>/dev/null | cut -d. -f1)
    log_warn "当前数据库信息:"
    log_warn "  路径: $DB_FILE"
    log_warn "  大小: $CURRENT_SIZE"
    log_warn "  修改时间: $CURRENT_MTIME"
else
    log_info "当前没有数据库文件"
fi

# 显示备份文件信息
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_MTIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$BACKUP_FILE" 2>/dev/null || stat -c "%y" "$BACKUP_FILE" 2>/dev/null | cut -d. -f1)
log_info "备份文件信息:"
log_info "  路径: $BACKUP_FILE"
log_info "  大小: $BACKUP_SIZE"
log_info "  修改时间: $BACKUP_MTIME"

# 确认恢复
echo ""
log_warn "⚠️  警告：此操作将覆盖当前数据库！"
read -p "确认恢复? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log_info "已取消恢复操作"
    exit 0
fi

# 备份当前数据库（如果存在）
if [ -f "$DB_FILE" ]; then
    SAFETY_BACKUP="$DB_FILE.before_restore_$(date +%Y%m%d_%H%M%S)"
    log_info "创建安全备份: $SAFETY_BACKUP"
    cp "$DB_FILE" "$SAFETY_BACKUP"
fi

# 检查后端服务是否在运行
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    log_warn "检测到后端服务正在运行"
    log_warn "建议先停止服务: systemctl stop talentlens-backend"
    read -p "继续恢复? (yes/no): " continue_confirm
    if [ "$continue_confirm" != "yes" ]; then
        log_info "已取消恢复操作"
        exit 0
    fi
fi

# 执行恢复
log_info "开始恢复数据库..."
cp "$BACKUP_FILE" "$DB_FILE"

# 验证恢复
if [ -f "$DB_FILE" ]; then
    RESTORED_SIZE=$(du -h "$DB_FILE" | cut -f1)
    log_info "恢复成功! 文件大小: $RESTORED_SIZE"
    
    # 验证数据库完整性
    log_info "验证数据库完整性..."
    if sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_info "数据库完整性检查通过 ✓"
    else
        log_error "数据库完整性检查失败!"
        if [ -f "$SAFETY_BACKUP" ]; then
            log_warn "正在恢复安全备份..."
            cp "$SAFETY_BACKUP" "$DB_FILE"
            log_info "已恢复到操作前的状态"
        fi
        exit 1
    fi
else
    log_error "恢复失败!"
    exit 1
fi

log_info "数据库恢复完成! ✓"
log_info "如果后端服务已停止，请重新启动: systemctl start talentlens-backend"

