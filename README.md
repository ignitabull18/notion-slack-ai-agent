# Notion-Slack AI Agent

AI-powered integration between Notion and Slack using the Agno framework for intelligent task management, knowledge synchronization, and workflow automation.

## Overview

This system creates a seamless bridge between Notion and Slack, allowing teams to:
- Manage Notion tasks directly from Slack using natural language
- Automatically sync Notion updates to relevant Slack channels
- Query Notion knowledge bases through conversational AI
- Execute complex multi-step workflows across both platforms

## Architecture

The system leverages:
- **Agno Framework**: For AI agent orchestration and multi-agent coordination
- **Hybrid Memory**: Combining Supabase (structured) and Qdrant (vector) storage
- **Real-time Webhooks**: For instant synchronization between platforms
- **Secure API Gateway**: With rate limiting and authentication

## Key Features

### 🤖 Intelligent Agent System
- Natural language understanding for complex queries
- Context-aware responses using hybrid memory
- Multi-agent coordination for specialized tasks
- Persistent conversation history

### 📝 Notion Integration
- Create, update, and query Notion databases
- Real-time page change notifications
- Bulk operations and workflow automation
- Semantic search across workspaces

### 💬 Slack Integration
- Slash commands for quick actions
- Thread-aware conversations
- Channel-specific notifications
- Interactive message components

### 🔒 Enterprise Security
- OAuth 2.0 authentication
- Role-based access control
- Audit logging and compliance
- PII filtering and data encryption

## Quick Start

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Notion Integration Token
- Slack App Credentials
- OpenAI/Claude API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ignitabull18/notion-slack-ai-agent.git
cd notion-slack-ai-agent
```

2. Copy environment template:
```bash
cp .env.template .env
```

3. Configure your credentials in `.env`

4. Install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

5. Run with Docker:
```bash
docker-compose up -d
```

## Usage Examples

### Slack Commands
```
/task Create a new project proposal in Notion
/query What are our Q4 objectives?
/sync Enable real-time updates for #product channel
```

### Python SDK
```python
from src.agents import NotionSlackAgent

agent = NotionSlackAgent()
response = await agent.process_request(
    "Create a task for the marketing team about the new campaign"
)
```

## Documentation

- [Setup Guide](docs/setup_guide.md)
- [API Reference](docs/api_reference.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## Implementation Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Foundation Setup | 6 days | Environment, API configuration, database schema |
| Core Agent Development | 14 days | Basic agent, Notion/Slack tools, memory system |
| Integration Layer | 15 days | Webhooks, event queue, auth, error handling |
| Advanced Features | 19 days | Multi-agent patterns, workflows, optimizations |
| Production Ready | 10 days | Monitoring, deployment, security, documentation |

**Total Timeline**: ~64 days (9 weeks)

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@your-domain.com
- 💬 Slack: [Join our community](https://your-slack-invite-link)
- 📚 Documentation: [docs.your-domain.com](https://docs.your-domain.com)

## Acknowledgments

- [Agno Framework](https://github.com/agno-ai/agno) for agent orchestration
- [Notion API](https://developers.notion.com) for workspace integration
- [Slack API](https://api.slack.com) for messaging platform