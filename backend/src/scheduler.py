"""
Automated forecast scheduler for Azure demand forecasting system
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import traceback

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from database import get_database_manager, ForecastRun, Forecast
from model_manager import get_model_manager
from capacity_planning import get_capacity_engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """Configuration for the forecast scheduler"""
    forecast_horizon_days: int = 30
    schedule_frequency: str = "daily"  # "daily" or "weekly"
    model_version: str = "1.0"
    max_retries: int = 3
    store_confidence_intervals: bool = True

class ForecastScheduler:
    """
    Automated forecast scheduler that:
    1. Generates forecasts for all available model combinations
    2. Stores forecasts in database with metadata
    3. Generates capacity recommendations
    4. Tracks run status and errors
    """
    
    def __init__(self, config: SchedulerConfig = None):
        """
        Initialize the forecast scheduler
        
        Args:
            config: Scheduler configuration (uses defaults if None)
        """
        self.config = config or SchedulerConfig()
        self.db_manager = get_database_manager()
        self.model_manager = get_model_manager()
        self.capacity_engine = get_capacity_engine()
        
    def generate_run_id(self) -> str:
        """Generate unique run ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    def create_forecast_run(self, run_id: str) -> ForecastRun:
        """
        Create forecast run record in database
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            ForecastRun object
        """
        run_start = datetime.now()
        run_end = run_start + timedelta(days=self.config.forecast_horizon_days)
        
        forecast_run = ForecastRun(
            run_id=run_id,
            model_version=self.config.model_version,
            run_time=run_start,
            run_window_start=run_start,
            run_window_end=run_end,
            status='running',
            total_forecasts=0
        )
        
        session = self.db_manager.get_session()
        try:
            session.add(forecast_run)
            session.commit()
            logger.info(f"Created forecast run: {run_id}")
            return forecast_run
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create forecast run: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def store_forecast(self, run_id: str, region: str, service: str, target: str,
                      forecast_data: List[float], forecast_dates: List[str],
                      confidence_intervals: Optional[Dict[str, List[float]]] = None) -> int:
        """
        Store forecast results in database
        
        Args:
            run_id: Run identifier
            region: Azure region
            service: Service type
            target: Target metric
            forecast_data: List of predicted values
            forecast_dates: List of forecast dates
            confidence_intervals: Optional confidence intervals
            
        Returns:
            Number of forecast records created
        """
        session = self.db_manager.get_session()
        forecasts_created = 0
        
        try:
            for i, (date_str, predicted_value) in enumerate(zip(forecast_dates, forecast_data)):
                forecast_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Extract confidence intervals if available
                lower_ci = None
                upper_ci = None
                if confidence_intervals:
                    lower_ci = confidence_intervals.get('lower', [None])[i] if i < len(confidence_intervals.get('lower', [])) else None
                    upper_ci = confidence_intervals.get('upper', [None])[i] if i < len(confidence_intervals.get('upper', [])) else None
                
                forecast = Forecast(
                    run_id=run_id,
                    region=region,
                    service=service,
                    target=target,
                    forecast_date=forecast_date,
                    predicted_value=predicted_value,
                    lower_ci=lower_ci,
                    upper_ci=upper_ci,
                    model_version=self.config.model_version,
                    horizon_days=self.config.forecast_horizon_days,
                    confidence_score=0.8  # Default confidence score
                )
                
                session.add(forecast)
                forecasts_created += 1
            
            session.commit()
            logger.info(f"Stored {forecasts_created} forecasts for {region}/{service}/{target}")
            return forecasts_created
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store forecasts for {region}/{service}/{target}: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def update_run_status(self, run_id: str, status: str, total_forecasts: int = 0, 
                         error_message: str = None):
        """
        Update forecast run status
        
        Args:
            run_id: Run identifier
            status: New status ('running', 'completed', 'failed')
            total_forecasts: Total number of forecasts generated
            error_message: Error message if failed
        """
        session = self.db_manager.get_session()
        try:
            forecast_run = session.query(ForecastRun).filter(ForecastRun.run_id == run_id).first()
            if forecast_run:
                forecast_run.status = status
                forecast_run.total_forecasts = total_forecasts
                if error_message:
                    forecast_run.error_message = error_message
                session.commit()
                logger.info(f"Updated run {run_id} status to {status}")
            else:
                logger.error(f"Forecast run {run_id} not found")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update run status: {e}")
        finally:
            self.db_manager.close_session(session)
    
    def run_scheduled_forecast(self) -> Dict[str, Any]:
        """
        Execute a complete scheduled forecast run
        
        Returns:
            Dictionary with run results and statistics
        """
        run_start_time = datetime.now()
        run_id = self.generate_run_id()
        
        logger.info(f"Starting scheduled forecast run: {run_id}")
        
        # Create run record
        try:
            forecast_run = self.create_forecast_run(run_id)
        except Exception as e:
            logger.error(f"Failed to create forecast run: {e}")
            return {"status": "failed", "error": str(e)}
        
        # Get available model combinations
        available_combinations = self.model_manager.get_available_combinations()
        if not available_combinations:
            error_msg = "No trained models available for forecasting"
            logger.error(error_msg)
            self.update_run_status(run_id, 'failed', 0, error_msg)
            return {"status": "failed", "error": error_msg}
        
        logger.info(f"Found {len(available_combinations)} model combinations")
        
        # Generate forecasts for each combination
        total_forecasts = 0
        successful_forecasts = 0
        failed_forecasts = 0
        errors = []
        
        # Generate forecast dates
        start_date = datetime.now().date() + timedelta(days=1)
        forecast_dates = [(start_date + timedelta(days=i)).isoformat() 
                         for i in range(self.config.forecast_horizon_days)]
        
        for region, service, target in available_combinations:
            try:
                logger.info(f"Generating forecast for {region}/{service}/{target}")
                
                # Get forecast from model manager
                forecast_result = self.model_manager.get_forecast(
                    region, service, target, self.config.forecast_horizon_days
                )
                
                if not forecast_result:
                    error_msg = f"Failed to generate forecast for {region}/{service}/{target}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    failed_forecasts += 1
                    continue
                
                # Store forecast in database
                forecasts_created = self.store_forecast(
                    run_id=run_id,
                    region=region,
                    service=service,
                    target=target,
                    forecast_data=forecast_result['forecast'],
                    forecast_dates=forecast_dates,
                    confidence_intervals=forecast_result.get('confidence_intervals')
                )
                
                total_forecasts += forecasts_created
                successful_forecasts += 1
                
                logger.info(f"Successfully processed {region}/{service}/{target}")
                
            except Exception as e:
                error_msg = f"Error processing {region}/{service}/{target}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                errors.append(error_msg)
                failed_forecasts += 1
        
        # Update run status
        run_end_time = datetime.now()
        duration = (run_end_time - run_start_time).total_seconds()
        
        if failed_forecasts == 0:
            status = 'completed'
            error_message = None
        elif successful_forecasts > 0:
            status = 'completed'
            error_message = f"Partial success: {failed_forecasts} failures"
        else:
            status = 'failed'
            error_message = "All forecasts failed"
        
        self.update_run_status(run_id, status, total_forecasts, error_message)
        
        # Generate summary
        result = {
            "status": status,
            "run_id": run_id,
            "duration_seconds": duration,
            "total_combinations": len(available_combinations),
            "successful_forecasts": successful_forecasts,
            "failed_forecasts": failed_forecasts,
            "total_forecast_records": total_forecasts,
            "forecast_horizon_days": self.config.forecast_horizon_days,
            "model_version": self.config.model_version,
            "errors": errors[:10]  # Limit error list
        }
        
        logger.info(f"Completed forecast run {run_id} in {duration:.1f}s")
        logger.info(f"Success: {successful_forecasts}, Failed: {failed_forecasts}, Total records: {total_forecasts}")
        
        return result
    
    def get_latest_run_status(self) -> Optional[Dict[str, Any]]:
        """
        Get status of the most recent forecast run
        
        Returns:
            Dictionary with run information or None if no runs found
        """
        session = self.db_manager.get_session()
        try:
            latest_run = session.query(ForecastRun).order_by(ForecastRun.run_time.desc()).first()
            if latest_run:
                return {
                    "run_id": latest_run.run_id,
                    "status": latest_run.status,
                    "run_time": latest_run.run_time.isoformat(),
                    "total_forecasts": latest_run.total_forecasts,
                    "model_version": latest_run.model_version,
                    "error_message": latest_run.error_message
                }
            return None
        finally:
            self.db_manager.close_session(session)
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent forecast runs
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of run information dictionaries
        """
        session = self.db_manager.get_session()
        try:
            runs = session.query(ForecastRun).order_by(ForecastRun.run_time.desc()).limit(limit).all()
            return [
                {
                    "run_id": run.run_id,
                    "status": run.status,
                    "run_time": run.run_time.isoformat(),
                    "total_forecasts": run.total_forecasts,
                    "model_version": run.model_version,
                    "error_message": run.error_message
                }
                for run in runs
            ]
        finally:
            self.db_manager.close_session(session)
    
    # =============================================================================
    # MONITORING AND DRIFT DETECTION METHODS
    # =============================================================================
    
    def run_monitoring_checks(self) -> Dict[str, Any]:
        """
        Run comprehensive monitoring checks
        
        Returns:
            Dictionary with monitoring results
        """
        logger.info("Starting scheduled monitoring checks")
        
        monitoring_results = {
            "timestamp": datetime.now().isoformat(),
            "drift_check": None,
            "performance_check": None,
            "health_check": None,
            "retraining_check": None,
            "alerts": [],
            "status": "running"
        }
        
        try:
            # Run drift detection
            drift_results = self.run_drift_detection()
            monitoring_results["drift_check"] = drift_results
            
            # Run performance monitoring
            performance_results = self.run_performance_monitoring()
            monitoring_results["performance_check"] = performance_results
            
            # Run health checks
            health_results = self.run_health_checks()
            monitoring_results["health_check"] = health_results
            
            # Check for retraining needs
            retraining_results = self.check_retraining_needs()
            monitoring_results["retraining_check"] = retraining_results
            
            # Collect alerts
            alerts = self.collect_monitoring_alerts(drift_results, performance_results, health_results, retraining_results)
            monitoring_results["alerts"] = alerts
            
            # Process alerts through alerting system
            created_alerts = self.process_alerts_through_system(monitoring_results)
            monitoring_results["created_alerts"] = len(created_alerts)
            
            monitoring_results["status"] = "completed"
            logger.info(f"Monitoring checks completed. Found {len(alerts)} alerts, created {len(created_alerts)} system alerts.")
            
        except Exception as e:
            monitoring_results["status"] = "failed"
            monitoring_results["error"] = str(e)
            logger.error(f"Monitoring checks failed: {e}")
        
        return monitoring_results
    
    def run_drift_detection(self) -> Dict[str, Any]:
        """
        Run data drift detection across all models
        
        Returns:
            Dictionary with drift detection results
        """
        try:
            from .model_monitor import get_model_monitor
            
            monitor = get_model_monitor()
            results = monitor.monitor_all_models()
            
            # Analyze drift results
            total_models = len(results)
            models_with_drift = [r for r in results if r.drift_metrics and r.drift_metrics.drift_flag]
            
            drift_summary = {
                "total_models_checked": total_models,
                "models_with_drift": len(models_with_drift),
                "drift_detected": len(models_with_drift) > 0,
                "high_drift_models": [
                    {
                        "region": r.region,
                        "service": r.service, 
                        "target": r.target,
                        "drift_score": r.drift_metrics.drift_score,
                        "p_value": r.drift_metrics.p_value
                    }
                    for r in models_with_drift
                    if r.drift_metrics.drift_score > 0.1  # High drift threshold
                ],
                "checked_at": datetime.now().isoformat()
            }
            
            logger.info(f"Drift detection completed: {len(models_with_drift)}/{total_models} models with drift")
            return drift_summary
            
        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def run_performance_monitoring(self) -> Dict[str, Any]:
        """
        Run performance monitoring across all models
        
        Returns:
            Dictionary with performance monitoring results
        """
        try:
            from .model_monitor import get_model_monitor
            
            monitor = get_model_monitor()
            results = monitor.monitor_all_models()
            
            if not results:
                return {"error": "No models available for performance monitoring"}
            
            # Analyze performance
            degraded_models = []
            for result in results:
                perf = result.performance_metrics
                mae_ratio = perf.current_mae / perf.baseline_mae
                
                if mae_ratio > 1.2:  # More than 20% worse than baseline
                    degraded_models.append({
                        "region": result.region,
                        "service": result.service,
                        "target": result.target,
                        "current_mae": perf.current_mae,
                        "baseline_mae": perf.baseline_mae,
                        "degradation_ratio": mae_ratio,
                        "trend": perf.mae_trend
                    })
            
            # Calculate average performance
            mae_values = [r.performance_metrics.current_mae for r in results]
            avg_mae = sum(mae_values) / len(mae_values)
            
            performance_summary = {
                "total_models_checked": len(results),
                "degraded_models_count": len(degraded_models),
                "degraded_models": degraded_models,
                "average_mae": round(avg_mae, 3),
                "performance_degradation_detected": len(degraded_models) > 0,
                "checked_at": datetime.now().isoformat()
            }
            
            logger.info(f"Performance monitoring completed: {len(degraded_models)}/{len(results)} models degraded")
            return performance_summary
            
        except Exception as e:
            logger.error(f"Performance monitoring failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def run_health_checks(self) -> Dict[str, Any]:
        """
        Run system health checks
        
        Returns:
            Dictionary with health check results
        """
        try:
            from .model_monitor import get_model_monitor
            
            monitor = get_model_monitor()
            results = monitor.monitor_all_models()
            
            if not results:
                return {"error": "No models available for health checks", "system_status": "unknown"}
            
            # Categorize by health status
            health_counts = {
                "excellent": 0,
                "good": 0,
                "warning": 0,
                "critical": 0
            }
            
            critical_models = []
            warning_models = []
            
            for result in results:
                health_status = result.health_status.value
                health_counts[health_status] += 1
                
                if health_status == "critical":
                    critical_models.append({
                        "region": result.region,
                        "service": result.service,
                        "target": result.target,
                        "summary": result.monitoring_summary,
                        "recommended_action": result.recommended_action.value
                    })
                elif health_status == "warning":
                    warning_models.append({
                        "region": result.region,
                        "service": result.service,
                        "target": result.target,
                        "summary": result.monitoring_summary,
                        "recommended_action": result.recommended_action.value
                    })
            
            # Determine overall system health
            total_models = len(results)
            healthy_count = health_counts["excellent"] + health_counts["good"]
            health_percentage = healthy_count / total_models if total_models > 0 else 0
            
            if health_counts["critical"] > 0:
                system_status = "critical"
            elif health_counts["warning"] > total_models * 0.3:
                system_status = "warning"
            elif health_percentage > 0.8:
                system_status = "healthy"
            else:
                system_status = "degraded"
            
            health_summary = {
                "system_status": system_status,
                "health_percentage": round(health_percentage * 100, 1),
                "total_models": total_models,
                "health_distribution": health_counts,
                "critical_models": critical_models,
                "warning_models": warning_models,
                "checked_at": datetime.now().isoformat()
            }
            
            logger.info(f"Health checks completed: System status {system_status} ({health_percentage:.1%} healthy)")
            return health_summary
            
        except Exception as e:
            logger.error(f"Health checks failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def check_retraining_needs(self) -> Dict[str, Any]:
        """
        Check which models need retraining
        
        Returns:
            Dictionary with retraining recommendations
        """
        try:
            from .auto_retrainer import get_auto_retrainer
            
            retrainer = get_auto_retrainer()
            available_combinations = self.model_manager.get_available_combinations()
            
            retrain_recommendations = []
            
            for region, service, target in available_combinations:
                should_retrain, triggers = retrainer.should_retrain(region, service, target)
                
                if should_retrain:
                    retrain_recommendations.append({
                        "region": region,
                        "service": service,
                        "target": target,
                        "triggers": [t.value for t in triggers],
                        "primary_trigger": triggers[0].value if triggers else "unknown"
                    })
            
            retraining_summary = {
                "total_models_checked": len(available_combinations),
                "models_needing_retrain": len(retrain_recommendations),
                "retraining_needed": len(retrain_recommendations) > 0,
                "recommendations": retrain_recommendations,
                "checked_at": datetime.now().isoformat()
            }
            
            logger.info(f"Retraining check completed: {len(retrain_recommendations)} models need retraining")
            return retraining_summary
            
        except Exception as e:
            logger.error(f"Retraining check failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def collect_monitoring_alerts(self, drift_results: Dict, performance_results: Dict, 
                                health_results: Dict, retraining_results: Dict) -> List[Dict[str, Any]]:
        """
        Collect alerts from monitoring results
        
        Args:
            drift_results: Drift detection results
            performance_results: Performance monitoring results
            health_results: Health check results
            retraining_results: Retraining check results
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        try:
            # Critical system health alerts
            if health_results.get("system_status") == "critical":
                alerts.append({
                    "level": "critical",
                    "type": "system_health",
                    "message": f"System health critical: {len(health_results.get('critical_models', []))} critical models",
                    "timestamp": datetime.now().isoformat(),
                    "details": health_results.get("critical_models", [])
                })
            
            # High drift alerts
            if drift_results.get("drift_detected") and drift_results.get("high_drift_models"):
                alerts.append({
                    "level": "warning",
                    "type": "data_drift",
                    "message": f"High data drift detected in {len(drift_results['high_drift_models'])} models",
                    "timestamp": datetime.now().isoformat(),
                    "details": drift_results["high_drift_models"]
                })
            
            # Performance degradation alerts
            if performance_results.get("performance_degradation_detected"):
                degraded_count = performance_results.get("degraded_models_count", 0)
                alerts.append({
                    "level": "warning",
                    "type": "performance_degradation",
                    "message": f"Performance degradation detected in {degraded_count} models",
                    "timestamp": datetime.now().isoformat(),
                    "details": performance_results.get("degraded_models", [])
                })
            
            # Retraining needed alerts
            if retraining_results.get("retraining_needed"):
                retrain_count = retraining_results.get("models_needing_retrain", 0)
                alerts.append({
                    "level": "info",
                    "type": "retraining_needed",
                    "message": f"{retrain_count} models need retraining",
                    "timestamp": datetime.now().isoformat(),
                    "details": retraining_results.get("recommendations", [])
                })
            
        except Exception as e:
            logger.error(f"Error collecting alerts: {e}")
            alerts.append({
                "level": "error",
                "type": "monitoring_error",
                "message": f"Error collecting monitoring alerts: {e}",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    def run_automated_retraining(self) -> Dict[str, Any]:
        """
        Run automated retraining for models that need it
        
        Returns:
            Dictionary with retraining results
        """
        try:
            from .auto_retrainer import get_auto_retrainer
            
            retrainer = get_auto_retrainer()
            job_ids = retrainer.check_all_models_for_retraining()
            
            retraining_summary = {
                "jobs_started": len(job_ids),
                "job_ids": job_ids,
                "automated_retraining_triggered": len(job_ids) > 0,
                "triggered_at": datetime.now().isoformat()
            }
            
            logger.info(f"Automated retraining completed: {len(job_ids)} jobs started")
            return retraining_summary
            
        except Exception as e:
            logger.error(f"Automated retraining failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    def process_alerts_through_system(self, monitoring_results: Dict[str, Any]) -> List[Any]:
        """
        Process monitoring results through the alerting system
        
        Args:
            monitoring_results: Results from monitoring checks
            
        Returns:
            List of created alerts
        """
        try:
            from .alerting import get_alert_manager
            
            alert_manager = get_alert_manager()
            created_alerts = alert_manager.process_monitoring_alerts(monitoring_results)
            
            logger.info(f"Processed monitoring results through alerting system: {len(created_alerts)} alerts created")
            return created_alerts
            
        except Exception as e:
            logger.error(f"Error processing alerts through system: {e}")
            return []

# Global scheduler instance
_scheduler = None

def get_scheduler() -> ForecastScheduler:
    """Get global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ForecastScheduler()
    return _scheduler

def run_forecast_job():
    """Entry point for scheduled forecast job"""
    scheduler = get_scheduler()
    result = scheduler.run_scheduled_forecast()
    
    # Log results
    if result["status"] == "completed":
        logger.info(f"Forecast job completed successfully: {result['total_forecast_records']} records")
    else:
        logger.error(f"Forecast job failed: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    # Run forecast when executed directly
    print("Starting automated forecast generation...")
    result = run_forecast_job()
    print(f"Forecast completed with status: {result['status']}")
    if result.get('errors'):
        print(f"Errors encountered: {len(result['errors'])}")
        for error in result['errors'][:5]:  # Show first 5 errors
            print(f"  - {error}")

from database import get_database_manager, ForecastRun, Forecast
from model_manager import get_model_manager
from capacity_planning import get_capacity_engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """Configuration for the forecast scheduler"""
    forecast_horizon_days: int = 30
    schedule_frequency: str = "daily"  # "daily" or "weekly"
    model_version: str = "1.0"
    max_retries: int = 3
    store_confidence_intervals: bool = True

class ForecastScheduler:
    """
    Automated forecast scheduler that:
    1. Generates forecasts for all available model combinations
    2. Stores forecasts in database with metadata
    3. Generates capacity recommendations
    4. Tracks run status and errors
    """
    
    def __init__(self, config: SchedulerConfig = None):
        """
        Initialize the forecast scheduler
        
        Args:
            config: Scheduler configuration (uses defaults if None)
        """
        self.config = config or SchedulerConfig()
        self.db_manager = get_database_manager()
        self.model_manager = get_model_manager()
        self.capacity_engine = get_capacity_engine()
        
    def generate_run_id(self) -> str:
        """Generate unique run ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    def create_forecast_run(self, run_id: str) -> ForecastRun:
        """
        Create forecast run record in database
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            ForecastRun object
        """
        run_start = datetime.now()
        run_end = run_start + timedelta(days=self.config.forecast_horizon_days)
        
        forecast_run = ForecastRun(
            run_id=run_id,
            model_version=self.config.model_version,
            run_time=run_start,
            run_window_start=run_start,
            run_window_end=run_end,
            status='running',
            total_forecasts=0
        )
        
        session = self.db_manager.get_session()
        try:
            session.add(forecast_run)
            session.commit()
            logger.info(f"Created forecast run: {run_id}")
            return forecast_run
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create forecast run: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def store_forecast(self, run_id: str, region: str, service: str, target: str,
                      forecast_data: List[float], forecast_dates: List[str],
                      confidence_intervals: Optional[Dict[str, List[float]]] = None) -> int:
        """
        Store forecast results in database
        
        Args:
            run_id: Run identifier
            region: Azure region
            service: Service type
            target: Target metric
            forecast_data: List of predicted values
            forecast_dates: List of forecast dates
            confidence_intervals: Optional confidence intervals
            
        Returns:
            Number of forecast records created
        """
        session = self.db_manager.get_session()
        forecasts_created = 0
        
        try:
            for i, (date_str, predicted_value) in enumerate(zip(forecast_dates, forecast_data)):
                forecast_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Extract confidence intervals if available
                lower_ci = None
                upper_ci = None
                if confidence_intervals:
                    lower_ci = confidence_intervals.get('lower', [None])[i] if i < len(confidence_intervals.get('lower', [])) else None
                    upper_ci = confidence_intervals.get('upper', [None])[i] if i < len(confidence_intervals.get('upper', [])) else None
                
                forecast = Forecast(
                    run_id=run_id,
                    region=region,
                    service=service,
                    target=target,
                    forecast_date=forecast_date,
                    predicted_value=predicted_value,
                    lower_ci=lower_ci,
                    upper_ci=upper_ci,
                    model_version=self.config.model_version,
                    horizon_days=self.config.forecast_horizon_days,
                    confidence_score=0.8  # Default confidence score
                )
                
                session.add(forecast)
                forecasts_created += 1
            
            session.commit()
            logger.info(f"Stored {forecasts_created} forecasts for {region}/{service}/{target}")
            return forecasts_created
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store forecasts for {region}/{service}/{target}: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def update_run_status(self, run_id: str, status: str, total_forecasts: int = 0, 
                         error_message: str = None):
        """
        Update forecast run status
        
        Args:
            run_id: Run identifier
            status: New status ('running', 'completed', 'failed')
            total_forecasts: Total number of forecasts generated
            error_message: Error message if failed
        """
        session = self.db_manager.get_session()
        try:
            forecast_run = session.query(ForecastRun).filter(ForecastRun.run_id == run_id).first()
            if forecast_run:
                forecast_run.status = status
                forecast_run.total_forecasts = total_forecasts
                if error_message:
                    forecast_run.error_message = error_message
                session.commit()
                logger.info(f"Updated run {run_id} status to {status}")
            else:
                logger.error(f"Forecast run {run_id} not found")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update run status: {e}")
        finally:
            self.db_manager.close_session(session)
    
    def run_scheduled_forecast(self) -> Dict[str, Any]:
        """
        Execute a complete scheduled forecast run
        
        Returns:
            Dictionary with run results and statistics
        """
        run_start_time = datetime.now()
        run_id = self.generate_run_id()
        
        logger.info(f"Starting scheduled forecast run: {run_id}")
        
        # Create run record
        try:
            forecast_run = self.create_forecast_run(run_id)
        except Exception as e:
            logger.error(f"Failed to create forecast run: {e}")
            return {"status": "failed", "error": str(e)}
        
        # Get available model combinations
        available_combinations = self.model_manager.get_available_combinations()
        if not available_combinations:
            error_msg = "No trained models available for forecasting"
            logger.error(error_msg)
            self.update_run_status(run_id, 'failed', 0, error_msg)
            return {"status": "failed", "error": error_msg}
        
        logger.info(f"Found {len(available_combinations)} model combinations")
        
        # Generate forecasts for each combination
        total_forecasts = 0
        successful_forecasts = 0
        failed_forecasts = 0
        errors = []
        
        # Generate forecast dates
        start_date = datetime.now().date() + timedelta(days=1)
        forecast_dates = [(start_date + timedelta(days=i)).isoformat() 
                         for i in range(self.config.forecast_horizon_days)]
        
        for region, service, target in available_combinations:
            try:
                logger.info(f"Generating forecast for {region}/{service}/{target}")
                
                # Get forecast from model manager
                forecast_result = self.model_manager.get_forecast(
                    region, service, target, self.config.forecast_horizon_days
                )
                
                if not forecast_result:
                    error_msg = f"Failed to generate forecast for {region}/{service}/{target}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    failed_forecasts += 1
                    continue
                
                # Store forecast in database
                forecasts_created = self.store_forecast(
                    run_id=run_id,
                    region=region,
                    service=service,
                    target=target,
                    forecast_data=forecast_result['forecast'],
                    forecast_dates=forecast_dates,
                    confidence_intervals=forecast_result.get('confidence_intervals')
                )
                
                total_forecasts += forecasts_created
                successful_forecasts += 1
                
                logger.info(f"Successfully processed {region}/{service}/{target}")
                
            except Exception as e:
                error_msg = f"Error processing {region}/{service}/{target}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                errors.append(error_msg)
                failed_forecasts += 1
        
        # Update run status
        run_end_time = datetime.now()
        duration = (run_end_time - run_start_time).total_seconds()
        
        if failed_forecasts == 0:
            status = 'completed'
            error_message = None
        elif successful_forecasts > 0:
            status = 'completed'
            error_message = f"Partial success: {failed_forecasts} failures"
        else:
            status = 'failed'
            error_message = "All forecasts failed"
        
        self.update_run_status(run_id, status, total_forecasts, error_message)
        
        # Generate summary
        result = {
            "status": status,
            "run_id": run_id,
            "duration_seconds": duration,
            "total_combinations": len(available_combinations),
            "successful_forecasts": successful_forecasts,
            "failed_forecasts": failed_forecasts,
            "total_forecast_records": total_forecasts,
            "forecast_horizon_days": self.config.forecast_horizon_days,
            "model_version": self.config.model_version,
            "errors": errors[:10]  # Limit error list
        }
        
        logger.info(f"Completed forecast run {run_id} in {duration:.1f}s")
        logger.info(f"Success: {successful_forecasts}, Failed: {failed_forecasts}, Total records: {total_forecasts}")
        
        return result
    
    def get_latest_run_status(self) -> Optional[Dict[str, Any]]:
        """
        Get status of the most recent forecast run
        
        Returns:
            Dictionary with run information or None if no runs found
        """
        session = self.db_manager.get_session()
        try:
            latest_run = session.query(ForecastRun).order_by(ForecastRun.run_time.desc()).first()
            if latest_run:
                return {
                    "run_id": latest_run.run_id,
                    "status": latest_run.status,
                    "run_time": latest_run.run_time.isoformat(),
                    "total_forecasts": latest_run.total_forecasts,
                    "model_version": latest_run.model_version,
                    "error_message": latest_run.error_message
                }
            return None
        finally:
            self.db_manager.close_session(session)
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent forecast runs
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of run information dictionaries
        """
        session = self.db_manager.get_session()
        try:
            runs = session.query(ForecastRun).order_by(ForecastRun.run_time.desc()).limit(limit).all()
            return [
                {
                    "run_id": run.run_id,
                    "status": run.status,
                    "run_time": run.run_time.isoformat(),
                    "total_forecasts": run.total_forecasts,
                    "model_version": run.model_version,
                    "error_message": run.error_message
                }
                for run in runs
            ]
        finally:
            self.db_manager.close_session(session)

# Global scheduler instance
_scheduler = None

def get_scheduler() -> ForecastScheduler:
    """Get global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ForecastScheduler()
    return _scheduler

def run_forecast_job():
    """Entry point for scheduled forecast job"""
    scheduler = get_scheduler()
    result = scheduler.run_scheduled_forecast()
    
    # Log results
    if result["status"] == "completed":
        logger.info(f"Forecast job completed successfully: {result['total_forecast_records']} records")
    else:
        logger.error(f"Forecast job failed: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    # Run forecast when executed directly
    print("Starting automated forecast generation...")
    result = run_forecast_job()
    print(f"Forecast completed with status: {result['status']}")
    if result.get('errors'):
        print(f"Errors encountered: {len(result['errors'])}")
        for error in result['errors'][:5]:  # Show first 5 errors
            print(f"  - {error}")