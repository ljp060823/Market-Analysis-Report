from langgraph.checkpoint.mysql.aio import AIOMySQLSaver
from langchain_neo4j import Neo4jGraph
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import structlog

logger = structlog.get_logger()

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class Settings(BaseSettings):
    MYSQL_URI: str = "mysql+aiomysql://user:password@localhost:3306/aether_invest"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    REDIS_URI: str = "redis://localhost:6379/0"
    BOCHA_API_KEY: str = ""
    LLM_BASE_URL: str = "http://140.210.92.250:8001/v1"

    # 正确指定你的.env绝对路径
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,  # 关闭大小写敏感
        extra="ignore", 
    )

settings = Settings()

_checkpointer_cm = None

async def get_checkpointer():
    global _checkpointer_cm
    try:
        _checkpointer_cm = AIOMySQLSaver.from_conn_string(settings.MYSQL_URI)
        checkpointer = await _checkpointer_cm.__aenter__()
        await checkpointer.setup()
        logger.info("checkpointer_initialized", message="MySQL Checkpointer 初始化成功")
        return checkpointer
    except Exception as exc:
        logger.exception("checkpointer_init_failed", error=str(exc))
        raise RuntimeError(f"MySQL Checkpointer 初始化失败: {exc}") from exc

# Neo4j 4.4.48 Graph实例（生产：连接池自动管理）
graph_db = Neo4jGraph(
    url=settings.NEO4J_URI,
    username=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD,
    database="neo4j",
    enhanced_schema=False,
)

# 初始化
# graph_db.query("""
# CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
# """)
# graph_db.query("""
# CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
# """)