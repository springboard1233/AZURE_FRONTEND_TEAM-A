"""
Database models for forecast storage and tracking
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class ForecastRun(Base):
    """
    Metadata for each forecast generation run
    """
    __tablename__ = 'forecast_runs'
    
    run_id = Column(String(50), primary_key=True)
    model_version = Column(String(20), nullable=False)
    run_time = Column(DateTime, default=datetime.utcnow)
    run_window_start = Column(DateTime, nullable=False)
    run_window_end = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False)  # 'running', 'completed', 'failed'
    total_forecasts = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Relationship to forecasts
    forecasts = relationship("Forecast", back_populates="run")

class Forecast(Base):
    """
    Individual forecast predictions
    """
    __tablename__ = 'forecasts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), ForeignKey('forecast_runs.run_id'), nullable=False)
    region = Column(String(50), nullable=False)
    service = Column(String(50), nullable=False)
    target = Column(String(50), nullable=False)  # 'usage_cpu' or 'usage_storage'
    forecast_date = Column(DateTime, nullable=False)  # Date being predicted
    predicted_value = Column(Float, nullable=False)
    lower_ci = Column(Float, nullable=True)  # Lower confidence interval
    upper_ci = Column(Float, nullable=True)  # Upper confidence interval
    model_version = Column(String(20), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    horizon_days = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=True)
    
    # Relationship to run
    run = relationship("ForecastRun", back_populates="forecasts")

class Actual(Base):
    """
    Actual observed values for accuracy calculation
    """
    __tablename__ = 'actuals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(50), nullable=False)
    service = Column(String(50), nullable=False)
    target = Column(String(50), nullable=False)
    date = Column(DateTime, nullable=False)
    actual_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    data_source = Column(String(100), nullable=True)  # Source of actual data

class AccuracyMetric(Base):
    """
    Calculated accuracy metrics for model performance tracking
    """
    __tablename__ = 'accuracy_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(50), nullable=False)
    service = Column(String(50), nullable=False)
    target = Column(String(50), nullable=False)
    model_version = Column(String(20), nullable=False)
    metric_type = Column(String(20), nullable=False)  # 'MAE', 'MAPE', 'RMSE'
    metric_value = Column(Float, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    sample_size = Column(Integer, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

class CapacityAction(Base):
    """
    Track capacity actions taken based on recommendations
    """
    __tablename__ = 'capacity_actions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(50), nullable=False)
    service = Column(String(50), nullable=False)
    target = Column(String(50), nullable=False)
    action_type = Column(String(20), nullable=False)  # 'scale_up', 'scale_down', etc.
    recommended_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    capacity_before = Column(Float, nullable=False)
    capacity_after = Column(Float, nullable=True)
    cost_impact = Column(Float, nullable=True)
    status = Column(String(20), default='pending')  # 'pending', 'executed', 'ignored'
    notes = Column(Text, nullable=True)

class DatabaseManager:
    """
    Database connection and session management
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize database connection
        
        Args:
            database_url: SQLite database URL (default: sqlite:///data/forecasting.db)
        """
        if database_url is None:
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            os.makedirs(data_dir, exist_ok=True)
            database_url = f"sqlite:///{os.path.join(data_dir, 'forecasting.db')}"
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def close_session(self, session):
        """Close a database session"""
        session.close()

# Global database manager instance
_db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.create_tables()
    return _db_manager

def init_database():
    """Initialize database with tables"""
    db_manager = get_database_manager()
    db_manager.create_tables()
    print("Database initialized successfully")

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()