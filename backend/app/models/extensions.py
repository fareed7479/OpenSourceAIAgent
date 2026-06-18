import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class RepositoryMemory(Base):
    __tablename__ = "repository_memory"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=False)
    memory_type = Column(String, nullable=False)  # pattern, convention, preference, past_review, etc.
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    repository = relationship("Repository")

class RepositoryEmbedding(Base):
    __tablename__ = "repository_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    filepath = Column(String, nullable=False)
    symbol = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # list of floats
    
    created_at = Column(DateTime, default=func.now())
    
    repository = relationship("Repository")

class AgentState(Base):
    __tablename__ = "agent_states"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String, nullable=False)
    state_data = Column(JSON, default=dict)
    status = Column(String, default="idle")  # idle, busy, error, done
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    agent_run = relationship("AgentRun")

class AgentTask(Base):
    __tablename__ = "agent_tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    task_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    assignee = Column(String, nullable=False)  # agent_name
    status = Column(String, default="pending")  # pending, running, completed, failed
    result = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    agent_run = relationship("AgentRun")

class AgentPlan(Base):
    __tablename__ = "agent_plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    steps = Column(JSON, nullable=False)  # list of steps [{"step": 1, "description": "...", "status": "pending"}]
    status = Column(String, default="pending_approval")  # pending_approval, approved, rejected
    feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    agent_run = relationship("AgentRun")

class AgentReview(Base):
    __tablename__ = "agent_reviews"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pr_id = Column(String, ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False)
    reviewer_name = Column(String, nullable=False)
    report = Column(Text, nullable=False)
    score = Column(Integer, default=0)
    status = Column(String, default="passed")  # passed, failed_retry
    
    created_at = Column(DateTime, default=func.now())
    
    pull_request = relationship("PullRequest")

class RepairAttempt(Base):
    __tablename__ = "repair_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=False)
    planned_fix = Column(Text, nullable=False)
    result_logs = Column(Text, nullable=True)
    status = Column(String, default="failed")  # failed, succeeded
    
    created_at = Column(DateTime, default=func.now())
    
    agent_run = relationship("AgentRun")

class FeedbackHistory(Base):
    __tablename__ = "feedback_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)  # approve, reject, regenerate
    feedback_text = Column(Text, nullable=True)
    code_diff = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    repository = relationship("Repository")
    user = relationship("User")

class LearningSignal(Base):
    __tablename__ = "learning_signals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    signal_type = Column(String, nullable=False)  # convention, preference, review_pattern
    description = Column(Text, nullable=False)
    strength = Column(Float, default=1.0)
    
    created_at = Column(DateTime, default=func.now())
    
    repository = relationship("Repository")

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_delivery_id = Column(String, unique=True, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="received")  # received, processed, failed
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())

class CodeSearchIndex(Base):
    __tablename__ = "code_search_index"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    filepath = Column(String, nullable=False)
    symbol_name = Column(String, nullable=False, index=True)
    symbol_type = Column(String, nullable=False)  # class, function, import
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=func.now())
    
    repository = relationship("Repository")

class ImplementationIteration(Base):
    __tablename__ = "implementation_iterations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    iteration_number = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    code_diff = Column(Text, nullable=False)
    test_passed = Column(Boolean, default=False)
    test_logs = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    agent_run = relationship("AgentRun")

class QualityMetric(Base):
    __tablename__ = "quality_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    security_score = Column(Integer, default=0)
    performance_score = Column(Integer, default=0)
    maintainability_score = Column(Integer, default=0)
    style_score = Column(Integer, default=0)
    overall_score = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    
    agent_run = relationship("AgentRun")


class CodeSymbol(Base):
    __tablename__ = "code_symbols"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    filepath = Column(String, nullable=False)
    name = Column(String, nullable=False, index=True)
    symbol_type = Column(String, nullable=False)  # class, function, method, interface, route, api_handler
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    
    repository = relationship("Repository")


class CodeRelation(Base):
    __tablename__ = "code_relations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    source_file = Column(String, nullable=False)
    target_file = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)  # imports, depends_on, calls, extends
    
    repository = relationship("Repository")

