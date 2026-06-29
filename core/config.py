import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./knowledge_base/chromadb")
    PROJECT_NAME = os.getenv("PROJECT_NAME", "NexBIM Multi-Agent System")
    VERSION = os.getenv("VERSION", "1.0.0")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", 120))

config = Config()