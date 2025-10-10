"""
Forecast accuracy tracking and metrics calculation
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import statistics
import numpy as np
from dataclasses import dataclass

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from database import get_database_manager, Forecast, Actual, AccuracyMetric
from sqlalchemy import and_, func

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AccuracyResult:
    """Container for accuracy calculation results"""
    region: str
    service: str
    target: str
    model_version: str
    mae: float  # Mean Absolute Error
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    sample_size: int
    period_start: datetime
    period_end: datetime
    accuracy_score: float  # Overall score 0-1 (higher is better)

class AccuracyTracker:
    """
    System for tracking forecast accuracy by comparing predictions with actual values
    """
    
    def __init__(self):
        """Initialize accuracy tracker"""
        self.db_manager = get_database_manager()
    
    def add_actual_values(self, actuals_data: List[Dict[str, Any]]) -> int:
        """
        Add actual observed values to the database
        
        Args:
            actuals_data: List of dictionaries with keys:
                - region: str
                - service: str
                - target: str  
                - date: str (ISO format)
                - actual_value: float
                - data_source: str (optional)
        
        Returns:
            Number of actual records added
        """
        session = self.db_manager.get_session()
        records_added = 0
        
        try:
            for actual_data in actuals_data:
                # Check if record already exists
                existing = session.query(Actual).filter(
                    and_(
                        Actual.region == actual_data['region'],
                        Actual.service == actual_data['service'],
                        Actual.target == actual_data['target'],
                        Actual.date == datetime.fromisoformat(actual_data['date'].replace('Z', '+00:00'))
                    )
                ).first()
                
                if not existing:
                    actual = Actual(
                        region=actual_data['region'],
                        service=actual_data['service'],
                        target=actual_data['target'],
                        date=datetime.fromisoformat(actual_data['date'].replace('Z', '+00:00')),
                        actual_value=actual_data['actual_value'],
                        data_source=actual_data.get('data_source', 'manual')
                    )
                    session.add(actual)
                    records_added += 1
                else:
                    # Update existing record
                    existing.actual_value = actual_data['actual_value']
                    existing.recorded_at = datetime.utcnow()
                    existing.data_source = actual_data.get('data_source', 'manual')
            
            session.commit()
            logger.info(f"Added/updated {records_added} actual value records")
            return records_added
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add actual values: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def calculate_accuracy_metrics(self, forecasts: List[float], actuals: List[float]) -> Tuple[float, float, float, float]:
        """
        Calculate accuracy metrics for forecast vs actual data
        
        Args:
            forecasts: List of predicted values
            actuals: List of actual values
            
        Returns:
            Tuple of (MAE, MAPE, RMSE, accuracy_score)
        """
        if len(forecasts) != len(actuals) or len(forecasts) == 0:
            return 0.0, 0.0, 0.0, 0.0
        
        # Convert to numpy arrays for easier calculation
        forecasts = np.array(forecasts)
        actuals = np.array(actuals)
        
        # Mean Absolute Error
        mae = np.mean(np.abs(forecasts - actuals))
        
        # Mean Absolute Percentage Error (handle division by zero)
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = np.mean(np.abs((actuals - forecasts) / actuals)) * 100
            mape = np.where(np.isfinite(mape), mape, 0.0)
            if isinstance(mape, np.ndarray):
                mape = np.mean(mape)
        
        # Root Mean Square Error
        rmse = np.sqrt(np.mean((forecasts - actuals) ** 2))
        
        # Accuracy Score (0-1, higher is better)
        # Based on normalized MAE - assumes typical values are in range 0-100
        max_possible_error = np.mean(np.abs(actuals)) + np.std(actuals)
        if max_possible_error > 0:
            accuracy_score = max(0.0, 1.0 - (mae / max_possible_error))
        else:
            accuracy_score = 1.0 if mae == 0 else 0.0
        
        return float(mae), float(mape), float(rmse), float(accuracy_score)
    
    def calculate_accuracy_for_combination(self, region: str, service: str, target: str,
                                         days_back: int = 30) -> Optional[AccuracyResult]:
        """
        Calculate accuracy metrics for a specific region/service/target combination
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            days_back: Number of days back to analyze
            
        Returns:
            AccuracyResult object or None if insufficient data
        """
        session = self.db_manager.get_session()
        
        try:
            # Define time period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Get forecasts for this combination and time period
            forecasts_query = session.query(Forecast).filter(
                and_(
                    Forecast.region == region,
                    Forecast.service == service,
                    Forecast.target == target,
                    Forecast.forecast_date >= start_date,
                    Forecast.forecast_date <= end_date
                )
            ).order_by(Forecast.forecast_date)
            
            forecasts = forecasts_query.all()
            
            if not forecasts:
                logger.warning(f"No forecast data found for {region}/{service}/{target}")
                return None
            
            # Get corresponding actual values
            forecast_dates = [f.forecast_date for f in forecasts]
            
            actuals_query = session.query(Actual).filter(
                and_(
                    Actual.region == region,
                    Actual.service == service,
                    Actual.target == target,
                    Actual.date.in_(forecast_dates)
                )
            ).order_by(Actual.date)
            
            actuals = actuals_query.all()
            
            if not actuals:
                logger.warning(f"No actual data found for {region}/{service}/{target}")
                return None
            
            # Align forecasts and actuals by date
            actuals_dict = {a.date: a.actual_value for a in actuals}
            aligned_forecasts = []
            aligned_actuals = []
            
            for forecast in forecasts:
                if forecast.forecast_date in actuals_dict:
                    aligned_forecasts.append(forecast.predicted_value)
                    aligned_actuals.append(actuals_dict[forecast.forecast_date])
            
            if len(aligned_forecasts) < 3:  # Need at least 3 data points
                logger.warning(f"Insufficient aligned data for {region}/{service}/{target}: {len(aligned_forecasts)} points")
                return None
            
            # Calculate metrics
            mae, mape, rmse, accuracy_score = self.calculate_accuracy_metrics(
                aligned_forecasts, aligned_actuals
            )
            
            # Get model version from most recent forecast
            model_version = forecasts[-1].model_version if forecasts else "unknown"
            
            result = AccuracyResult(
                region=region,
                service=service,
                target=target,
                model_version=model_version,
                mae=mae,
                mape=mape,
                rmse=rmse,
                sample_size=len(aligned_forecasts),
                period_start=start_date,
                period_end=end_date,
                accuracy_score=accuracy_score
            )
            
            logger.info(f"Calculated accuracy for {region}/{service}/{target}: "
                       f"MAE={mae:.2f}, MAPE={mape:.1f}%, Score={accuracy_score:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating accuracy for {region}/{service}/{target}: {e}")
            return None
        finally:
            self.db_manager.close_session(session)
    
    def store_accuracy_metrics(self, accuracy_results: List[AccuracyResult]) -> int:
        """
        Store calculated accuracy metrics in database
        
        Args:
            accuracy_results: List of AccuracyResult objects
            
        Returns:
            Number of metrics stored
        """
        session = self.db_manager.get_session()
        stored_count = 0
        
        try:
            for result in accuracy_results:
                # Store each metric type separately
                metric_types = [
                    ('MAE', result.mae),
                    ('MAPE', result.mape),
                    ('RMSE', result.rmse),
                    ('ACCURACY_SCORE', result.accuracy_score)
                ]
                
                for metric_type, metric_value in metric_types:
                    metric = AccuracyMetric(
                        region=result.region,
                        service=result.service,
                        target=result.target,
                        model_version=result.model_version,
                        metric_type=metric_type,
                        metric_value=metric_value,
                        period_start=result.period_start,
                        period_end=result.period_end,
                        sample_size=result.sample_size
                    )
                    session.add(metric)
                    stored_count += 1
            
            session.commit()
            logger.info(f"Stored {stored_count} accuracy metric records")
            return stored_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store accuracy metrics: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def calculate_all_accuracy_metrics(self, days_back: int = 30) -> List[AccuracyResult]:
        """
        Calculate accuracy metrics for all available region/service/target combinations
        
        Args:
            days_back: Number of days back to analyze
            
        Returns:
            List of AccuracyResult objects
        """
        session = self.db_manager.get_session()
        results = []
        
        try:
            # Get all unique combinations that have both forecasts and actuals
            forecast_combinations = session.query(
                Forecast.region, 
                Forecast.service, 
                Forecast.target
            ).distinct().all()
            
            actual_combinations = session.query(
                Actual.region,
                Actual.service, 
                Actual.target
            ).distinct().all()
            
            # Find intersection of combinations
            forecast_set = set(forecast_combinations)
            actual_set = set(actual_combinations)
            common_combinations = forecast_set.intersection(actual_set)
            
            logger.info(f"Found {len(common_combinations)} combinations with both forecasts and actuals")
            
            for region, service, target in common_combinations:
                result = self.calculate_accuracy_for_combination(
                    region, service, target, days_back
                )
                if result:
                    results.append(result)
            
            # Store results in database
            if results:
                self.store_accuracy_metrics(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating all accuracy metrics: {e}")
            return []
        finally:
            self.db_manager.close_session(session)
    
    def get_accuracy_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get summary of accuracy metrics across all combinations
        
        Args:
            days_back: Number of days back to analyze
            
        Returns:
            Dictionary with accuracy summary statistics
        """
        session = self.db_manager.get_session()
        
        try:
            # Get recent accuracy metrics
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            metrics = session.query(AccuracyMetric).filter(
                AccuracyMetric.calculated_at >= cutoff_date
            ).all()
            
            if not metrics:
                return {"message": "No accuracy metrics available", "total_metrics": 0}
            
            # Group by metric type
            metrics_by_type = {}
            for metric in metrics:
                if metric.metric_type not in metrics_by_type:
                    metrics_by_type[metric.metric_type] = []
                metrics_by_type[metric.metric_type].append(metric.metric_value)
            
            # Calculate summary statistics
            summary = {
                "total_metrics": len(metrics),
                "period_days": days_back,
                "metric_types": {}
            }
            
            for metric_type, values in metrics_by_type.items():
                summary["metric_types"][metric_type] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
                }
            
            # Get combination-level summary
            combinations = session.query(
                AccuracyMetric.region,
                AccuracyMetric.service,
                AccuracyMetric.target,
                func.avg(AccuracyMetric.metric_value).label('avg_accuracy')
            ).filter(
                and_(
                    AccuracyMetric.metric_type == 'ACCURACY_SCORE',
                    AccuracyMetric.calculated_at >= cutoff_date
                )
            ).group_by(
                AccuracyMetric.region,
                AccuracyMetric.service,
                AccuracyMetric.target
            ).order_by(func.avg(AccuracyMetric.metric_value).desc()).all()
            
            summary["top_performers"] = [
                {
                    "region": combo.region,
                    "service": combo.service,
                    "target": combo.target,
                    "accuracy_score": float(combo.avg_accuracy)
                }
                for combo in combinations[:10]
            ]
            
            summary["worst_performers"] = [
                {
                    "region": combo.region,
                    "service": combo.service,
                    "target": combo.target,
                    "accuracy_score": float(combo.avg_accuracy)
                }
                for combo in combinations[-5:]
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating accuracy summary: {e}")
            return {"error": str(e)}
        finally:
            self.db_manager.close_session(session)
    
    def simulate_actual_data(self, days_back: int = 30, noise_factor: float = 0.1) -> int:
        """
        Generate simulated actual data based on existing forecasts (for testing)
        
        Args:
            days_back: Number of days back to generate data for
            noise_factor: Amount of noise to add (0.0 = no noise, 1.0 = high noise)
            
        Returns:
            Number of simulated actual records created
        """
        import random
        
        session = self.db_manager.get_session()
        
        try:
            # Get recent forecasts
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            forecasts = session.query(Forecast).filter(
                Forecast.forecast_date >= cutoff_date
            ).all()
            
            if not forecasts:
                logger.warning("No forecasts found to simulate actuals from")
                return 0
            
            simulated_actuals = []
            
            for forecast in forecasts:
                # Add noise to forecast to create "actual" value
                noise = random.gauss(0, forecast.predicted_value * noise_factor)
                actual_value = max(0, forecast.predicted_value + noise)
                
                simulated_actuals.append({
                    'region': forecast.region,
                    'service': forecast.service,
                    'target': forecast.target,
                    'date': forecast.forecast_date.isoformat(),
                    'actual_value': actual_value,
                    'data_source': 'simulated'
                })
            
            # Add simulated actuals to database
            records_added = self.add_actual_values(simulated_actuals)
            
            logger.info(f"Generated {records_added} simulated actual records")
            return records_added
            
        except Exception as e:
            logger.error(f"Error generating simulated actual data: {e}")
            return 0
        finally:
            self.db_manager.close_session(session)

# Global accuracy tracker instance
_accuracy_tracker = None

def get_accuracy_tracker() -> AccuracyTracker:
    """Get global accuracy tracker instance"""
    global _accuracy_tracker
    if _accuracy_tracker is None:
        _accuracy_tracker = AccuracyTracker()
    return _accuracy_tracker

if __name__ == "__main__":
    # Test accuracy tracking
    tracker = get_accuracy_tracker()
    
    print("Generating simulated actual data...")
    simulated_count = tracker.simulate_actual_data(days_back=30)
    print(f"Generated {simulated_count} simulated records")
    
    print("Calculating accuracy metrics...")
    results = tracker.calculate_all_accuracy_metrics(days_back=30)
    print(f"Calculated accuracy for {len(results)} combinations")
    
    print("Getting accuracy summary...")
    summary = tracker.get_accuracy_summary()
    print(f"Summary: {summary.get('total_metrics', 0)} metrics available")