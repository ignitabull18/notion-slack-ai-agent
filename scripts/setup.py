"""
Setup script for initializing the Notion-Slack AI Agent.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any
import json
import secrets

def print_banner():
    """Print setup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                 Notion-Slack AI Agent Setup                 ║
║                                                              ║
║  This script will help you set up the development           ║
║  environment and configuration for the AI agent.           ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ is required. Current version:", sys.version)
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")

def check_dependencies():
    """Check if required system dependencies are available."""
    dependencies = {
        "git": "Git is required for version control",
        "docker": "Docker is optional but recommended for deployment",
        "postgresql": "PostgreSQL is optional (SQLite can be used for development)"
    }
    
    for cmd, description in dependencies.items():
        if shutil.which(cmd):
            print(f"✅ {cmd} is available")
        else:
            if cmd == "docker" or cmd == "postgresql":
                print(f"⚠️  {cmd} not found - {description}")
            else:
                print(f"❌ {cmd} not found - {description}")
                if cmd == "git":
                    print("Please install Git and try again.")
                    sys.exit(1)

def create_virtual_environment():
    """Create and activate virtual environment."""
    print("\n📦 Setting up virtual environment...")
    
    if not os.path.exists("venv"):
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            sys.exit(1)
    else:
        print("✅ Virtual environment already exists")
    
    # Get activation command
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate"
    else:
        activate_cmd = "source venv/bin/activate"
    
    print(f"\n💡 To activate the virtual environment, run:")
    print(f"   {activate_cmd}")

def install_dependencies():
    """Install Python dependencies."""
    print("\n📥 Installing Python dependencies...")
    
    venv_python = get_venv_python()
    
    try:
        # Upgrade pip first
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install dependencies
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def get_venv_python():
    """Get path to Python executable in virtual environment."""
    if sys.platform == "win32":
        return os.path.join("venv", "Scripts", "python.exe")
    else:
        return os.path.join("venv", "bin", "python")

def create_env_file():
    """Create .env file from template."""
    print("\n⚙️  Creating environment configuration...")
    
    env_template_path = ".env.template"
    env_path = ".env"
    
    if not os.path.exists(env_template_path):
        print(f"❌ Template file {env_template_path} not found")
        return
    
    if os.path.exists(env_path):
        response = input(f"{env_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("⚠️  Skipping .env file creation")
            return
    
    # Read template
    with open(env_template_path, 'r') as f:
        content = f.read()
    
    # Generate secure keys
    api_secret_key = secrets.token_urlsafe(32)
    
    # Replace placeholders
    replacements = {
        "your-secret-key-here": api_secret_key,
        "https://your-domain.com": "http://localhost:8000"
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Created {env_path}")
    print("\n⚠️  IMPORTANT: Please edit .env and add your API keys:")
    print("   - OPENAI_API_KEY (required)")
    print("   - NOTION_INTEGRATION_TOKEN (required)")
    print("   - SLACK_BOT_TOKEN (required)")
    print("   - SLACK_SIGNING_SECRET (required)")

def setup_database():
    """Set up the database."""
    print("\n🗄️  Setting up database...")
    
    # Ask user about database preference
    print("Choose database option:")
    print("1. SQLite (recommended for development)")
    print("2. PostgreSQL (recommended for production)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        # SQLite setup
        db_url = "sqlite:///./agent.db"
        print("✅ Configured for SQLite")
    elif choice == "2":
        # PostgreSQL setup
        print("Please ensure PostgreSQL is running and create a database.")
        db_name = input("Database name (default: notion_slack_agent): ").strip() or "notion_slack_agent"
        db_user = input("Database user (default: postgres): ").strip() or "postgres"
        db_password = input("Database password: ").strip()
        db_host = input("Database host (default: localhost): ").strip() or "localhost"
        db_port = input("Database port (default: 5432): ").strip() or "5432"
        
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"✅ Configured for PostgreSQL: {db_name}")
    else:
        print("Invalid choice, defaulting to SQLite")
        db_url = "sqlite:///./agent.db"
    
    # Update .env file with database URL
    update_env_file("DATABASE_URL", db_url)

def update_env_file(key: str, value: str):
    """Update a key in the .env file."""
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    
    lines = []
    updated = False
    
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}\n")
                updated = True
            else:
                lines.append(line)
    
    if not updated:
        lines.append(f"{key}={value}\n")
    
    with open(env_path, 'w') as f:
        f.writelines(lines)

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = [
        "logs",
        "data",
        "backups",
        "tmp"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created {directory}/")

def initialize_database():
    """Initialize the database tables."""
    print("\n🏗️  Initializing database tables...")
    
    venv_python = get_venv_python()
    
    try:
        # Run database initialization
        subprocess.run([
            venv_python, "-c",
            "from src.models.database import init_database, create_tables; init_database(); create_tables()"
        ], check=True)
        print("✅ Database tables created")
    except subprocess.CalledProcessError:
        print("⚠️  Failed to initialize database (this is normal if API keys aren't configured yet)")

def create_sample_config():
    """Create sample configuration files."""
    print("\n📄 Creating sample configuration...")
    
    # Create a sample workflow configuration
    sample_workflow = {
        "name": "Daily Digest Workflow",
        "description": "Send daily digest of Notion updates to Slack",
        "schedule": "0 9 * * *",  # 9 AM daily
        "source": {
            "type": "notion",
            "database_id": "YOUR_NOTION_DATABASE_ID"
        },
        "target": {
            "type": "slack",
            "channel_id": "YOUR_SLACK_CHANNEL_ID"
        },
        "filters": {
            "last_edited_time": {
                "after": "{{yesterday}}"
            }
        }
    }
    
    with open("sample_workflow.json", "w") as f:
        json.dump(sample_workflow, f, indent=2)
    
    print("✅ Created sample_workflow.json")

def print_next_steps():
    """Print next steps for the user."""
    next_steps = """

🎉 Setup complete! Next steps:

1. Edit .env file with your API keys:
   - Get OpenAI API key from: https://platform.openai.com/api-keys
   - Create Notion integration: https://developers.notion.com
   - Create Slack app: https://api.slack.com/apps

2. Test the setup:
   source venv/bin/activate  # Windows: venv\\Scripts\\activate
   python -m src.main

3. Run tests:
   pytest

4. Start development:
   - Check out the README.md for detailed usage instructions
   - Explore the example configurations
   - Set up your Notion databases and Slack channels

5. Deploy to production:
   - Use Docker: docker-compose up -d
   - Or follow the deployment guide in docs/

📚 Documentation:
   - API docs: http://localhost:8000/docs (when running)
   - README: ./README.md
   - Deployment guide: ./deployment-guide.md

❓ Need help?
   - GitHub Issues: https://github.com/ignitabull18/notion-slack-ai-agent/issues
   - Documentation: Check the /docs folder

Happy coding! 🚀
    """
    print(next_steps)

def main():
    """Main setup function."""
    print_banner()
    
    # Checks
    check_python_version()
    check_dependencies()
    
    # Environment setup
    create_virtual_environment()
    
    # Ask if user wants to install dependencies
    install_deps = input("\nInstall Python dependencies? (Y/n): ").strip().lower()
    if install_deps != 'n':
        install_dependencies()
    
    # Configuration
    create_env_file()
    setup_database()
    create_directories()
    create_sample_config()
    
    # Database initialization
    init_db = input("\nInitialize database tables? (Y/n): ").strip().lower()
    if init_db != 'n':
        initialize_database()
    
    # Finish
    print_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
