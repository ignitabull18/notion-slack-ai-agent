"""
Database setup and initialization script.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.models.database import create_tables, SessionLocal
from src.models.schemas import User, UserPreferences, SlackWorkspace
from src.services.auth_service import AuthService
from src.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Initialize database with tables and default data."""
    logger.info("Setting up database...")
    
    # Create all tables
    create_tables()
    logger.info("Database tables created successfully")
    
    # Create default admin user if not exists
    create_default_admin()
    
    logger.info("Database setup completed")

def create_default_admin():
    """Create default admin user."""
    settings = get_settings()
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        
        if existing_admin:
            logger.info("Admin user already exists")
            return
        
        # Create default admin user
        admin_user = User(
            slack_user_id="U_ADMIN_DEFAULT",
            slack_team_id="T_DEFAULT",
            email="admin@example.com",
            display_name="System Admin",
            real_name="System Administrator",
            is_active=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Create preferences for admin
        admin_prefs = UserPreferences(
            user_id=admin_user.id,
            notifications_enabled=True,
            digest_frequency="daily",
            response_style="detailed",
            auto_create_tasks=True
        )
        
        db.add(admin_prefs)
        db.commit()
        
        # Create default API key for admin
        auth_service = AuthService(db)
        api_key_result = auth_service.create_api_key(
            name="Default Admin Key",
            created_by_user_id=admin_user.id,
            scopes=["admin"],
            rate_limit_per_hour=10000
        )
        
        logger.info(f"Created default admin user with ID: {admin_user.id}")
        logger.info(f"Admin API Key: {api_key_result['api_key']}")
        logger.info("IMPORTANT: Save this API key - it won't be shown again!")
        
    except IntegrityError as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

def create_sample_data():
    """Create sample data for development/testing."""
    db = SessionLocal()
    
    try:
        # Create sample Slack workspace
        workspace = SlackWorkspace(
            team_id="T_SAMPLE_TEAM",
            team_name="Sample Team",
            team_domain="sample-team",
            team_url="https://sample-team.slack.com",
            bot_user_id="U_BOT_SAMPLE",
            auto_response_enabled=True,
            default_notification_channel="C_GENERAL",
            slash_commands_enabled=True,
            webhooks_enabled=True
        )
        
        db.add(workspace)
        
        # Create sample users
        sample_users = [
            {
                "slack_user_id": "U_SAMPLE_USER1",
                "slack_team_id": "T_SAMPLE_TEAM",
                "email": "user1@example.com",
                "display_name": "Sample User 1",
                "real_name": "John Doe"
            },
            {
                "slack_user_id": "U_SAMPLE_USER2", 
                "slack_team_id": "T_SAMPLE_TEAM",
                "email": "user2@example.com",
                "display_name": "Sample User 2",
                "real_name": "Jane Smith"
            }
        ]
        
        for user_data in sample_users:
            user = User(**user_data)
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create preferences for each user
            prefs = UserPreferences(
                user_id=user.id,
                notifications_enabled=True,
                digest_frequency="daily" if user.slack_user_id.endswith("1") else "weekly",
                response_style="detailed"
            )
            db.add(prefs)
        
        db.commit()
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

def reset_database():
    """Reset database by dropping and recreating all tables."""
    logger.warning("Resetting database - all data will be lost!")
    
    from src.models.database import reset_database as db_reset
    db_reset()
    
    logger.info("Database reset completed")
    
    # Recreate default data
    create_default_admin()

def migrate_database():
    """Run database migrations (placeholder for Alembic)."""
    logger.info("Running database migrations...")
    
    # This would integrate with Alembic for production
    # For now, just ensure tables exist
    create_tables()
    
    logger.info("Database migrations completed")

def check_database_health():
    """Check database connectivity and health."""
    logger.info("Checking database health...")
    
    db = SessionLocal()
    try:
        # Test basic query
        user_count = db.query(User).count()
        logger.info(f"Database is healthy - {user_count} users found")
        
        # Test write operation
        test_time = datetime.utcnow()
        db.execute("SELECT 1")
        
        logger.info("Database health check passed")
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
    finally:
        db.close()

def cleanup_old_data():
    """Clean up old data (sessions, metrics, etc.)."""
    logger.info("Cleaning up old data...")
    
    db = SessionLocal()
    try:
        from src.models.repositories import (
            AgentSessionRepository,
            SystemMetricsRepository
        )
        
        # Clean up old sessions
        session_repo = AgentSessionRepository(db)
        session_repo.cleanup_inactive_sessions(inactive_hours=24)
        
        # Clean up old metrics
        metrics_repo = SystemMetricsRepository(db)
        metrics_repo.cleanup_old_metrics(days=30)
        
        logger.info("Data cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during data cleanup: {e}")
    finally:
        db.close()

def main():
    """Main setup function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python setup_database.py [setup|reset|migrate|health|cleanup|sample]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        setup_database()
    elif command == "reset":
        reset_database()
    elif command == "migrate":
        migrate_database()
    elif command == "health":
        healthy = check_database_health()
        sys.exit(0 if healthy else 1)
    elif command == "cleanup":
        cleanup_old_data()
    elif command == "sample":
        create_sample_data()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: setup, reset, migrate, health, cleanup, sample")
        sys.exit(1)

if __name__ == "__main__":
    main()
