"""
Repository classes for database operations.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime, timedelta

from .schemas import (
    User, UserPreferences, AgentSession, NotionDatabase,
    SlackWorkspace, WorkflowExecution, APIKey, SystemMetrics
)

class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, db: Session, model_class):
        self.db = db
        self.model = model_class
    
    def get_by_id(self, id: int):
        """Get record by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100):
        """Get all records with pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, **kwargs):
        """Create new record."""
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, id: int, **kwargs):
        """Update record by ID."""
        obj = self.get_by_id(id)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(obj)
        return obj
    
    def delete(self, id: int):
        """Delete record by ID."""
        obj = self.get_by_id(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj

class UserRepository(BaseRepository):
    """Repository for User operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_slack_id(self, slack_user_id: str, slack_team_id: str) -> Optional[User]:
        """Get user by Slack user ID and team ID."""
        return self.db.query(User).filter(
            and_(
                User.slack_user_id == slack_user_id,
                User.slack_team_id == slack_team_id
            )
        ).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_active_users(self) -> List[User]:
        """Get all active users."""
        return self.db.query(User).filter(User.is_active == True).all()
    
    def get_admins(self) -> List[User]:
        """Get all admin users."""
        return self.db.query(User).filter(
            and_(User.is_admin == True, User.is_active == True)
        ).all()
    
    def update_last_seen(self, user_id: int):
        """Update user's last seen timestamp."""
        user = self.get_by_id(user_id)
        if user:
            user.last_seen_at = datetime.utcnow()
            self.db.commit()
        return user
    
    def search_users(self, query: str) -> List[User]:
        """Search users by name or email."""
        return self.db.query(User).filter(
            or_(
                User.display_name.ilike(f"%{query}%"),
                User.real_name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).all()

class AgentSessionRepository(BaseRepository):
    """Repository for AgentSession operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, AgentSession)
    
    def get_by_session_id(self, session_id: str) -> Optional[AgentSession]:
        """Get session by session ID."""
        return self.db.query(AgentSession).filter(
            AgentSession.session_id == session_id
        ).first()
    
    def get_user_sessions(self, user_id: int, active_only: bool = True) -> List[AgentSession]:
        """Get all sessions for a user."""
        query = self.db.query(AgentSession).filter(AgentSession.user_id == user_id)
        if active_only:
            query = query.filter(AgentSession.is_active == True)
        return query.order_by(desc(AgentSession.last_activity)).all()
    
    def get_channel_sessions(self, channel_id: str, active_only: bool = True) -> List[AgentSession]:
        """Get all sessions for a Slack channel."""
        query = self.db.query(AgentSession).filter(AgentSession.channel_id == channel_id)
        if active_only:
            query = query.filter(AgentSession.is_active == True)
        return query.order_by(desc(AgentSession.last_activity)).all()
    
    def update_activity(self, session_id: str, message_data: Dict[str, Any] = None):
        """Update session activity and optionally add message."""
        session = self.get_by_session_id(session_id)
        if session:
            session.last_activity = datetime.utcnow()
            if message_data:
                session.messages.append(message_data)
                session.total_messages += 1
            self.db.commit()
        return session
    
    def cleanup_inactive_sessions(self, inactive_hours: int = 24):
        """Mark sessions as inactive after specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=inactive_hours)
        self.db.query(AgentSession).filter(
            and_(
                AgentSession.last_activity < cutoff_time,
                AgentSession.is_active == True
            )
        ).update({"is_active": False})
        self.db.commit()

class NotionDatabaseRepository(BaseRepository):
    """Repository for NotionDatabase operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, NotionDatabase)
    
    def get_by_database_id(self, database_id: str) -> Optional[NotionDatabase]:
        """Get database by Notion database ID."""
        return self.db.query(NotionDatabase).filter(
            NotionDatabase.database_id == database_id
        ).first()
    
    def get_by_slack_channel(self, channel_id: str) -> List[NotionDatabase]:
        """Get databases associated with a Slack channel."""
        return self.db.query(NotionDatabase).filter(
            NotionDatabase.slack_channel_id == channel_id
        ).all()
    
    def get_auto_sync_databases(self) -> List[NotionDatabase]:
        """Get databases with auto-sync enabled."""
        return self.db.query(NotionDatabase).filter(
            NotionDatabase.auto_sync_enabled == True
        ).all()
    
    def get_user_databases(self, user_id: int) -> List[NotionDatabase]:
        """Get databases accessible to a user."""
        return self.db.query(NotionDatabase).filter(
            or_(
                NotionDatabase.created_by_user_id == user_id,
                NotionDatabase.is_public == True,
                NotionDatabase.allowed_users.contains([user_id])
            )
        ).all()
    
    def update_sync_time(self, database_id: str):
        """Update last sync timestamp."""
        db_record = self.get_by_database_id(database_id)
        if db_record:
            db_record.last_sync_at = datetime.utcnow()
            self.db.commit()
        return db_record

class WorkflowExecutionRepository(BaseRepository):
    """Repository for WorkflowExecution operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, WorkflowExecution)
    
    def get_by_execution_id(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by execution ID."""
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.execution_id == execution_id
        ).first()
    
    def get_user_executions(self, user_id: int, limit: int = 50) -> List[WorkflowExecution]:
        """Get executions for a user."""
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.user_id == user_id
        ).order_by(desc(WorkflowExecution.created_at)).limit(limit).all()
    
    def get_by_status(self, status: str) -> List[WorkflowExecution]:
        """Get executions by status."""
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.status == status
        ).all()
    
    def get_running_executions(self) -> List[WorkflowExecution]:
        """Get currently running executions."""
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.status.in_(["pending", "running"])
        ).all()
    
    def update_status(self, execution_id: str, status: str, 
                     error_message: str = None, output_data: Dict = None):
        """Update execution status."""
        execution = self.get_by_execution_id(execution_id)
        if execution:
            execution.status = status
            execution.updated_at = datetime.utcnow()
            
            if status == "completed":
                execution.completed_at = datetime.utcnow()
                if execution.started_at:
                    duration = execution.completed_at - execution.started_at
                    execution.duration_ms = int(duration.total_seconds() * 1000)
            
            if error_message:
                execution.error_message = error_message
            
            if output_data:
                execution.output_data = output_data
            
            self.db.commit()
        return execution
    
    def get_execution_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get execution statistics for the last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total_executions = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.created_at >= start_date
        ).count()
        
        successful_executions = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.created_at >= start_date,
                WorkflowExecution.status == "completed"
            )
        ).count()
        
        failed_executions = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.created_at >= start_date,
                WorkflowExecution.status == "failed"
            )
        ).count()
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0
        }

class SlackWorkspaceRepository(BaseRepository):
    """Repository for SlackWorkspace operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, SlackWorkspace)
    
    def get_by_team_id(self, team_id: str) -> Optional[SlackWorkspace]:
        """Get workspace by team ID."""
        return self.db.query(SlackWorkspace).filter(
            SlackWorkspace.team_id == team_id
        ).first()
    
    def update_activity(self, team_id: str):
        """Update workspace last activity."""
        workspace = self.get_by_team_id(team_id)
        if workspace:
            workspace.last_active_at = datetime.utcnow()
            self.db.commit()
        return workspace
    
    def increment_usage(self, team_id: str):
        """Increment daily API usage."""
        workspace = self.get_by_team_id(team_id)
        if workspace:
            # Reset counter if it's a new day
            if workspace.last_usage_reset.date() < datetime.utcnow().date():
                workspace.current_daily_usage = 0
                workspace.last_usage_reset = datetime.utcnow()
            
            workspace.current_daily_usage += 1
            self.db.commit()
        return workspace

class APIKeyRepository(BaseRepository):
    """Repository for API key operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, APIKey)
    
    def get_by_key_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by key ID."""
        return self.db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    def get_active_keys(self) -> List[APIKey]:
        """Get all active API keys."""
        now = datetime.utcnow()
        return self.db.query(APIKey).filter(
            and_(
                APIKey.is_active == True,
                or_(APIKey.expires_at.is_(None), APIKey.expires_at > now)
            )
        ).all()
    
    def update_usage(self, key_id: str):
        """Update API key usage statistics."""
        api_key = self.get_by_key_id(key_id)
        if api_key:
            # Reset hourly counter if needed
            if api_key.last_hour_reset < datetime.utcnow() - timedelta(hours=1):
                api_key.current_hour_requests = 0
                api_key.last_hour_reset = datetime.utcnow()
            
            api_key.current_hour_requests += 1
            api_key.total_requests += 1
            api_key.last_used_at = datetime.utcnow()
            self.db.commit()
        return api_key

class SystemMetricsRepository(BaseRepository):
    """Repository for system metrics operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, SystemMetrics)
    
    def record_metric(self, name: str, value: int, metric_type: str = "counter", 
                     tags: Dict[str, Any] = None):
        """Record a system metric."""
        metric = SystemMetrics(
            metric_name=name,
            metric_type=metric_type,
            value=value,
            tags=tags or {}
        )
        self.db.add(metric)
        self.db.commit()
        return metric
    
    def get_metrics_by_name(self, name: str, hours: int = 24) -> List[SystemMetrics]:
        """Get metrics by name for the last N hours."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(SystemMetrics).filter(
            and_(
                SystemMetrics.metric_name == name,
                SystemMetrics.timestamp >= start_time
            )
        ).order_by(asc(SystemMetrics.timestamp)).all()
    
    def get_metric_summary(self, name: str, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated metric summary."""
        metrics = self.get_metrics_by_name(name, hours)
        if not metrics:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values)
        }
    
    def cleanup_old_metrics(self, days: int = 30):
        """Remove metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        self.db.query(SystemMetrics).filter(
            SystemMetrics.timestamp < cutoff_date
        ).delete()
        self.db.commit()
