"""
Repository pattern implementation for database operations.
"""
from typing import List, Optional, Dict, Any, Generic, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime, timedelta
import logging

from .database import Base
from .schemas import EventType, EventStatus, WorkflowType

logger = logging.getLogger(__name__)

# Generic type for models
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, model: type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """Get multiple records with pagination and filters."""
        query = db.query(self.model)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        if hasattr(obj_in, 'model_dump'):
            obj_data = obj_in.model_dump()
        else:
            obj_data = obj_in.dict()
        
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Update an existing record."""
        if hasattr(obj_in, 'model_dump'):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        if hasattr(db_obj, 'updated_at'):
            db_obj.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, id: int) -> Optional[ModelType]:
        """Delete a record by ID."""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def count(self, db: Session, **filters) -> int:
        """Count records with optional filters."""
        query = db.query(self.model)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        return query.count()

class AgentSessionRepository(BaseRepository):
    """Repository for agent session operations."""
    
    def __init__(self):
        from .models import AgentSessionModel
        super().__init__(AgentSessionModel)
    
    def get_by_session_id(self, db: Session, session_id: str) -> Optional[ModelType]:
        """Get session by session_id."""
        return db.query(self.model).filter(
            self.model.session_id == session_id
        ).first()
    
    def get_active_sessions(self, db: Session) -> List[ModelType]:
        """Get all active sessions."""
        return db.query(self.model).filter(
            self.model.is_active == True
        ).all()
    
    def get_user_sessions(
        self, 
        db: Session, 
        user_id: str, 
        limit: int = 10
    ) -> List[ModelType]:
        """Get recent sessions for a user."""
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).order_by(desc(self.model.last_activity)).limit(limit).all()
    
    def cleanup_inactive_sessions(
        self, 
        db: Session, 
        hours: int = 24
    ) -> int:
        """Clean up sessions inactive for specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        count = db.query(self.model).filter(
            self.model.last_activity < cutoff_time,
            self.model.is_active == True
        ).count()
        
        db.query(self.model).filter(
            self.model.last_activity < cutoff_time,
            self.model.is_active == True
        ).update({"is_active": False})
        
        db.commit()
        return count
    
    def update_activity(self, db: Session, session_id: str) -> Optional[ModelType]:
        """Update last activity timestamp for a session."""
        session = self.get_by_session_id(db, session_id)
        if session:
            session.last_activity = datetime.utcnow()
            db.commit()
            db.refresh(session)
        return session

class WorkflowConfigRepository(BaseRepository):
    """Repository for workflow configuration operations."""
    
    def __init__(self):
        from .models import WorkflowConfigModel
        super().__init__(WorkflowConfigModel)
    
    def get_by_type(
        self, 
        db: Session, 
        workflow_type: WorkflowType
    ) -> List[ModelType]:
        """Get workflows by type."""
        return db.query(self.model).filter(
            self.model.workflow_type == workflow_type
        ).all()
    
    def get_active_workflows(self, db: Session) -> List[ModelType]:
        """Get all active workflows."""
        return db.query(self.model).filter(
            self.model.is_active == True
        ).all()
    
    def get_scheduled_workflows(self, db: Session) -> List[ModelType]:
        """Get workflows that have schedule configuration."""
        return db.query(self.model).filter(
            self.model.is_active == True,
            self.model.schedule_config.isnot(None)
        ).all()
    
    def update_execution_stats(
        self, 
        db: Session, 
        workflow_id: int, 
        success: bool = True
    ) -> Optional[ModelType]:
        """Update execution statistics for a workflow."""
        workflow = self.get(db, workflow_id)
        if workflow:
            workflow.last_executed = datetime.utcnow()
            workflow.execution_count += 1
            db.commit()
            db.refresh(workflow)
        return workflow

class EventLogRepository(BaseRepository):
    """Repository for event log operations."""
    
    def __init__(self):
        from .models import EventLogModel
        super().__init__(EventLogModel)
    
    def get_by_event_type(
        self, 
        db: Session, 
        event_type: EventType,
        limit: int = 100
    ) -> List[ModelType]:
        """Get events by type."""
        return db.query(self.model).filter(
            self.model.event_type == event_type
        ).order_by(desc(self.model.timestamp)).limit(limit).all()
    
    def get_by_session(
        self, 
        db: Session, 
        session_id: str,
        limit: int = 100
    ) -> List[ModelType]:
        """Get events for a session."""
        return db.query(self.model).filter(
            self.model.session_id == session_id
        ).order_by(desc(self.model.timestamp)).limit(limit).all()
    
    def get_by_user(
        self, 
        db: Session, 
        user_id: str,
        limit: int = 100
    ) -> List[ModelType]:
        """Get events for a user."""
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).order_by(desc(self.model.timestamp)).limit(limit).all()
    
    def get_failed_events(
        self, 
        db: Session,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ModelType]:
        """Get failed events."""
        query = db.query(self.model).filter(
            self.model.status == EventStatus.FAILED
        )
        
        if since:
            query = query.filter(self.model.timestamp >= since)
        
        return query.order_by(desc(self.model.timestamp)).limit(limit).all()
    
    def get_events_by_date_range(
        self,
        db: Session,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[EventType]] = None
    ) -> List[ModelType]:
        """Get events within a date range."""
        query = db.query(self.model).filter(
            and_(
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date
            )
        )
        
        if event_types:
            query = query.filter(self.model.event_type.in_(event_types))
        
        return query.order_by(desc(self.model.timestamp)).all()
    
    def get_performance_stats(
        self,
        db: Session,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance statistics."""
        query = db.query(self.model)
        
        if since:
            query = query.filter(self.model.timestamp >= since)
        
        events = query.all()
        
        if not events:
            return {}
        
        # Calculate statistics
        total_events = len(events)
        successful_events = len([e for e in events if e.status == EventStatus.COMPLETED])
        failed_events = len([e for e in events if e.status == EventStatus.FAILED])
        
        processing_times = [
            e.processing_time_ms for e in events 
            if e.processing_time_ms is not None
        ]
        
        stats = {
            "total_events": total_events,
            "successful_events": successful_events,
            "failed_events": failed_events,
            "success_rate": successful_events / total_events if total_events > 0 else 0,
        }
        
        if processing_times:
            stats.update({
                "avg_processing_time_ms": sum(processing_times) / len(processing_times),
                "min_processing_time_ms": min(processing_times),
                "max_processing_time_ms": max(processing_times),
            })
        
        # Event type breakdown
        event_type_counts = {}
        for event in events:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        stats["event_type_breakdown"] = event_type_counts
        
        return stats
    
    def cleanup_old_events(
        self, 
        db: Session, 
        days: int = 30
    ) -> int:
        """Clean up events older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        count = db.query(self.model).filter(
            self.model.timestamp < cutoff_date
        ).count()
        
        db.query(self.model).filter(
            self.model.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        return count

class UserMappingRepository(BaseRepository):
    """Repository for user mapping operations."""
    
    def __init__(self):
        from .models import UserMappingModel
        super().__init__(UserMappingModel)
    
    def get_by_slack_user_id(
        self, 
        db: Session, 
        slack_user_id: str
    ) -> Optional[ModelType]:
        """Get user mapping by Slack user ID."""
        return db.query(self.model).filter(
            self.model.slack_user_id == slack_user_id
        ).first()
    
    def get_by_notion_user_id(
        self, 
        db: Session, 
        notion_user_id: str
    ) -> Optional[ModelType]:
        """Get user mapping by Notion user ID."""
        return db.query(self.model).filter(
            self.model.notion_user_id == notion_user_id
        ).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[ModelType]:
        """Get user mapping by email."""
        return db.query(self.model).filter(
            self.model.email == email
        ).first()
    
    def get_active_users(self, db: Session) -> List[ModelType]:
        """Get all active user mappings."""
        return db.query(self.model).filter(
            self.model.is_active == True
        ).all()
    
    def update_last_seen(
        self, 
        db: Session, 
        slack_user_id: str
    ) -> Optional[ModelType]:
        """Update last seen timestamp for a user."""
        user = self.get_by_slack_user_id(db, slack_user_id)
        if user:
            user.last_seen = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user
    
    def search_users(
        self, 
        db: Session, 
        query: str,
        limit: int = 20
    ) -> List[ModelType]:
        """Search users by display name or email."""
        search_pattern = f"%{query}%"
        return db.query(self.model).filter(
            or_(
                self.model.display_name.ilike(search_pattern),
                self.model.email.ilike(search_pattern)
            ),
            self.model.is_active == True
        ).limit(limit).all()

# Repository instances (can be imported directly)
agent_session_repo = AgentSessionRepository()
workflow_config_repo = WorkflowConfigRepository()
event_log_repo = EventLogRepository()
user_mapping_repo = UserMappingRepository()
