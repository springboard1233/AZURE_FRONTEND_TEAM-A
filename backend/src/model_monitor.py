"""
Model monitoring system for Azure demand forecasting
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import statistics
import numpy as np
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from database import get_database_manager, Forecast, Actual, AccuracyMetric
from accuracy_tracker import get_accuracy_tracker
from sqlalchemy import and_, func, desc

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelHealth(Enum):
    """Model health status levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class RecommendedAction(Enum):
    """Recommended actions for model maintenance"""
    CONTINUE = "continue"
    MONITOR_CLOSELY = "monitor_closely"
    RETRAIN_SOON = "retrain_soon"
    RETRAIN_IMMEDIATELY = "retrain_immediately"
    INVESTIGATE = "investigate"

@dataclass
class ModelPerformanceMetrics:
    """Container for model performance metrics"""
    region: str
    service: str
    target: str
    model_version: str
    current_mae: float
    mae_30day_avg: float
    mae_7day_avg: float
    baseline_mae: float
    mae_trend: str  # 'improving', 'stable', 'degrading'
    sample_size: int
    data_coverage: float  # percentage of expected data points
    last_updated: datetime

@dataclass
class DriftMetrics:
    """Container for data drift detection metrics"""
    region: str
    service: str
    target: str
    drift_score: float
    drift_flag: bool
    drift_method: str  # 'ks_test', 'psi', 'js_divergence'
    reference_period_start: datetime
    reference_period_end: datetime
    current_period_start: datetime
    current_period_end: datetime
    p_value: Optional[float]

@dataclass
class ModelMonitoringStatus:
    """Complete monitoring status for a model"""
    region: str
    service: str
    target: str
    model_version: str
    health_status: ModelHealth
    recommended_action: RecommendedAction
    performance_metrics: ModelPerformanceMetrics
    drift_metrics: DriftMetrics
    days_since_last_retrain: int
    last_retrain_date: Optional[datetime]
    alert_level: str
    monitoring_summary: str

class ModelMonitor:
    """
    Comprehensive model monitoring system that tracks:
    1. Performance metrics (MAE, trends, coverage)
    2. Data drift detection
    3. Model health assessment
    4. Retraining recommendations
    """
    
    def __init__(self, baseline_file: str = None):
        """
        Initialize model monitor
        
        Args:
            baseline_file: Path to baseline metrics file
        """
        self.db_manager = get_database_manager()
        self.accuracy_tracker = get_accuracy_tracker()
        
        # Load baseline metrics
        self.baseline_file = baseline_file or "data/model_baselines.json"
        self.baselines = self._load_baselines()
        
        # Monitoring configuration
        self.config = {
            "mae_degradation_threshold": 1.2,  # 20% worse than baseline
            "drift_threshold": 0.05,  # p-value threshold for statistical tests
            "min_sample_size": 10,  # Minimum samples for reliable metrics
            "retrain_days_threshold": 30,  # Force retrain after 30 days
            "data_coverage_threshold": 0.8,  # 80% expected data coverage
            "trend_window_days": 7  # Days to calculate trends
        }
    
    def _load_baselines(self) -> Dict[str, Dict[str, float]]:
        """Load baseline performance metrics"""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Baseline file {self.baseline_file} not found, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Error loading baselines: {e}")
            return {}
    
    def _save_baselines(self):
        """Save baseline metrics to file"""
        try:
            os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baselines, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving baselines: {e}")
    
    def _get_baseline_mae(self, region: str, service: str, target: str) -> float:
        """Get baseline MAE for a model combination"""
        key = f"{region}_{service}_{target}"
        return self.baselines.get(key, {}).get('mae', 10.0)  # Default baseline
    
    def _set_baseline_mae(self, region: str, service: str, target: str, mae: float):
        """Set baseline MAE for a model combination"""
        key = f"{region}_{service}_{target}"
        if key not in self.baselines:
            self.baselines[key] = {}
        self.baselines[key]['mae'] = mae
        self.baselines[key]['updated_at'] = datetime.now().isoformat()
        self._save_baselines()
    
    def calculate_performance_metrics(self, region: str, service: str, target: str,
                                    days_back: int = 30) -> Optional[ModelPerformanceMetrics]:
        """
        Calculate comprehensive performance metrics for a model
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            days_back: Number of days to analyze
            
        Returns:
            ModelPerformanceMetrics object or None if insufficient data
        """
        session = self.db_manager.get_session()
        
        try:
            # Get accuracy metrics for the period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Query recent accuracy metrics
            recent_metrics = session.query(AccuracyMetric).filter(
                and_(
                    AccuracyMetric.region == region,
                    AccuracyMetric.service == service,
                    AccuracyMetric.target == target,
                    AccuracyMetric.metric_type == 'MAE',
                    AccuracyMetric.calculated_at >= start_date
                )
            ).order_by(AccuracyMetric.calculated_at.desc()).all()
            
            if not recent_metrics:
                logger.warning(f"No recent accuracy metrics for {region}/{service}/{target}")
                return None
            
            # Calculate current and historical MAE
            mae_values = [m.metric_value for m in recent_metrics]
            current_mae = mae_values[0] if mae_values else 0.0
            mae_30day_avg = statistics.mean(mae_values) if mae_values else 0.0
            
            # Get 7-day average
            week_ago = end_date - timedelta(days=7)
            recent_week_metrics = [m for m in recent_metrics if m.calculated_at >= week_ago]
            mae_7day_avg = statistics.mean([m.metric_value for m in recent_week_metrics]) if recent_week_metrics else mae_30day_avg
            
            # Determine trend
            if len(mae_values) >= 3:
                recent_vals = mae_values[:3]
                older_vals = mae_values[-3:] if len(mae_values) >= 6 else mae_values[3:6] if len(mae_values) > 3 else recent_vals
                
                recent_avg = statistics.mean(recent_vals)
                older_avg = statistics.mean(older_vals)
                
                if recent_avg < older_avg * 0.95:  # 5% improvement
                    mae_trend = "improving"
                elif recent_avg > older_avg * 1.05:  # 5% degradation
                    mae_trend = "degrading"
                else:
                    mae_trend = "stable"
            else:
                mae_trend = "unknown"
            
            # Get baseline MAE
            baseline_mae = self._get_baseline_mae(region, service, target)
            
            # Calculate data coverage
            expected_points = days_back  # Assume daily data
            actual_points = len(mae_values)
            data_coverage = actual_points / expected_points
            
            # Get model version
            model_version = recent_metrics[0].model_version if recent_metrics else "unknown"
            
            metrics = ModelPerformanceMetrics(
                region=region,
                service=service,
                target=target,
                model_version=model_version,
                current_mae=current_mae,
                mae_30day_avg=mae_30day_avg,
                mae_7day_avg=mae_7day_avg,
                baseline_mae=baseline_mae,
                mae_trend=mae_trend,
                sample_size=len(mae_values),
                data_coverage=data_coverage,
                last_updated=datetime.now()
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics for {region}/{service}/{target}: {e}")
            return None
        finally:
            self.db_manager.close_session(session)
    
    def detect_data_drift(self, region: str, service: str, target: str,
                         reference_days: int = 30, current_days: int = 7) -> Optional[DriftMetrics]:
        """
        Detect data drift using statistical tests
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            reference_days: Days for reference period
            current_days: Days for current period
            
        Returns:
            DriftMetrics object or None if insufficient data
        """
        session = self.db_manager.get_session()
        
        try:
            # Define time periods
            end_date = datetime.now()
            current_start = end_date - timedelta(days=current_days)
            reference_end = current_start
            reference_start = reference_end - timedelta(days=reference_days)
            
            # Get reference period actual values
            reference_actuals = session.query(Actual).filter(
                and_(
                    Actual.region == region,
                    Actual.service == service,
                    Actual.target == target,
                    Actual.date >= reference_start,
                    Actual.date < reference_end
                )
            ).all()
            
            # Get current period actual values
            current_actuals = session.query(Actual).filter(
                and_(
                    Actual.region == region,
                    Actual.service == service,
                    Actual.target == target,
                    Actual.date >= current_start,
                    Actual.date <= end_date
                )
            ).all()
            
            if len(reference_actuals) < 5 or len(current_actuals) < 3:
                logger.warning(f"Insufficient data for drift detection {region}/{service}/{target}")
                return None
            
            # Extract values
            reference_values = np.array([a.actual_value for a in reference_actuals])
            current_values = np.array([a.actual_value for a in current_actuals])
            
            # Perform Kolmogorov-Smirnov test
            from scipy import stats
            ks_statistic, p_value = stats.ks_2samp(reference_values, current_values)
            
            # Calculate drift score and flag
            drift_score = ks_statistic
            drift_flag = p_value < self.config["drift_threshold"]
            
            drift_metrics = DriftMetrics(
                region=region,
                service=service,
                target=target,
                drift_score=drift_score,
                drift_flag=drift_flag,
                drift_method="ks_test",
                reference_period_start=reference_start,
                reference_period_end=reference_end,
                current_period_start=current_start,
                current_period_end=end_date,
                p_value=p_value
            )
            
            return drift_metrics
            
        except Exception as e:
            logger.error(f"Error detecting drift for {region}/{service}/{target}: {e}")
            return None
        finally:
            self.db_manager.close_session(session)
    
    def calculate_days_since_retrain(self, region: str, service: str, target: str) -> Tuple[int, Optional[datetime]]:
        """
        Calculate days since last model retrain
        
        Returns:
            Tuple of (days_since_retrain, last_retrain_date)
        """
        # For now, simulate based on model file timestamps
        # In production, this would track actual retrain events
        try:
            models_dir = Path(__file__).parent.parent / "models" / "arima"
            model_file = models_dir / f"{region}_{service}_{target}_arima.pkl"
            
            if model_file.exists():
                last_modified = datetime.fromtimestamp(model_file.stat().st_mtime)
                days_since = (datetime.now() - last_modified).days
                return days_since, last_modified
            else:
                return 999, None  # Model doesn't exist
                
        except Exception as e:
            logger.error(f"Error calculating retrain days for {region}/{service}/{target}: {e}")
            return 999, None
    
    def assess_model_health(self, performance: ModelPerformanceMetrics, 
                           drift: Optional[DriftMetrics], 
                           days_since_retrain: int) -> Tuple[ModelHealth, RecommendedAction, str]:
        """
        Assess overall model health and recommend actions
        
        Args:
            performance: Performance metrics
            drift: Drift metrics (optional)
            days_since_retrain: Days since last retrain
            
        Returns:
            Tuple of (health_status, recommended_action, alert_level)
        """
        # Initialize with good health
        health = ModelHealth.GOOD
        action = RecommendedAction.CONTINUE
        alert_level = "info"
        
        # Check performance degradation
        mae_ratio = performance.current_mae / performance.baseline_mae
        
        if mae_ratio > self.config["mae_degradation_threshold"]:
            health = ModelHealth.WARNING
            action = RecommendedAction.RETRAIN_SOON
            alert_level = "warning"
            
            if mae_ratio > 1.5:  # 50% worse than baseline
                health = ModelHealth.CRITICAL
                action = RecommendedAction.RETRAIN_IMMEDIATELY
                alert_level = "critical"
        
        # Check data coverage
        if performance.data_coverage < self.config["data_coverage_threshold"]:
            if health == ModelHealth.GOOD:
                health = ModelHealth.WARNING
                action = RecommendedAction.INVESTIGATE
                alert_level = "warning"
        
        # Check drift
        if drift and drift.drift_flag:
            if health == ModelHealth.GOOD:
                health = ModelHealth.WARNING
                action = RecommendedAction.MONITOR_CLOSELY
                alert_level = "warning"
            elif health == ModelHealth.WARNING:
                health = ModelHealth.CRITICAL
                action = RecommendedAction.RETRAIN_SOON
                alert_level = "critical"
        
        # Check time since last retrain
        if days_since_retrain > self.config["retrain_days_threshold"]:
            if action == RecommendedAction.CONTINUE:
                action = RecommendedAction.RETRAIN_SOON
                alert_level = "warning"
        
        # Check trend
        if performance.mae_trend == "degrading":
            if action == RecommendedAction.CONTINUE:
                action = RecommendedAction.MONITOR_CLOSELY
        
        # Final health assessment
        if action in [RecommendedAction.RETRAIN_IMMEDIATELY]:
            health = ModelHealth.CRITICAL
        elif action in [RecommendedAction.RETRAIN_SOON, RecommendedAction.INVESTIGATE]:
            health = max(health, ModelHealth.WARNING)
        
        return health, action, alert_level
    
    def generate_monitoring_summary(self, status: ModelMonitoringStatus) -> str:
        """Generate human-readable monitoring summary"""
        perf = status.performance_metrics
        drift = status.drift_metrics
        
        summary_parts = []
        
        # Performance summary
        summary_parts.append(f"Current MAE: {perf.current_mae:.2f} (baseline: {perf.baseline_mae:.2f})")
        summary_parts.append(f"30-day average: {perf.mae_30day_avg:.2f}, trend: {perf.mae_trend}")
        
        # Drift summary
        if drift:
            drift_status = "detected" if drift.drift_flag else "not detected"
            summary_parts.append(f"Data drift: {drift_status} (score: {drift.drift_score:.3f})")
        
        # Retrain summary
        summary_parts.append(f"Days since retrain: {status.days_since_last_retrain}")
        
        # Action summary
        summary_parts.append(f"Recommended action: {status.recommended_action.value}")
        
        return "; ".join(summary_parts)
    
    def monitor_model(self, region: str, service: str, target: str) -> Optional[ModelMonitoringStatus]:
        """
        Perform complete monitoring for a single model
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            
        Returns:
            ModelMonitoringStatus object or None if monitoring failed
        """
        try:
            # Calculate performance metrics
            performance = self.calculate_performance_metrics(region, service, target)
            if not performance:
                logger.warning(f"Unable to calculate performance metrics for {region}/{service}/{target}")
                return None
            
            # Detect drift
            drift = self.detect_data_drift(region, service, target)
            
            # Calculate days since retrain
            days_since_retrain, last_retrain_date = self.calculate_days_since_retrain(region, service, target)
            
            # Assess health
            health, action, alert_level = self.assess_model_health(performance, drift, days_since_retrain)
            
            # Create monitoring status
            status = ModelMonitoringStatus(
                region=region,
                service=service,
                target=target,
                model_version=performance.model_version,
                health_status=health,
                recommended_action=action,
                performance_metrics=performance,
                drift_metrics=drift,
                days_since_last_retrain=days_since_retrain,
                last_retrain_date=last_retrain_date,
                alert_level=alert_level,
                monitoring_summary=""  # Will be filled below
            )
            
            # Generate summary
            status.monitoring_summary = self.generate_monitoring_summary(status)
            
            logger.info(f"Monitoring completed for {region}/{service}/{target}: {health.value}")
            return status
            
        except Exception as e:
            logger.error(f"Error monitoring model {region}/{service}/{target}: {e}")
            return None
    
    def monitor_all_models(self) -> List[ModelMonitoringStatus]:
        """
        Monitor all available models
        
        Returns:
            List of ModelMonitoringStatus objects
        """
        from model_manager import get_model_manager
        
        model_manager = get_model_manager()
        available_combinations = model_manager.get_available_combinations()
        
        monitoring_results = []
        
        for region, service, target in available_combinations:
            status = self.monitor_model(region, service, target)
            if status:
                monitoring_results.append(status)
        
        logger.info(f"Monitoring completed for {len(monitoring_results)} models")
        return monitoring_results
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get overall monitoring summary across all models
        
        Returns:
            Dictionary with summary statistics
        """
        monitoring_results = self.monitor_all_models()
        
        if not monitoring_results:
            return {"message": "No models available for monitoring", "total_models": 0}
        
        # Count by health status
        health_counts = {}
        for status in monitoring_results:
            health = status.health_status.value
            health_counts[health] = health_counts.get(health, 0) + 1
        
        # Count by recommended action
        action_counts = {}
        for status in monitoring_results:
            action = status.recommended_action.value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Find models needing immediate attention
        critical_models = [s for s in monitoring_results if s.health_status == ModelHealth.CRITICAL]
        warning_models = [s for s in monitoring_results if s.health_status == ModelHealth.WARNING]
        
        # Calculate overall system health
        total_models = len(monitoring_results)
        healthy_models = len([s for s in monitoring_results if s.health_status in [ModelHealth.EXCELLENT, ModelHealth.GOOD]])
        system_health_score = healthy_models / total_models if total_models > 0 else 0.0
        
        return {
            "monitoring_timestamp": datetime.now().isoformat(),
            "total_models": total_models,
            "system_health_score": round(system_health_score, 3),
            "health_distribution": health_counts,
            "action_distribution": action_counts,
            "critical_models": [
                {
                    "region": s.region,
                    "service": s.service,
                    "target": s.target,
                    "health": s.health_status.value,
                    "action": s.recommended_action.value,
                    "summary": s.monitoring_summary
                }
                for s in critical_models
            ],
            "warning_models": [
                {
                    "region": s.region,
                    "service": s.service,
                    "target": s.target,
                    "health": s.health_status.value,
                    "action": s.recommended_action.value,
                    "summary": s.monitoring_summary
                }
                for s in warning_models
            ]
        }

# Global monitor instance
_model_monitor = None

def get_model_monitor() -> ModelMonitor:
    """Get global model monitor instance"""
    global _model_monitor
    if _model_monitor is None:
        _model_monitor = ModelMonitor()
    return _model_monitor

if __name__ == "__main__":
    # Test monitoring system
    monitor = get_model_monitor()
    
    print("Running model monitoring...")
    summary = monitor.get_monitoring_summary()
    print(f"System health score: {summary['system_health_score']:.3f}")
    print(f"Total models: {summary['total_models']}")
    print(f"Critical models: {len(summary['critical_models'])}")
    print(f"Warning models: {len(summary['warning_models'])}")