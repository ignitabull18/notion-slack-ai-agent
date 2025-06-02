# Quick Start Guide

Get the Notion-Slack AI Agent up and running in minutes!

## 🚀 1-Minute Setup

```bash
# Clone the repository
git clone https://github.com/ignitabull18/notion-slack-ai-agent.git
cd notion-slack-ai-agent

# Run the setup script
python scripts/setup.py

# Edit your API keys in .env
nano .env  # or code .env

# Start the agent
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m src.main
```

That's it! Your agent will be running at `http://localhost:8000`

## 📋 Prerequisites

- **Python 3.9+** 
- **API Keys** (get these first):
  - [OpenAI API Key](https://platform.openai.com/api-keys)
  - [Notion Integration Token](https://developers.notion.com)
  - [Slack Bot Token](https://api.slack.com/apps)

## 🔧 Configuration

### Required Environment Variables

Edit `.env` file with your credentials:

```bash
# AI Model
OPENAI_API_KEY=sk-your-openai-key-here
MODEL_ID=gpt-4

# Notion Integration
NOTION_INTEGRATION_TOKEN=secret_your-notion-token
NOTION_WORKSPACE_ID=your-workspace-id

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret

# Database (SQLite for development)
DATABASE_URL=sqlite:///./agent.db
```

### Notion Setup

1. **Create Integration**
   - Go to [developers.notion.com](https://developers.notion.com)
   - Click "New integration"
   - Give it a name: "AI Agent"
   - Select capabilities: Read, Update, Insert content
   - Copy the **Integration Token**

2. **Share Databases**
   - Open your Notion databases
   - Click "Share" → "Invite"
   - Add your integration by name

### Slack Setup

1. **Create App**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - App name: "Notion AI Assistant"

2. **Configure Permissions**
   ```
   OAuth Scopes (Bot Token):
   - channels:read
   - chat:write
   - commands
   - app_mentions:read
   ```

3. **Add Slash Commands**
   ```
   /task - Create tasks in Notion
   /query - Search Notion knowledge base
   /sync - Trigger synchronization
   ```

4. **Install to Workspace**
   - Copy **Bot User OAuth Token** (starts with `xoxb-`)
   - Copy **Signing Secret**

## 🎮 Usage Examples

### Basic API Usage

```bash
# Health check
curl http://localhost:8000/health

# Chat with agent
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a task for project planning"}'
```

### Slack Commands

```bash
# In Slack, try these commands:
/task Implement user authentication system
/query project roadmap
/sync
```

### Workflow Automation

```python
from src.tools.workflow_tools import WorkflowTools

# Sync Notion to Slack
workflow = WorkflowTools()
await workflow.sync_notion_to_slack(
    database_id="your-database-id",
    channel_id="C1234567890"
)

# Daily digest
await workflow.daily_digest(
    database_id="your-database-id", 
    channel_id="C1234567890"
)
```

## 🧪 Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_notion_tools.py

# Run with coverage
pytest --cov=src
```

## 🐳 Docker Deployment

```bash
# Quick start with Docker Compose
docker-compose up -d

# Or build manually
docker build -t notion-slack-agent .
docker run -p 8000:8000 --env-file .env notion-slack-agent
```

## 📊 Monitoring

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:9090/metrics (if Prometheus enabled)
- **Logs**: Check `logs/` directory

## 🔍 Troubleshooting

### Common Issues

**❌ "Invalid API key"**
```bash
# Check your .env file
cat .env | grep API_KEY

# Verify OpenAI key is valid
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

**❌ "Notion integration not found"**
- Ensure you've shared databases with your integration
- Check the integration token in `.env`
- Verify workspace ID is correct

**❌ "Slack webhook verification failed"**
- Check `SLACK_SIGNING_SECRET` in `.env`
- Ensure webhook URL points to your server
- Use ngrok for local development: `ngrok http 8000`

**❌ "Database connection error"**
```bash
# For SQLite (development)
rm agent.db  # Reset database
python -c "from src.models.database import create_tables; create_tables()"

# For PostgreSQL (production)
createdb notion_slack_agent
psql notion_slack_agent -c "SELECT 1;"  # Test connection
```

### Getting Help

- **Logs**: Check `logs/app.log` for detailed error information
- **Debug Mode**: Set `DEBUG=true` in `.env` for verbose logging
- **GitHub Issues**: [Report bugs or request features](https://github.com/ignitabull18/notion-slack-ai-agent/issues)

## 🚀 Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Set up Workflows**: Check `sample_workflow.json`
3. **Customize Agents**: Modify agent instructions in `src/main.py`
4. **Add Tools**: Create custom tools in `src/tools/`
5. **Deploy to Production**: Follow the deployment guide

## 💡 Pro Tips

- **Use ngrok** for local Slack webhook testing: `ngrok http 8000`
- **Set up monitoring** early with Prometheus + Grafana
- **Create dedicated Notion workspace** for testing
- **Use environment-specific** `.env` files (`.env.dev`, `.env.prod`)
- **Regular backups** of your database and configurations

## 📚 Learn More

- [Full Documentation](README.md)
- [API Reference](http://localhost:8000/docs)
- [Deployment Guide](deployment-guide.md)
- [Architecture Overview](docs/architecture.md)
- [Contributing Guidelines](CONTRIBUTING.md)

---

**Happy automating! 🎉**

If you found this helpful, please star the repository and share it with others!
