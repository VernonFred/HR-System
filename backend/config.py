"""
TalentLens 后端配置
"""
import os

class Config:
    """基础配置"""
    # DeepSeek API
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
    
    # 服务器
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    # 管理员
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'epq_admin_123')
    
    # 文件上传
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'xls', 'doc', 'docx'}
    
    @classmethod
    def init_app(cls, app):
        """初始化应用配置"""
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)

