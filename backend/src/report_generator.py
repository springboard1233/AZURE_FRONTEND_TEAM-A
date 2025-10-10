"""
Automated report generation for Azure demand forecasting system
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import csv
from dataclasses import dataclass, asdict
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from database import get_database_manager, ForecastRun, Forecast, AccuracyMetric, CapacityAction
from accuracy_tracker import get_accuracy_tracker
from capacity_planning import get_capacity_engine
from model_manager import get_model_manager
from sqlalchemy import and_, func, desc

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DailySummary:
    """Daily forecast and capacity summary"""
    date: str
    total_forecasts_generated: int
    regions_with_shortages: List[Dict[str, Any]]
    urgent_capacity_actions: List[Dict[str, Any]]
    top_risks: List[Dict[str, Any]]
    recommended_adjustments: List[Dict[str, Any]]
    system_health: Dict[str, Any]

@dataclass
class WeeklyReport:
    """Weekly accuracy and performance report"""
    week_start: str
    week_end: str
    forecast_accuracy_trends: Dict[str, Any]
    capacity_changes_executed: List[Dict[str, Any]]
    cost_impact_summary: Dict[str, Any]
    model_performance: Dict[str, Any]
    recommendations_summary: List[Dict[str, Any]]

class ReportGenerator:
    """
    Automated report generation system that creates:
    1. Daily summaries with capacity shortages and urgent actions
    2. Weekly reports with accuracy trends and cost analysis
    3. Export capabilities (CSV, JSON, HTML)
    """
    
    def __init__(self, reports_dir: str = None):
        """
        Initialize report generator
        
        Args:
            reports_dir: Directory to store generated reports
        """
        self.db_manager = get_database_manager()
        self.accuracy_tracker = get_accuracy_tracker()
        self.capacity_engine = get_capacity_engine()
        self.model_manager = get_model_manager()
        
        # Set up reports directory
        if reports_dir is None:
            self.reports_dir = Path(__file__).parent.parent / "reports" / "automated"
        else:
            self.reports_dir = Path(reports_dir)
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Reports will be saved to: {self.reports_dir}")
    
    def generate_daily_summary(self, target_date: datetime = None) -> DailySummary:
        """
        Generate daily summary report
        
        Args:
            target_date: Date to generate summary for (default: yesterday)
            
        Returns:
            DailySummary object
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        logger.info(f"Generating daily summary for {target_date.date()}")
        
        session = self.db_manager.get_session()
        
        try:
            # Get forecast runs for the target date
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            forecast_runs = session.query(ForecastRun).filter(
                and_(
                    ForecastRun.run_time >= start_of_day,
                    ForecastRun.run_time < end_of_day
                )
            ).all()
            
            total_forecasts = sum(run.total_forecasts for run in forecast_runs)
            
            # Get capacity recommendations for current day
            available_combinations = self.model_manager.get_available_combinations()
            
            regions_with_shortages = []
            urgent_capacity_actions = []
            top_risks = []
            recommended_adjustments = []
            
            # Generate forecast dates for capacity analysis
            forecast_dates = [(datetime.now().date() + timedelta(days=i+1)).isoformat() 
                             for i in range(30)]
            
            for region, service, target in available_combinations:
                try:
                    # Get current forecast
                    forecast_result = self.model_manager.get_forecast(region, service, target, 30)
                    if not forecast_result:
                        continue
                    
                    # Generate capacity recommendation
                    recommendation = self.capacity_engine.create_capacity_recommendation(
                        region=region,
                        service=service,
                        target=target,
                        forecast_data=forecast_result['forecast'],
                        forecast_dates=forecast_dates
                    )
                    
                    if not recommendation:
                        continue
                    
                    # Categorize by risk level and action type
                    rec_data = {
                        "region": region,
                        "service": service,
                        "target": target,
                        "risk_level": recommendation.risk_level.value,
                        "action_type": recommendation.action_type.value,
                        "gap_percentage": round(recommendation.gap_percentage, 2),
                        "cost_impact": round(recommendation.cost_impact_monthly, 2),
                        "recommendation": recommendation.recommended_adjustment
                    }
                    
                    # Add to appropriate categories
                    if recommendation.gap_percentage > 0:  # Shortage
                        regions_with_shortages.append(rec_data)
                    
                    if recommendation.risk_level.value in ['critical', 'high']:
                        if recommendation.action_type.value == 'scale_up':
                            urgent_capacity_actions.append(rec_data)
                        top_risks.append(rec_data)
                    
                    if recommendation.action_type.value != 'maintain':
                        recommended_adjustments.append(rec_data)
                        
                except Exception as e:
                    logger.warning(f"Error processing {region}/{service}/{target}: {e}")
                    continue
            
            # Sort by priority
            regions_with_shortages.sort(key=lambda x: x['gap_percentage'], reverse=True)
            urgent_capacity_actions.sort(key=lambda x: x['cost_impact'], reverse=True)
            top_risks.sort(key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x['risk_level']], reverse=True)
            
            # System health metrics
            successful_runs = sum(1 for run in forecast_runs if run.status == 'completed')
            failed_runs = len(forecast_runs) - successful_runs
            
            system_health = {
                "total_runs": len(forecast_runs),
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": (successful_runs / len(forecast_runs)) * 100 if forecast_runs else 0,
                "total_forecasts_generated": total_forecasts,
                "models_available": len(available_combinations)
            }
            
            summary = DailySummary(
                date=target_date.date().isoformat(),
                total_forecasts_generated=total_forecasts,
                regions_with_shortages=regions_with_shortages[:10],  # Top 10
                urgent_capacity_actions=urgent_capacity_actions[:5],  # Top 5
                top_risks=top_risks[:10],  # Top 10
                recommended_adjustments=recommended_adjustments[:15],  # Top 15
                system_health=system_health
            )
            
            logger.info(f"Daily summary generated: {len(regions_with_shortages)} shortages, "
                       f"{len(urgent_capacity_actions)} urgent actions")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def generate_weekly_report(self, week_start: datetime = None) -> WeeklyReport:
        """
        Generate weekly accuracy and performance report
        
        Args:
            week_start: Start of week to analyze (default: last Monday)
            
        Returns:
            WeeklyReport object
        """
        if week_start is None:
            # Get last Monday
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday + 7)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_end = week_start + timedelta(days=7)
        
        logger.info(f"Generating weekly report for {week_start.date()} to {week_end.date()}")
        
        session = self.db_manager.get_session()
        
        try:
            # Get accuracy metrics for the week
            accuracy_metrics = session.query(AccuracyMetric).filter(
                and_(
                    AccuracyMetric.calculated_at >= week_start,
                    AccuracyMetric.calculated_at < week_end
                )
            ).all()
            
            # Process accuracy trends
            accuracy_by_type = {}
            for metric in accuracy_metrics:
                if metric.metric_type not in accuracy_by_type:
                    accuracy_by_type[metric.metric_type] = []
                accuracy_by_type[metric.metric_type].append(metric.metric_value)
            
            forecast_accuracy_trends = {}
            for metric_type, values in accuracy_by_type.items():
                if values:
                    forecast_accuracy_trends[metric_type] = {
                        "count": len(values),
                        "average": sum(values) / len(values),
                        "best": max(values) if metric_type == 'ACCURACY_SCORE' else min(values),
                        "worst": min(values) if metric_type == 'ACCURACY_SCORE' else max(values)
                    }
            
            # Get capacity actions (simulated for now)
            capacity_changes_executed = []
            
            # Calculate cost impact summary
            total_cost_impact = 0.0
            cost_savings = 0.0
            cost_increases = 0.0
            
            # Get recent capacity recommendations for cost analysis
            available_combinations = self.model_manager.get_available_combinations()
            forecast_dates = [(datetime.now().date() + timedelta(days=i+1)).isoformat() 
                             for i in range(30)]
            
            for region, service, target in available_combinations[:10]:  # Limit for performance
                try:
                    forecast_result = self.model_manager.get_forecast(region, service, target, 30)
                    if not forecast_result:
                        continue
                    
                    recommendation = self.capacity_engine.create_capacity_recommendation(
                        region=region,
                        service=service,
                        target=target,
                        forecast_data=forecast_result['forecast'],
                        forecast_dates=forecast_dates
                    )
                    
                    if recommendation:
                        total_cost_impact += recommendation.cost_impact_monthly
                        if recommendation.cost_impact_monthly > 0:
                            cost_increases += recommendation.cost_impact_monthly
                        else:
                            cost_savings += abs(recommendation.cost_impact_monthly)
                            
                except Exception as e:
                    logger.warning(f"Error calculating cost for {region}/{service}/{target}: {e}")
                    continue
            
            cost_impact_summary = {
                "total_cost_impact_monthly": round(total_cost_impact, 2),
                "potential_cost_increases": round(cost_increases, 2),
                "potential_cost_savings": round(cost_savings, 2),
                "net_impact": round(total_cost_impact, 2)
            }
            
            # Model performance summary
            model_performance = {
                "total_models": len(available_combinations),
                "accuracy_metrics_calculated": len(accuracy_metrics),
                "average_accuracy_score": forecast_accuracy_trends.get('ACCURACY_SCORE', {}).get('average', 0.0)
            }
            
            # Recommendations summary
            recommendations_summary = []
            for region, service, target in available_combinations[:5]:  # Top 5 for summary
                try:
                    forecast_result = self.model_manager.get_forecast(region, service, target, 30)
                    if forecast_result:
                        recommendation = self.capacity_engine.create_capacity_recommendation(
                            region, service, target, forecast_result['forecast'], forecast_dates
                        )
                        if recommendation and recommendation.action_type.value != 'maintain':
                            recommendations_summary.append({
                                "region": region,
                                "service": service,
                                "target": target,
                                "action": recommendation.action_type.value,
                                "risk_level": recommendation.risk_level.value,
                                "cost_impact": round(recommendation.cost_impact_monthly, 2)
                            })
                except:
                    continue
            
            report = WeeklyReport(
                week_start=week_start.date().isoformat(),
                week_end=week_end.date().isoformat(),
                forecast_accuracy_trends=forecast_accuracy_trends,
                capacity_changes_executed=capacity_changes_executed,
                cost_impact_summary=cost_impact_summary,
                model_performance=model_performance,
                recommendations_summary=recommendations_summary
            )
            
            logger.info(f"Weekly report generated with {len(accuracy_metrics)} accuracy metrics")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            raise
        finally:
            self.db_manager.close_session(session)
    
    def export_daily_summary_csv(self, summary: DailySummary, filename: str = None) -> str:
        """
        Export daily summary to CSV format
        
        Args:
            summary: DailySummary object
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"daily_summary_{summary.date}.csv"
        
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Daily Capacity Planning Summary', summary.date])
            writer.writerow([])
            
            # System Health
            writer.writerow(['System Health'])
            for key, value in summary.system_health.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])
            
            # Regions with Shortages
            writer.writerow(['Regions with Capacity Shortages'])
            writer.writerow(['Region', 'Service', 'Target', 'Gap %', 'Risk Level', 'Cost Impact'])
            for shortage in summary.regions_with_shortages:
                writer.writerow([
                    shortage['region'],
                    shortage['service'],
                    shortage['target'],
                    shortage['gap_percentage'],
                    shortage['risk_level'],
                    shortage['cost_impact']
                ])
            writer.writerow([])
            
            # Urgent Actions
            writer.writerow(['Urgent Capacity Actions Required'])
            writer.writerow(['Region', 'Service', 'Target', 'Action', 'Cost Impact', 'Recommendation'])
            for action in summary.urgent_capacity_actions:
                writer.writerow([
                    action['region'],
                    action['service'],
                    action['target'],
                    action['action_type'],
                    action['cost_impact'],
                    action['recommendation']
                ])
        
        logger.info(f"Daily summary exported to CSV: {filepath}")
        return str(filepath)
    
    def export_weekly_report_json(self, report: WeeklyReport, filename: str = None) -> str:
        """
        Export weekly report to JSON format
        
        Args:
            report: WeeklyReport object
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"weekly_report_{report.week_start}_to_{report.week_end}.json"
        
        filepath = self.reports_dir / filename
        
        # Convert dataclass to dictionary
        report_dict = asdict(report)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(report_dict, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Weekly report exported to JSON: {filepath}")
        return str(filepath)
    
    def generate_html_summary(self, summary: DailySummary, filename: str = None) -> str:
        """
        Generate HTML version of daily summary
        
        Args:
            summary: DailySummary object
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"daily_summary_{summary.date}.html"
        
        filepath = self.reports_dir / filename
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Daily Capacity Planning Summary - {summary.date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2E86AB; }}
        h2 {{ color: #A23B72; border-bottom: 2px solid #F18F01; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .high {{ color: #f57c00; font-weight: bold; }}
        .medium {{ color: #fbc02d; }}
        .low {{ color: #388e3c; }}
        .summary-box {{ background-color: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Azure Demand Forecasting - Daily Summary</h1>
    <p><strong>Date:</strong> {summary.date}</p>
    
    <div class="summary-box">
        <h2>System Health</h2>
        <p><strong>Total Forecasts Generated:</strong> {summary.total_forecasts_generated}</p>
        <p><strong>Success Rate:</strong> {summary.system_health['success_rate']:.1f}%</p>
        <p><strong>Models Available:</strong> {summary.system_health['models_available']}</p>
    </div>
    
    <h2>Regions with Capacity Shortages ({len(summary.regions_with_shortages)})</h2>
    <table>
        <tr>
            <th>Region</th>
            <th>Service</th>
            <th>Target</th>
            <th>Gap %</th>
            <th>Risk Level</th>
            <th>Monthly Cost Impact</th>
        </tr>
"""
        
        for shortage in summary.regions_with_shortages:
            risk_class = shortage['risk_level']
            html_content += f"""
        <tr>
            <td>{shortage['region']}</td>
            <td>{shortage['service']}</td>
            <td>{shortage['target']}</td>
            <td>{shortage['gap_percentage']}%</td>
            <td class="{risk_class}">{shortage['risk_level'].upper()}</td>
            <td>${shortage['cost_impact']:.2f}</td>
        </tr>
"""
        
        html_content += f"""
    </table>
    
    <h2>Urgent Capacity Actions Required ({len(summary.urgent_capacity_actions)})</h2>
    <table>
        <tr>
            <th>Region</th>
            <th>Service</th>
            <th>Action</th>
            <th>Cost Impact</th>
            <th>Recommendation</th>
        </tr>
"""
        
        for action in summary.urgent_capacity_actions:
            html_content += f"""
        <tr>
            <td>{action['region']}</td>
            <td>{action['service']}</td>
            <td>{action['action_type']}</td>
            <td>${action['cost_impact']:.2f}</td>
            <td>{action['recommendation']}</td>
        </tr>
"""
        
        html_content += """
    </table>
    
    <p><em>Generated on """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</em></p>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write(html_content)
        
        logger.info(f"HTML summary generated: {filepath}")
        return str(filepath)
    
    def run_daily_report_generation(self) -> Dict[str, Any]:
        """
        Run complete daily report generation workflow
        
        Returns:
            Dictionary with generation results
        """
        try:
            # Generate daily summary
            summary = self.generate_daily_summary()
            
            # Export in multiple formats
            csv_path = self.export_daily_summary_csv(summary)
            html_path = self.generate_html_summary(summary)
            
            # JSON export for API consumption
            json_path = self.reports_dir / f"daily_summary_{summary.date}.json"
            with open(json_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(asdict(summary), jsonfile, indent=2, ensure_ascii=False)
            
            result = {
                "status": "success",
                "date": summary.date,
                "reports_generated": {
                    "csv": csv_path,
                    "html": html_path,
                    "json": str(json_path)
                },
                "summary_stats": {
                    "total_forecasts": summary.total_forecasts_generated,
                    "shortages_found": len(summary.regions_with_shortages),
                    "urgent_actions": len(summary.urgent_capacity_actions),
                    "system_success_rate": summary.system_health['success_rate']
                }
            }
            
            logger.info(f"Daily report generation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Daily report generation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def run_weekly_report_generation(self) -> Dict[str, Any]:
        """
        Run complete weekly report generation workflow
        
        Returns:
            Dictionary with generation results
        """
        try:
            # Generate weekly report
            report = self.generate_weekly_report()
            
            # Export in multiple formats
            json_path = self.export_weekly_report_json(report)
            
            result = {
                "status": "success",
                "week_start": report.week_start,
                "week_end": report.week_end,
                "reports_generated": {
                    "json": json_path
                },
                "summary_stats": {
                    "accuracy_metrics": len(report.forecast_accuracy_trends),
                    "cost_impact": report.cost_impact_summary['total_cost_impact_monthly'],
                    "recommendations": len(report.recommendations_summary)
                }
            }
            
            logger.info(f"Weekly report generation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            return {"status": "failed", "error": str(e)}

# Global report generator instance
_report_generator = None

def get_report_generator() -> ReportGenerator:
    """Get global report generator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator

if __name__ == "__main__":
    # Test report generation
    generator = get_report_generator()
    
    print("Generating daily report...")
    daily_result = generator.run_daily_report_generation()
    print(f"Daily report status: {daily_result['status']}")
    
    print("Generating weekly report...")
    weekly_result = generator.run_weekly_report_generation()
    print(f"Weekly report status: {weekly_result['status']}")