"""
Capacity Planning Engine for Azure Demand Forecasting
Converts forecasts into actionable capacity recommendations.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    MONITOR = "monitor"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    URGENT_SCALE_UP = "urgent_scale_up"

@dataclass
class CapacityRecommendation:
    region: str
    service: str
    target: str
    forecast_period: str
    forecast_peak_demand: float
    forecast_avg_demand: float
    available_capacity: float
    required_capacity: float
    gap_absolute: float
    gap_percentage: float
    risk_level: RiskLevel
    action_type: ActionType
    recommended_adjustment: str
    reason: str
    cost_impact_monthly: float
    confidence_score: float
    additional_metrics: Dict[str, Any]

class CapacityPlanningEngine:
    """
    Main engine for capacity planning and recommendations.
    """
    
    def __init__(self, capacity_inventory_path: Optional[Path] = None):
        """Initialize the capacity planning engine."""
        if capacity_inventory_path is None:
            capacity_inventory_path = Path(__file__).parent.parent / "data" / "capacity_inventory.json"
        
        self.capacity_inventory_path = capacity_inventory_path
        self.capacity_data = None
        self.business_rules = None
        self._load_capacity_inventory()
    
    def _load_capacity_inventory(self):
        """Load capacity inventory and business rules."""
        try:
            with open(self.capacity_inventory_path, 'r') as f:
                data = json.load(f)
            
            self.capacity_data = data.get('capacity_inventory', {})
            self.business_rules = data.get('business_rules', {})
            
            logger.info(f"Loaded capacity inventory for {len(self.capacity_data)} regions")
            
        except Exception as e:
            logger.error(f"Failed to load capacity inventory: {e}")
            self.capacity_data = {}
            self.business_rules = {}
    
    def get_capacity_info(self, region: str, service: str) -> Optional[Dict]:
        """Get capacity information for a specific region/service."""
        if region in self.capacity_data and service in self.capacity_data[region]:
            return self.capacity_data[region][service]
        return None
    
    def calculate_required_capacity(self, forecast_data: List[float], 
                                  capacity_info: Dict, 
                                  strategy: str = "peak_based") -> Tuple[float, Dict]:
        """
        Calculate required capacity based on forecast and strategy.
        
        Args:
            forecast_data: List of forecasted values (percentages)
            capacity_info: Capacity configuration for the service
            strategy: Capacity planning strategy
            
        Returns:
            Tuple of (required_capacity, metrics)
        """
        forecast_array = np.array(forecast_data)
        safety_buffer = capacity_info.get('safety_buffer_pct', 10.0) / 100.0
        
        if strategy == "peak_based":
            base_requirement = np.max(forecast_array)
        elif strategy == "p95_based":
            base_requirement = np.percentile(forecast_array, 95)
        elif strategy == "average_plus_buffer":
            mean_val = np.mean(forecast_array)
            std_val = np.std(forecast_array)
            base_requirement = mean_val + (2 * std_val)
        else:
            base_requirement = np.max(forecast_array)  # Default to peak
        
        # Apply safety buffer
        required_capacity = base_requirement * (1 + safety_buffer)
        
        metrics = {
            "forecast_min": float(np.min(forecast_array)),
            "forecast_max": float(np.max(forecast_array)),
            "forecast_mean": float(np.mean(forecast_array)),
            "forecast_std": float(np.std(forecast_array)),
            "forecast_p95": float(np.percentile(forecast_array, 95)),
            "base_requirement": float(base_requirement),
            "safety_buffer_applied": safety_buffer,
            "strategy_used": strategy
        }
        
        return required_capacity, metrics
    
    def assess_risk_level(self, gap_percentage: float) -> RiskLevel:
        """Assess risk level based on capacity gap."""
        thresholds = self.business_rules.get('adjustment_thresholds', {})
        
        abs_gap = abs(gap_percentage)
        
        if abs_gap <= thresholds.get('monitor_only', 5.0):
            return RiskLevel.LOW
        elif abs_gap <= thresholds.get('plan_scale', 20.0):
            return RiskLevel.MEDIUM
        elif abs_gap <= thresholds.get('urgent_scale', 50.0):
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def determine_action_type(self, gap_percentage: float, risk_level: RiskLevel) -> ActionType:
        """Determine recommended action type."""
        if risk_level == RiskLevel.LOW:
            return ActionType.MONITOR
        elif gap_percentage > 0:  # Need more capacity
            if risk_level == RiskLevel.CRITICAL:
                return ActionType.URGENT_SCALE_UP
            else:
                return ActionType.SCALE_UP
        else:  # Over-provisioned
            return ActionType.SCALE_DOWN
    
    def calculate_unit_adjustment(self, gap_percentage: float, 
                                current_units: int, 
                                capacity_info: Dict) -> Tuple[int, float]:
        """
        Calculate how many units to add/remove and cost impact.
        
        Returns:
            Tuple of (unit_adjustment, cost_impact_monthly)
        """
        # Calculate required unit adjustment
        unit_adjustment = int(np.ceil(current_units * abs(gap_percentage) / 100.0))
        
        # Ensure minimum adjustment of 1 unit for significant gaps
        if abs(gap_percentage) > 5.0 and unit_adjustment == 0:
            unit_adjustment = 1
        
        # Apply sign based on gap direction
        if gap_percentage < 0:  # Over-provisioned
            unit_adjustment = -unit_adjustment
        
        # Calculate cost impact
        cost_per_unit = capacity_info.get('cost_per_unit_monthly', 0.0)
        cost_impact = unit_adjustment * cost_per_unit
        
        return unit_adjustment, cost_impact
    
    def generate_recommendation_text(self, gap_percentage: float, 
                                   unit_adjustment: int,
                                   capacity_info: Dict,
                                   risk_level: RiskLevel) -> str:
        """Generate human-friendly recommendation text."""
        unit_type = capacity_info.get('unit_type', 'units')
        
        if abs(gap_percentage) <= 5.0:
            return f"Monitor only - capacity within acceptable range ({gap_percentage:+.1f}%)"
        
        if unit_adjustment > 0:
            urgency = "urgently " if risk_level == RiskLevel.CRITICAL else ""
            return f"Scale up {urgency}by {unit_adjustment} {unit_type} ({gap_percentage:+.1f}%)"
        elif unit_adjustment < 0:
            return f"Scale down by {abs(unit_adjustment)} {unit_type} to optimize costs ({gap_percentage:+.1f}%)"
        else:
            return f"Maintain current capacity - minor adjustment needed ({gap_percentage:+.1f}%)"
    
    def generate_reason(self, required_capacity: float, available_capacity: float,
                       metrics: Dict, capacity_info: Dict) -> str:
        """Generate detailed reason for the recommendation."""
        strategy = metrics.get('strategy_used', 'peak_based')
        safety_buffer = capacity_info.get('safety_buffer_pct', 10.0)
        
        if required_capacity > available_capacity:
            return f"Forecast {strategy.replace('_', ' ')} exceeds current capacity; {safety_buffer}% safety buffer applied"
        elif required_capacity < available_capacity * 0.8:  # Significantly over-provisioned
            return f"Current capacity significantly exceeds forecast requirements; cost optimization opportunity"
        else:
            return f"Capacity adequate for forecasted demand with {safety_buffer}% safety buffer"
    
    def create_capacity_recommendation(self, region: str, service: str, target: str,
                                     forecast_data: List[float],
                                     forecast_dates: List[str],
                                     strategy: str = None) -> Optional[CapacityRecommendation]:
        """
        Create a comprehensive capacity recommendation.
        
        Args:
            region: Azure region
            service: Service type (Container, VM, Storage)
            target: Target metric (usage_cpu, usage_storage)
            forecast_data: List of forecasted percentage values
            forecast_dates: List of forecast dates
            strategy: Capacity planning strategy (optional)
            
        Returns:
            CapacityRecommendation object or None if data not available
        """
        # Get capacity information
        capacity_info = self.get_capacity_info(region, service)
        if not capacity_info:
            logger.warning(f"No capacity info available for {region}/{service}")
            return None
        
        # Use default strategy if not provided
        if strategy is None:
            strategy = self.business_rules.get('default_strategy', 'peak_based')
        
        # Calculate required capacity
        required_capacity, metrics = self.calculate_required_capacity(
            forecast_data, capacity_info, strategy
        )
        
        # Get current capacity based on target type
        if target == 'usage_cpu':
            current_units = capacity_info['current_units']
            capacity_per_unit = capacity_info['cpu_capacity_per_unit']
            available_capacity = current_units * capacity_per_unit * capacity_info.get('max_utilization_threshold', 100.0)
        elif target == 'usage_storage':
            current_units = capacity_info['current_units']
            capacity_per_unit = capacity_info['storage_capacity_per_unit']
            available_capacity = current_units * capacity_per_unit * capacity_info.get('max_utilization_threshold', 100.0)
        else:
            logger.warning(f"Unknown target type: {target}")
            return None
        
        # Calculate gaps and adjustments
        gap_absolute = required_capacity - available_capacity
        gap_percentage = (gap_absolute / available_capacity) * 100.0 if available_capacity > 0 else 0.0
        
        # Assess risk and determine action
        risk_level = self.assess_risk_level(gap_percentage)
        action_type = self.determine_action_type(gap_percentage, risk_level)
        
        # Calculate unit adjustments and cost impact
        unit_adjustment, cost_impact = self.calculate_unit_adjustment(
            gap_percentage, capacity_info['current_units'], capacity_info
        )
        
        # Generate recommendation text and reason
        recommendation_text = self.generate_recommendation_text(
            gap_percentage, unit_adjustment, capacity_info, risk_level
        )
        reason = self.generate_reason(required_capacity, available_capacity, metrics, capacity_info)
        
        # Calculate confidence score based on forecast variance
        forecast_cv = metrics['forecast_std'] / metrics['forecast_mean'] if metrics['forecast_mean'] > 0 else 1.0
        confidence_score = max(0.1, min(1.0, 1.0 - forecast_cv))  # Lower variance = higher confidence
        
        # Build forecast period string
        if forecast_dates:
            forecast_period = f"{forecast_dates[0]} to {forecast_dates[-1]}"
        else:
            forecast_period = f"{datetime.now().date()} to {(datetime.now() + timedelta(days=30)).date()}"
        
        return CapacityRecommendation(
            region=region,
            service=service,
            target=target,
            forecast_period=forecast_period,
            forecast_peak_demand=metrics['forecast_max'],
            forecast_avg_demand=metrics['forecast_mean'],
            available_capacity=available_capacity,
            required_capacity=required_capacity,
            gap_absolute=gap_absolute,
            gap_percentage=gap_percentage,
            risk_level=risk_level,
            action_type=action_type,
            recommended_adjustment=recommendation_text,
            reason=reason,
            cost_impact_monthly=cost_impact,
            confidence_score=confidence_score,
            additional_metrics={
                **metrics,
                'current_units': capacity_info['current_units'],
                'unit_type': capacity_info['unit_type'],
                'cost_per_unit_monthly': capacity_info['cost_per_unit_monthly'],
                'unit_adjustment': unit_adjustment
            }
        )
    
    def get_all_capacity_summary(self) -> Dict[str, Any]:
        """Get summary of current capacity across all regions and services."""
        summary = {
            'total_regions': len(self.capacity_data),
            'total_services': 0,
            'capacity_by_region': {},
            'capacity_by_service': {},
            'total_monthly_cost': 0.0,
            'last_updated': datetime.now().isoformat()
        }
        
        for region, services in self.capacity_data.items():
            summary['capacity_by_region'][region] = {}
            region_cost = 0.0
            
            for service, capacity_info in services.items():
                summary['total_services'] += 1
                units = capacity_info['current_units']
                cost = units * capacity_info.get('cost_per_unit_monthly', 0.0)
                
                summary['capacity_by_region'][region][service] = {
                    'current_units': units,
                    'unit_type': capacity_info['unit_type'],
                    'monthly_cost': cost
                }
                
                # Global service summary
                if service not in summary['capacity_by_service']:
                    summary['capacity_by_service'][service] = {
                        'total_units': 0,
                        'total_monthly_cost': 0.0,
                        'regions': []
                    }
                
                summary['capacity_by_service'][service]['total_units'] += units
                summary['capacity_by_service'][service]['total_monthly_cost'] += cost
                summary['capacity_by_service'][service]['regions'].append(region)
                
                region_cost += cost
            
            summary['capacity_by_region'][region]['total_monthly_cost'] = region_cost
            summary['total_monthly_cost'] += region_cost
        
        return summary


# Global capacity planning engine instance
capacity_engine: Optional[CapacityPlanningEngine] = None

def get_capacity_engine() -> CapacityPlanningEngine:
    """Get the global capacity planning engine instance."""
    global capacity_engine
    if capacity_engine is None:
        capacity_engine = CapacityPlanningEngine()
    return capacity_engine