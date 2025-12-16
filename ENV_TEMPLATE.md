# Environment Variables Template

Create a `.env` file in the project root with these variables:

```bash
# ============================================================================
# MYCA MAS Environment Configuration
# ============================================================================

# Environment
MAS_ENV=development
DEBUG_MODE=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://mas:maspassword@postgres:5432/mas
POSTGRES_USER=mas
POSTGRES_PASSWORD=maspassword
POSTGRES_DB=mas

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379

# Qdrant
QDRANT_URL=http://qdrant:6333

# LLM Providers
LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=your-key-here
LOCAL_LLM_ENABLED=false
LOCAL_LLM_BASE_URL=http://litellm:4000

# Security
SECRET_KEY=your-secret-key-here
APPROVAL_REQUIRED=false

# See full template in UPGRADE_PLAN.md
```
