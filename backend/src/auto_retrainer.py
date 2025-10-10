"""
Automated Model Retraining System
Provides safe, automated retraining capabilities with validation and rollback.
"""

import logging
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrainTrigger(Enum):
    """Reasons for triggering retraining"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DATA_DRIFT = "data_drift"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    TIME_BASED = "time_based"

class RetrainStatus(Enum):
    """Status of retraining process"""
    PENDING = "pending"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class RetrainingJob:
    """Represents a retraining job"""
    job_id: str
    region: str
    service: str
    target: str
    trigger: RetrainTrigger
    status: RetrainStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    old_model_path: Optional[str] = None
    new_model_path: Optional[str] = None
    backup_path: Optional[str] = None
    validation_metrics: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None

@dataclass
class RetrainingConfig:
    """Configuration for retraining system"""
    # Performance thresholds
    mae_degradation_threshold: float = 1.2  # 20% worse than baseline
    validation_improvement_threshold: float = 0.95  # Must be at least 5% better
    
    # Safety checks
    min_training_data_days: int = 30
    validation_data_days: int = 7
    max_retrain_attempts: int = 3
    
    # Time limits
    retrain_timeout_minutes: int = 30
    validation_timeout_minutes: int = 10
    
    # Backup settings
    keep_backup_models: int = 5
    backup_retention_days: int = 30

class AutoRetrainer:
    """
    Automated model retraining system with safety checks and validation
    """
    
    def __init__(self, models_path: Optional[Path] = None, data_path: Optional[Path] = None):
        """
        Initialize AutoRetrainer
        
        Args:
            models_path: Path to models directory
            data_path: Path to data directory
        """
        # Set up paths
        if models_path is None:
            models_path = Path(__file__).parent.parent / "models"
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data"
        
        self.models_path = Path(models_path)
        self.data_path = Path(data_path)
        self.backup_path = self.models_path / "backups"
        self.jobs_path = self.models_path / "retraining_jobs"
        
        # Create directories
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.jobs_path.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = RetrainingConfig()
        
        # Active jobs tracking
        self.active_jobs: Dict[str, RetrainingJob] = {}
        
        logger.info(f"AutoRetrainer initialized with models at {self.models_path}")
    
    def generate_job_id(self, region: str, service: str, target: str) -> str:
        """Generate unique job ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"retrain_{region}_{service}_{target}_{timestamp}"
    
    def should_retrain(self, region: str, service: str, target: str) -> Tuple[bool, List[RetrainTrigger]]:
        """
        Determine if model should be retrained based on monitoring data
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            
        Returns:
            Tuple of (should_retrain, list_of_triggers)
        """
        from .model_monitor import get_model_monitor
        
        try:
            monitor = get_model_monitor()
            status = monitor.monitor_model(region, service, target)
            
            if not status:
                logger.warning(f"No monitoring status available for {region}/{service}/{target}")
                return False, []
            
            triggers = []
            
            # Check performance degradation
            perf = status.performance_metrics
            mae_ratio = perf.current_mae / perf.baseline_mae
            
            if mae_ratio > self.config.mae_degradation_threshold:
                triggers.append(RetrainTrigger.PERFORMANCE_DEGRADATION)
                logger.info(f"Performance degradation detected: MAE ratio {mae_ratio:.2f}")
            
            # Check data drift
            if status.drift_metrics and status.drift_metrics.drift_flag:
                triggers.append(RetrainTrigger.DATA_DRIFT)
                logger.info(f"Data drift detected: score {status.drift_metrics.drift_score:.3f}")
            
            # Check time-based retraining
            if status.days_since_last_retrain > 90:  # 3 months
                triggers.append(RetrainTrigger.TIME_BASED)
                logger.info(f"Time-based trigger: {status.days_since_last_retrain} days since last retrain")
            
            should_retrain = len(triggers) > 0
            return should_retrain, triggers
            
        except Exception as e:
            logger.error(f"Error checking retrain conditions for {region}/{service}/{target}: {e}")
            return False, []
    
    def create_retraining_job(self, region: str, service: str, target: str, 
                             trigger: RetrainTrigger) -> RetrainingJob:
        """
        Create a new retraining job
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            trigger: Reason for retraining
            
        Returns:
            RetrainingJob object
        """
        job_id = self.generate_job_id(region, service, target)
        
        job = RetrainingJob(
            job_id=job_id,
            region=region,
            service=service,
            target=target,
            trigger=trigger,
            status=RetrainStatus.PENDING,
            created_at=datetime.now()
        )
        
        # Save job
        self.save_job(job)
        self.active_jobs[job_id] = job
        
        logger.info(f"Created retraining job {job_id} for {region}/{service}/{target} (trigger: {trigger.value})")
        return job
    
    def save_job(self, job: RetrainingJob) -> None:
        """Save job to persistent storage"""
        job_file = self.jobs_path / f"{job.job_id}.json"
        
        # Convert datetime objects to strings for JSON serialization
        job_dict = asdict(job)
        for key, value in job_dict.items():
            if isinstance(value, datetime):
                job_dict[key] = value.isoformat() if value else None
            elif isinstance(value, (RetrainTrigger, RetrainStatus)):
                job_dict[key] = value.value
        
        with open(job_file, 'w') as f:
            json.dump(job_dict, f, indent=2)
    
    def load_job(self, job_id: str) -> Optional[RetrainingJob]:
        """Load job from persistent storage"""
        job_file = self.jobs_path / f"{job_id}.json"
        
        if not job_file.exists():
            return None
        
        try:
            with open(job_file, 'r') as f:
                job_dict = json.load(f)
            
            # Convert string dates back to datetime objects
            for key in ['created_at', 'started_at', 'completed_at']:
                if job_dict.get(key):
                    job_dict[key] = datetime.fromisoformat(job_dict[key])
            
            # Convert enum strings back to enums
            job_dict['trigger'] = RetrainTrigger(job_dict['trigger'])
            job_dict['status'] = RetrainStatus(job_dict['status'])
            
            return RetrainingJob(**job_dict)
            
        except Exception as e:
            logger.error(f"Error loading job {job_id}: {e}")
            return None
    
    def backup_current_model(self, region: str, service: str, target: str, job_id: str) -> Optional[str]:
        """
        Create backup of current model before retraining
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            job_id: Associated job ID
            
        Returns:
            Path to backup file or None if backup failed
        """
        try:
            # Find current model
            arima_dir = self.models_path / "arima"
            model_file = arima_dir / f"{region}_{service}_{target}_arima.pkl"
            
            if not model_file.exists():
                logger.warning(f"No existing model found at {model_file}")
                return None
            
            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{region}_{service}_{target}_backup_{timestamp}_{job_id}.pkl"
            backup_path = self.backup_path / backup_filename
            
            shutil.copy2(model_file, backup_path)
            logger.info(f"Model backed up to {backup_path}")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error backing up model for {region}/{service}/{target}: {e}")
            return None
    
    def load_training_data(self, region: str, service: str, target: str) -> Optional[pd.DataFrame]:
        """
        Load training data for model retraining
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            
        Returns:
            Training DataFrame or None if loading failed
        """
        try:
            # Load processed data
            data_file = self.data_path / "processed" / "feature_engineered.csv"
            
            if not data_file.exists():
                logger.error(f"Training data not found at {data_file}")
                return None
            
            df = pd.read_csv(data_file)
            
            # Filter for specific model
            df = df[
                (df['region'] == region) & 
                (df['service'] == service)
            ].copy()
            
            if df.empty:
                logger.error(f"No training data available for {region}/{service}")
                return None
            
            # Check data sufficiency
            days_of_data = len(df)
            if days_of_data < self.config.min_training_data_days:
                logger.error(f"Insufficient training data: {days_of_data} days (minimum: {self.config.min_training_data_days})")
                return None
            
            logger.info(f"Loaded {len(df)} rows of training data for {region}/{service}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading training data for {region}/{service}/{target}: {e}")
            return None
    
    def train_new_model(self, region: str, service: str, target: str, data: pd.DataFrame) -> Optional[str]:
        """
        Train new ARIMA model
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            data: Training data
            
        Returns:
            Path to new model file or None if training failed
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
            import warnings
            warnings.filterwarnings('ignore')
            
            # Prepare target data
            if target not in data.columns:
                logger.error(f"Target column '{target}' not found in data")
                return None
            
            target_data = data[target].dropna()
            
            if len(target_data) < self.config.min_training_data_days:
                logger.error(f"Insufficient non-null target data: {len(target_data)} points")
                return None
            
            # Train ARIMA model
            logger.info(f"Training ARIMA model for {region}/{service}/{target}")
            
            # Use default ARIMA(1,1,1) for simplicity
            # In production, you might want to do grid search
            model = ARIMA(target_data, order=(1, 1, 1))
            fitted_model = model.fit()
            
            # Save new model
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_model_filename = f"{region}_{service}_{target}_arima_new_{timestamp}.pkl"
            arima_dir = self.models_path / "arima"
            arima_dir.mkdir(exist_ok=True)
            new_model_path = arima_dir / new_model_filename
            
            # Save the fitted model
            joblib.dump(fitted_model, new_model_path)
            
            logger.info(f"New model trained and saved to {new_model_path}")
            return str(new_model_path)
            
        except Exception as e:
            logger.error(f"Error training new model for {region}/{service}/{target}: {e}")
            return None
    
    def validate_new_model(self, region: str, service: str, target: str, 
                          new_model_path: str, old_model_path: str) -> Dict[str, float]:
        """
        Validate new model against old model
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            new_model_path: Path to new model
            old_model_path: Path to old model
            
        Returns:
            Dictionary with validation metrics
        """
        try:
            # Load validation data (last N days)
            data = self.load_training_data(region, service, target)
            if data is None:
                return {"error": "No validation data available"}
            
            # Use last N days for validation
            validation_days = self.config.validation_data_days
            validation_data = data.tail(validation_days)[target].dropna()
            
            if len(validation_data) < validation_days:
                return {"error": f"Insufficient validation data: {len(validation_data)} points"}
            
            # Load models
            try:
                new_model = joblib.load(new_model_path)
                old_model = joblib.load(old_model_path) if Path(old_model_path).exists() else None
            except Exception as e:
                return {"error": f"Error loading models: {e}"}
            
            # Calculate validation metrics
            metrics = {}
            
            # Generate forecasts for validation period
            forecast_horizon = len(validation_data)
            
            try:
                new_forecast = new_model.forecast(steps=forecast_horizon)
                new_mae = abs(validation_data.values - new_forecast).mean()
                metrics["new_model_mae"] = float(new_mae)
            except Exception as e:
                metrics["new_model_mae"] = float('inf')
                logger.error(f"Error forecasting with new model: {e}")
            
            if old_model is not None:
                try:
                    old_forecast = old_model.forecast(steps=forecast_horizon)
                    old_mae = abs(validation_data.values - old_forecast).mean()
                    metrics["old_model_mae"] = float(old_mae)
                    
                    # Calculate improvement ratio
                    if old_mae > 0:
                        improvement_ratio = new_mae / old_mae
                        metrics["improvement_ratio"] = float(improvement_ratio)
                    else:
                        metrics["improvement_ratio"] = 1.0
                        
                except Exception as e:
                    metrics["old_model_mae"] = float('inf')
                    metrics["improvement_ratio"] = 0.0
                    logger.error(f"Error forecasting with old model: {e}")
            else:
                metrics["old_model_mae"] = float('inf')
                metrics["improvement_ratio"] = 0.0
            
            # Additional validation metrics
            metrics["validation_data_points"] = len(validation_data)
            metrics["validation_period_days"] = validation_days
            
            logger.info(f"Validation completed for {region}/{service}/{target}: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error validating model for {region}/{service}/{target}: {e}")
            return {"error": str(e)}
    
    def deploy_new_model(self, region: str, service: str, target: str, new_model_path: str) -> bool:
        """
        Deploy new model by replacing the current one
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            new_model_path: Path to new model
            
        Returns:
            True if deployment successful, False otherwise
        """
        try:
            # Target deployment path
            arima_dir = self.models_path / "arima"
            deployment_path = arima_dir / f"{region}_{service}_{target}_arima.pkl"
            
            # Copy new model to deployment location
            shutil.copy2(new_model_path, deployment_path)
            logger.info(f"New model deployed to {deployment_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deploying new model for {region}/{service}/{target}: {e}")
            return False
    
    def rollback_model(self, region: str, service: str, target: str, backup_path: str, reason: str) -> bool:
        """
        Rollback to previous model version
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            backup_path: Path to backup model
            reason: Reason for rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            if not Path(backup_path).exists():
                logger.error(f"Backup model not found at {backup_path}")
                return False
            
            # Restore from backup
            arima_dir = self.models_path / "arima"
            deployment_path = arima_dir / f"{region}_{service}_{target}_arima.pkl"
            
            shutil.copy2(backup_path, deployment_path)
            logger.info(f"Model rolled back from {backup_path} due to: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back model for {region}/{service}/{target}: {e}")
            return False
    
    def run_retraining_job(self, job_id: str) -> bool:
        """
        Execute a retraining job
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job completed successfully, False otherwise
        """
        job = self.active_jobs.get(job_id) or self.load_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        try:
            # Update job status
            job.status = RetrainStatus.RUNNING
            job.started_at = datetime.now()
            self.save_job(job)
            
            logger.info(f"Starting retraining job {job_id} for {job.region}/{job.service}/{job.target}")
            
            # Step 1: Backup current model
            backup_path = self.backup_current_model(job.region, job.service, job.target, job_id)
            if backup_path:
                job.backup_path = backup_path
                job.old_model_path = str(self.models_path / "arima" / f"{job.region}_{job.service}_{job.target}_arima.pkl")
                self.save_job(job)
            
            # Step 2: Load training data
            data = self.load_training_data(job.region, job.service, job.target)
            if data is None:
                raise Exception("Failed to load training data")
            
            # Step 3: Train new model
            new_model_path = self.train_new_model(job.region, job.service, job.target, data)
            if not new_model_path:
                raise Exception("Failed to train new model")
            
            job.new_model_path = new_model_path
            self.save_job(job)
            
            # Step 4: Validate new model
            job.status = RetrainStatus.VALIDATING
            self.save_job(job)
            
            validation_metrics = self.validate_new_model(
                job.region, job.service, job.target,
                new_model_path, job.old_model_path or ""
            )
            
            job.validation_metrics = validation_metrics
            self.save_job(job)
            
            # Step 5: Check if new model is better
            if "error" in validation_metrics:
                raise Exception(f"Validation failed: {validation_metrics['error']}")
            
            improvement_ratio = validation_metrics.get("improvement_ratio", 1.0)
            
            if improvement_ratio <= self.config.validation_improvement_threshold:
                # New model is better or acceptable
                if self.deploy_new_model(job.region, job.service, job.target, new_model_path):
                    job.status = RetrainStatus.COMPLETED
                    job.completed_at = datetime.now()
                    logger.info(f"Retraining job {job_id} completed successfully")
                else:
                    raise Exception("Failed to deploy new model")
            else:
                # New model is worse, rollback
                rollback_reason = f"New model performance worse: improvement ratio {improvement_ratio:.3f}"
                if backup_path and self.rollback_model(job.region, job.service, job.target, backup_path, rollback_reason):
                    job.status = RetrainStatus.ROLLED_BACK
                    job.rollback_reason = rollback_reason
                    job.completed_at = datetime.now()
                    logger.warning(f"Retraining job {job_id} rolled back: {rollback_reason}")
                else:
                    raise Exception("Failed to rollback model")
            
            self.save_job(job)
            return True
            
        except Exception as e:
            # Handle job failure
            job.status = RetrainStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            self.save_job(job)
            
            logger.error(f"Retraining job {job_id} failed: {e}")
            
            # Attempt rollback if backup exists
            if job.backup_path and Path(job.backup_path).exists():
                logger.info(f"Attempting rollback for failed job {job_id}")
                self.rollback_model(job.region, job.service, job.target, job.backup_path, f"Job failed: {e}")
            
            return False
    
    def retrain_model(self, region: str, service: str, target: str, trigger: RetrainTrigger = RetrainTrigger.MANUAL) -> str:
        """
        Start retraining process for a specific model
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            trigger: Trigger reason
            
        Returns:
            Job ID for tracking
        """
        # Create retraining job
        job = self.create_retraining_job(region, service, target, trigger)
        
        # Run the job
        success = self.run_retraining_job(job.job_id)
        
        if not success:
            logger.error(f"Retraining failed for {region}/{service}/{target}")
        
        return job.job_id
    
    def check_all_models_for_retraining(self) -> List[str]:
        """
        Check all models and start retraining for those that need it
        
        Returns:
            List of job IDs for started retraining jobs
        """
        from .model_manager import get_model_manager
        
        try:
            model_manager = get_model_manager()
            available_combinations = model_manager.get_available_combinations()
            
            started_jobs = []
            
            for region, service, target in available_combinations:
                should_retrain, triggers = self.should_retrain(region, service, target)
                
                if should_retrain and triggers:
                    # Use the first trigger for job creation
                    primary_trigger = triggers[0]
                    job_id = self.retrain_model(region, service, target, primary_trigger)
                    started_jobs.append(job_id)
                    
                    logger.info(f"Started retraining for {region}/{service}/{target} due to {primary_trigger.value}")
            
            logger.info(f"Automatic retraining check completed. Started {len(started_jobs)} jobs.")
            return started_jobs
            
        except Exception as e:
            logger.error(f"Error during automatic retraining check: {e}")
            return []
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a retraining job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary or None if job not found
        """
        job = self.active_jobs.get(job_id) or self.load_job(job_id)
        if not job:
            return None
        
        job_dict = asdict(job)
        
        # Convert datetime objects to strings
        for key, value in job_dict.items():
            if isinstance(value, datetime):
                job_dict[key] = value.isoformat() if value else None
            elif isinstance(value, (RetrainTrigger, RetrainStatus)):
                job_dict[key] = value.value
        
        return job_dict
    
    def cleanup_old_backups(self) -> int:
        """
        Clean up old backup files
        
        Returns:
            Number of files cleaned up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            cleaned_count = 0
            
            for backup_file in self.backup_path.glob("*.pkl"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned up old backup: {backup_file}")
            
            logger.info(f"Cleanup completed. Removed {cleaned_count} old backup files.")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            return 0

# Global retrainer instance
_auto_retrainer = None

def get_auto_retrainer() -> AutoRetrainer:
    """Get global auto retrainer instance"""
    global _auto_retrainer
    if _auto_retrainer is None:
        _auto_retrainer = AutoRetrainer()
    return _auto_retrainer

if __name__ == "__main__":
    # Test retraining system
    retrainer = get_auto_retrainer()
    
    print("Running automatic retraining check...")
    job_ids = retrainer.check_all_models_for_retraining()
    
    if job_ids:
        print(f"Started {len(job_ids)} retraining jobs:")
        for job_id in job_ids:
            print(f"  - {job_id}")
    else:
        print("No models need retraining at this time.")