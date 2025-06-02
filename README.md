# Notion-Slack AI Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Agno Framework](https://img.shields.io/badge/Agno-Framework-purple.svg)](https://github.com/agno-ai/agno)

An intelligent AI-powered integration system that bridges Notion and Slack, enabling seamless workflow automation, real-time synchronization, and natural language task management using the Agno framework.

## 🚀 Features

### Core Capabilities
- **🤖 AI-Powered Agent**: Leverages Agno framework with OpenAI/Claude models for intelligent task processing
- **🔄 Real-time Sync**: Bidirectional synchronization between Notion databases and Slack channels
- **📝 Smart Task Management**: Create, update, and track tasks through natural language commands
- **🔗 Webhook Integration**: Real-time event processing from both Notion and Slack
- **🛠️ Advanced Workflows**: Automated daily digests, status updates, and smart routing
- **📊 Monitoring & Analytics**: Comprehensive logging, metrics, and performance tracking

### Integration Features
- **Notion Tools**: Complete CRUD operations, database queries, page management
- **Slack Tools**: Message handling, channel management, user interactions
- **Workflow Automation**: Custom workflows for team collaboration
- **Security**: API key authentication, rate limiting, input validation
- **Scalability**: Docker support, database persistence, monitoring

## 🏗️ Architecture

The system follows a modular, agent-based architecture:

```
┌─────────────────┐    ┌─────────────────┐
│   Slack Users   │    │  Notion Users   │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│   Slack API     │    │   Notion API    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     ▼
          ┌─────────────────┐
          │ Webhook Handler │
          └─────────┬───────┘
                    ▼
          ┌─────────────────┐
          │ Agno AI Agent   │
          └─────────┬───────┘
                    ▼
          ┌─────────────────┐
          │   Database &    │
          │   Vector Store  │
          └─────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.9+
- Docker and Docker Compose (optional)
- PostgreSQL 12+ (or SQLite for development)
- Redis 6+ (for caching and queues)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/ignitabull18/notion-slack-ai-agent.git
   cd notion-slack-ai-agent
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.template .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the application**
   ```bash
   python -m src.main
   ```

### Docker Setup

```bash
# Start with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t notion-slack-agent .
docker run -p 8000:8000 --env-file .env notion-slack-agent
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# AI Model Configuration
OPENAI_API_KEY=sk-...
MODEL_PROVIDER=openai
MODEL_ID=gpt-4

# Notion Integration
NOTION_INTEGRATION_TOKEN=secret_...
NOTION_WORKSPACE_ID=...
NOTION_WEBHOOK_SECRET=...

# Slack Integration
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/notion_slack_agent
REDIS_URL=redis://localhost:6379

# Security
API_SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://your-domain.com

# Monitoring
LOG_LEVEL=INFO
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

### Notion Setup

1. **Create Integration**
   - Go to [Notion Developers](https://developers.notion.com)
   - Create new integration with read/write permissions
   - Copy the integration token

2. **Share Databases**
   - Open target Notion databases
   - Click "Share" → "Invite"
   - Add your integration

3. **Configure Webhooks** (Optional)
   ```bash
   curl -X POST https://api.notion.com/v1/webhooks \
     -H "Authorization: Bearer $NOTION_INTEGRATION_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "event_types": ["page.created", "page.updated"],
       "url": "https://your-domain.com/webhook/notion"
     }'
   ```

### Slack Setup

1. **Create Slack App**
   - Go to [Slack API](https://api.slack.com/apps)
   - Create new app with the following permissions:
     - `channels:read`, `chat:write`, `commands`
     - `app_mentions:read`, `channels:history`

2. **Configure Slash Commands**
   - `/task` - Create tasks in Notion
   - `/query` - Search Notion knowledge base
   - `/sync` - Trigger manual synchronization

3. **Install to Workspace**
   - Install app to your Slack workspace
   - Copy bot token, app token, and signing secret

## 🎯 Usage

### Basic Commands

#### Slack Slash Commands

```bash
# Create a task
/task Implement user authentication system

# Search Notion
/query project roadmap

# Trigger sync
/sync
```

#### API Endpoints

```bash
# Send message to agent
POST /api/v1/chat
{
  "message": "Create a task for code review",
  "channel_id": "C1234567890"
}

# Create Notion page
POST /api/v1/notion/pages
{
  "database_id": "abc123...",
  "title": "New Project",
  "properties": {...}
}

# Send Slack message
POST /api/v1/slack/messages
{
  "channel": "#general",
  "text": "Hello from the agent!"
}
```

### Advanced Workflows

#### Daily Digest
```python
from src.tools.workflow_tools import WorkflowTools

workflow = WorkflowTools()
await workflow.daily_digest(
    database_id="your-database-id",
    channel_id="C1234567890",
    lookback_hours=24
)
```

#### Status Update Automation
```python
await workflow.status_update_workflow(
    page_id="page-id",
    new_status="In Progress",
    channel_id="C1234567890"
)
```

#### Smart Channel Routing
```python
routing_rules = [
    {
        "keywords": ["bug", "error", "issue"],
        "target_channel": "#dev-alerts",
        "template": "🐛 Bug Report: {}"
    }
]

await workflow.smart_channel_routing(
    message="Found a critical bug in login",
    source_channel="#general",
    routing_rules=routing_rules
)
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_tools.py
```

## 📊 Monitoring

### Health Checks
- **Application**: `GET /health`
- **Detailed**: `GET /api/v1/health`

### Metrics
- **Prometheus**: Available at `:9090/metrics`
- **Custom Metrics**: Request counts, response times, API calls
- **Dashboards**: Grafana-compatible metrics

### Logging
- **Structured Logging**: JSON format with context
- **Security Events**: Authentication, rate limiting
- **API Calls**: Performance and error tracking

## 🔧 Development

### Project Structure
```
src/
├── agents/          # AI agent implementations
├── api/            # FastAPI routes and middleware
├── integrations/   # Webhook handlers
├── models/         # Database models and schemas
├── services/       # Business logic and monitoring
├── tools/          # Notion, Slack, and workflow tools
└── utils/          # Utilities and helpers
```

### Adding New Tools
```python
from agno.tools import Tool

class CustomTool(Tool):
    def custom_operation(self, param: str) -> dict:
        # Implement your custom logic
        return {"success": True, "result": param}
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- **API Reference**: Available at `/docs` (Swagger UI)
- **Deployment Guide**: See `deployment-guide.md`
- **Architecture**: Detailed system design in `/docs`

## 🚀 Deployment

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] SSL certificates installed
- [ ] Monitoring and logging enabled
- [ ] Backup strategy implemented
- [ ] Security audit completed

### Scaling

- **Horizontal**: Load balancer + multiple instances
- **Database**: Read replicas for heavy read workloads
- **Caching**: Redis for frequent queries
- **Queues**: Celery for background tasks

## 🛡️ Security

- **API Authentication**: Bearer tokens and API keys
- **Input Validation**: Comprehensive sanitization
- **Rate Limiting**: Per-user and per-endpoint limits
- **HTTPS**: Required for all endpoints
- **Secrets Management**: Environment variables only

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/ignitabull18/notion-slack-ai-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ignitabull18/notion-slack-ai-agent/discussions)
- **Documentation**: [Wiki](https://github.com/ignitabull18/notion-slack-ai-agent/wiki)

## 🙏 Acknowledgments

- [Agno Framework](https://github.com/agno-ai/agno) - AI agent framework
- [Notion API](https://developers.notion.com) - Workspace integration
- [Slack API](https://api.slack.com) - Team communication
- [FastAPI](https://fastapi.tiangolo.com) - Web framework

---

**Built with ❤️ using the Agno AI Agent Framework**
