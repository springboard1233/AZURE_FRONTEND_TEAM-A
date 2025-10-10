"""
Alerting System for Model Monitoring
Provides alert management, notifications, and escalation for critical model issues.
"""

import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"

class AlertStatus(Enum):
    """Alert status tracking"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class NotificationChannel(Enum):
    """Available notification channels"""
    EMAIL = "email"
    LOG = "log"
    WEBHOOK = "webhook"

@dataclass
class Alert:
    """Represents a system alert"""
    alert_id: str
    level: AlertLevel
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    region: Optional[str] = None
    service: Optional[str] = None
    target: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    suppressed_until: Optional[datetime] = None
    notification_sent: bool = False
    escalation_count: int = 0

@dataclass
class NotificationConfig:
    """Configuration for notifications"""
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    to_emails: List[str] = None
    
    # Alert thresholds
    critical_escalation_minutes: int = 30
    warning_escalation_minutes: int = 60
    max_escalations: int = 3
    
    # Suppression settings
    duplicate_suppression_minutes: int = 30
    maintenance_mode: bool = False

class AlertManager:
    """
    Manages alerts, notifications, and escalation for model monitoring
    """
    
    def __init__(self, alerts_path: Optional[Path] = None):
        """
        Initialize AlertManager
        
        Args:
            alerts_path: Path to store alert data
        """
        # Set up paths
        if alerts_path is None:
            alerts_path = Path(__file__).parent.parent / "alerts"
        
        self.alerts_path = Path(alerts_path)
        self.alerts_path.mkdir(parents=True, exist_ok=True)
        
        self.active_alerts_file = self.alerts_path / "active_alerts.json"
        self.alert_history_file = self.alerts_path / "alert_history.json"
        self.config_file = self.alerts_path / "notification_config.json"
        
        # Load configuration
        self.config = self.load_notification_config()
        if self.config.to_emails is None:
            self.config.to_emails = []
        
        # Load active alerts
        self.active_alerts: Dict[str, Alert] = self.load_active_alerts()
        
        logger.info(f"AlertManager initialized with {len(self.active_alerts)} active alerts")
    
    def load_notification_config(self) -> NotificationConfig:
        """Load notification configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_dict = json.load(f)
                    return NotificationConfig(**config_dict)
            else:
                # Create default config
                config = NotificationConfig()
                self.save_notification_config(config)
                return config
        except Exception as e:
            logger.error(f"Error loading notification config: {e}")
            return NotificationConfig()
    
    def save_notification_config(self, config: NotificationConfig) -> None:
        """Save notification configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(config), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving notification config: {e}")
    
    def load_active_alerts(self) -> Dict[str, Alert]:
        """Load active alerts from disk"""
        try:
            if self.active_alerts_file.exists():
                with open(self.active_alerts_file, 'r') as f:
                    alerts_data = json.load(f)
                
                alerts = {}
                for alert_id, alert_dict in alerts_data.items():
                    # Convert datetime strings back to datetime objects
                    for key in ['created_at', 'updated_at', 'suppressed_until']:
                        if alert_dict.get(key):
                            alert_dict[key] = datetime.fromisoformat(alert_dict[key])
                    
                    # Convert enums
                    alert_dict['level'] = AlertLevel(alert_dict['level'])
                    alert_dict['status'] = AlertStatus(alert_dict['status'])
                    
                    alerts[alert_id] = Alert(**alert_dict)
                
                return alerts
            else:
                return {}
        except Exception as e:
            logger.error(f"Error loading active alerts: {e}")
            return {}
    
    def save_active_alerts(self) -> None:
        """Save active alerts to disk"""
        try:
            alerts_data = {}
            for alert_id, alert in self.active_alerts.items():
                alert_dict = asdict(alert)
                
                # Convert datetime objects to strings
                for key, value in alert_dict.items():
                    if isinstance(value, datetime):
                        alert_dict[key] = value.isoformat() if value else None
                    elif isinstance(value, (AlertLevel, AlertStatus)):
                        alert_dict[key] = value.value
                
                alerts_data[alert_id] = alert_dict
            
            with open(self.active_alerts_file, 'w') as f:
                json.dump(alerts_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving active alerts: {e}")
    
    def generate_alert_id(self, alert_type: str, region: str = None, service: str = None, target: str = None) -> str:
        """Generate unique alert ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        components = [alert_type, timestamp]
        
        if region:
            components.insert(1, region)
        if service:
            components.insert(-1, service)
        if target:
            components.insert(-1, target)
        
        return "_".join(components)
    
    def create_alert(self, level: AlertLevel, alert_type: str, message: str,
                    details: Optional[Dict[str, Any]] = None,
                    region: Optional[str] = None, service: Optional[str] = None,
                    target: Optional[str] = None) -> Alert:
        """
        Create a new alert
        
        Args:
            level: Alert severity level
            alert_type: Type of alert
            message: Alert message
            details: Additional alert details
            region: Azure region (optional)
            service: Service type (optional)
            target: Target metric (optional)
            
        Returns:
            Created Alert object
        """
        # Check for duplicate alerts (suppression)
        if self.should_suppress_alert(alert_type, region, service, target):
            logger.info(f"Alert suppressed: {alert_type} for {region}/{service}/{target}")
            return None
        
        alert_id = self.generate_alert_id(alert_type, region, service, target)
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            type=alert_type,
            message=message,
            details=details,
            region=region,
            service=service,
            target=target,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add to active alerts
        self.active_alerts[alert_id] = alert
        self.save_active_alerts()
        
        # Send notifications
        self.send_notifications(alert)
        
        logger.info(f"Created alert {alert_id}: {level.value} - {alert_type}")
        return alert
    
    def should_suppress_alert(self, alert_type: str, region: str = None, 
                             service: str = None, target: str = None) -> bool:
        """
        Check if alert should be suppressed due to duplicates or maintenance mode
        
        Args:
            alert_type: Type of alert
            region: Azure region
            service: Service type
            target: Target metric
            
        Returns:
            True if alert should be suppressed
        """
        # Check maintenance mode
        if self.config.maintenance_mode:
            return True
        
        # Check for recent similar alerts
        cutoff_time = datetime.now() - timedelta(minutes=self.config.duplicate_suppression_minutes)
        
        for alert in self.active_alerts.values():
            if (alert.type == alert_type and
                alert.region == region and
                alert.service == service and
                alert.target == target and
                alert.created_at >= cutoff_time and
                alert.status == AlertStatus.ACTIVE):
                return True
        
        return False
    
    def send_notifications(self, alert: Alert) -> None:
        """
        Send notifications for an alert
        
        Args:
            alert: Alert to send notifications for
        """
        try:
            # Always log the alert
            self.send_log_notification(alert)
            
            # Send email notifications for WARNING and CRITICAL
            if alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
                self.send_email_notification(alert)
            
            # Mark as notification sent
            alert.notification_sent = True
            alert.updated_at = datetime.now()
            self.save_active_alerts()
            
        except Exception as e:
            logger.error(f"Error sending notifications for alert {alert.alert_id}: {e}")
    
    def send_log_notification(self, alert: Alert) -> None:
        """Send log notification"""
        log_message = f"ALERT [{alert.level.value.upper()}] {alert.type}: {alert.message}"
        
        if alert.region or alert.service or alert.target:
            model_info = f" (Model: {alert.region}/{alert.service}/{alert.target})"
            log_message += model_info
        
        if alert.level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(log_message)
        elif alert.level == AlertLevel.ERROR:
            logger.error(log_message)
        else:
            logger.info(log_message)
    
    def send_email_notification(self, alert: Alert) -> bool:
        """
        Send email notification
        
        Args:
            alert: Alert to send email for
            
        Returns:
            True if email sent successfully
        """
        try:
            if not self.config.smtp_username or not self.config.to_emails:
                logger.warning("Email configuration incomplete, skipping email notification")
                return False
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.config.from_email or self.config.smtp_username
            msg['To'] = ', '.join(self.config.to_emails)
            msg['Subject'] = f"[ALERT] {alert.level.value.upper()}: {alert.type}"
            
            # Create email body
            body = self.create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification for alert {alert.alert_id}: {e}")
            return False
    
    def create_email_body(self, alert: Alert) -> str:
        """Create HTML email body for alert"""
        # Color based on alert level
        color_map = {
            AlertLevel.CRITICAL: "#d73027",
            AlertLevel.WARNING: "#fc8d59",
            AlertLevel.ERROR: "#e31a1c",
            AlertLevel.INFO: "#2166ac"
        }
        
        color = color_map.get(alert.level, "#666666")
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: {color}; margin-top: 0;">
                    {alert.level.value.upper()} Alert: {alert.type}
                </h2>
                
                <p><strong>Message:</strong> {alert.message}</p>
                
                <table style="border-collapse: collapse; width: 100%; margin: 15px 0;">
                    <tr>
                        <td style="padding: 8px; background-color: #e9e9e9;"><strong>Alert ID:</strong></td>
                        <td style="padding: 8px;">{alert.alert_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; background-color: #e9e9e9;"><strong>Created:</strong></td>
                        <td style="padding: 8px;">{alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; background-color: #e9e9e9;"><strong>Status:</strong></td>
                        <td style="padding: 8px;">{alert.status.value}</td>
                    </tr>
        """
        
        # Add model information if available
        if alert.region or alert.service or alert.target:
            html_body += f"""
                    <tr>
                        <td style="padding: 8px; background-color: #e9e9e9;"><strong>Model:</strong></td>
                        <td style="padding: 8px;">{alert.region}/{alert.service}/{alert.target}</td>
                    </tr>
            """
        
        html_body += """
                </table>
        """
        
        # Add details if available
        if alert.details:
            html_body += """
                <h3>Alert Details:</h3>
                <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; font-family: monospace;">
            """
            
            for key, value in alert.details.items():
                html_body += f"<p><strong>{key}:</strong> {value}</p>"
            
            html_body += """
                </div>
            """
        
        html_body += """
                <hr style="margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">
                    This is an automated alert from the Azure Demand Forecasting System.<br>
                    Please investigate and acknowledge this alert promptly.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def process_monitoring_alerts(self, monitoring_results: Dict[str, Any]) -> List[Alert]:
        """
        Process monitoring results and create alerts
        
        Args:
            monitoring_results: Results from monitoring checks
            
        Returns:
            List of created alerts
        """
        created_alerts = []
        
        try:
            # Process alerts from monitoring results
            if 'alerts' in monitoring_results:
                for alert_data in monitoring_results['alerts']:
                    level = AlertLevel(alert_data.get('level', 'info'))
                    alert_type = alert_data.get('type', 'monitoring')
                    message = alert_data.get('message', 'Monitoring alert')
                    details = alert_data.get('details', {})
                    
                    alert = self.create_alert(
                        level=level,
                        alert_type=alert_type,
                        message=message,
                        details=details
                    )
                    
                    if alert:
                        created_alerts.append(alert)
            
            # Process specific monitoring results
            if monitoring_results.get('health_check', {}).get('system_status') == 'critical':
                alert = self.create_alert(
                    level=AlertLevel.CRITICAL,
                    alert_type='system_health',
                    message='System health is critical',
                    details=monitoring_results.get('health_check')
                )
                if alert:
                    created_alerts.append(alert)
            
            if monitoring_results.get('drift_check', {}).get('drift_detected'):
                drift_models = monitoring_results['drift_check'].get('high_drift_models', [])
                if drift_models:
                    alert = self.create_alert(
                        level=AlertLevel.WARNING,
                        alert_type='data_drift',
                        message=f'High data drift detected in {len(drift_models)} models',
                        details={'models': drift_models}
                    )
                    if alert:
                        created_alerts.append(alert)
            
            if monitoring_results.get('performance_check', {}).get('performance_degradation_detected'):
                degraded_models = monitoring_results['performance_check'].get('degraded_models', [])
                alert = self.create_alert(
                    level=AlertLevel.WARNING,
                    alert_type='performance_degradation',
                    message=f'Performance degradation detected in {len(degraded_models)} models',
                    details={'models': degraded_models}
                )
                if alert:
                    created_alerts.append(alert)
            
        except Exception as e:
            logger.error(f"Error processing monitoring alerts: {e}")
        
        return created_alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: Alert identifier
            acknowledged_by: Who acknowledged the alert
            
        Returns:
            True if acknowledged successfully
        """
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.now()
                self.save_active_alerts()
                
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
            else:
                logger.warning(f"Alert {alert_id} not found for acknowledgment")
                return False
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """
        Resolve an alert
        
        Args:
            alert_id: Alert identifier
            resolved_by: Who resolved the alert
            
        Returns:
            True if resolved successfully
        """
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_by = resolved_by
                alert.updated_at = datetime.now()
                
                # Move to history and remove from active
                self.move_to_history(alert)
                del self.active_alerts[alert_id]
                self.save_active_alerts()
                
                logger.info(f"Alert {alert_id} resolved by {resolved_by}")
                return True
            else:
                logger.warning(f"Alert {alert_id} not found for resolution")
                return False
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            return False
    
    def move_to_history(self, alert: Alert) -> None:
        """Move alert to history file"""
        try:
            # Load existing history
            history = []
            if self.alert_history_file.exists():
                with open(self.alert_history_file, 'r') as f:
                    history = json.load(f)
            
            # Convert alert to dict for storage
            alert_dict = asdict(alert)
            for key, value in alert_dict.items():
                if isinstance(value, datetime):
                    alert_dict[key] = value.isoformat() if value else None
                elif isinstance(value, (AlertLevel, AlertStatus)):
                    alert_dict[key] = value.value
            
            # Add to history
            history.append(alert_dict)
            
            # Keep only last 1000 alerts in history
            if len(history) > 1000:
                history = history[-1000:]
            
            # Save history
            with open(self.alert_history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error moving alert to history: {e}")
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """
        Get active alerts with optional filtering
        
        Args:
            level: Filter by alert level
            
        Returns:
            List of active alerts
        """
        alerts = []
        
        for alert in self.active_alerts.values():
            if level is None or alert.level == level:
                alert_dict = asdict(alert)
                
                # Convert datetime objects to strings
                for key, value in alert_dict.items():
                    if isinstance(value, datetime):
                        alert_dict[key] = value.isoformat() if value else None
                    elif isinstance(value, (AlertLevel, AlertStatus)):
                        alert_dict[key] = value.value
                
                alerts.append(alert_dict)
        
        # Sort by creation time (newest first)
        alerts.sort(key=lambda x: x['created_at'], reverse=True)
        return alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status"""
        level_counts = {level.value: 0 for level in AlertLevel}
        status_counts = {status.value: 0 for status in AlertStatus}
        
        for alert in self.active_alerts.values():
            level_counts[alert.level.value] += 1
            status_counts[alert.status.value] += 1
        
        return {
            "total_active_alerts": len(self.active_alerts),
            "alerts_by_level": level_counts,
            "alerts_by_status": status_counts,
            "last_updated": datetime.now().isoformat()
        }
    
    def cleanup_resolved_alerts(self, days_old: int = 7) -> int:
        """
        Clean up old resolved alerts
        
        Args:
            days_old: Remove alerts older than this many days
            
        Returns:
            Number of alerts cleaned up
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        
        alerts_to_remove = []
        for alert_id, alert in self.active_alerts.items():
            if (alert.status == AlertStatus.RESOLVED and 
                alert.updated_at < cutoff_date):
                alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.active_alerts[alert_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            self.save_active_alerts()
            logger.info(f"Cleaned up {cleaned_count} old resolved alerts")
        
        return cleaned_count

# Global alert manager instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager

if __name__ == "__main__":
    # Test alerting system
    alert_manager = get_alert_manager()
    
    print("Alerting System Test")
    print(f"Active alerts: {len(alert_manager.active_alerts)}")
    
    # Create test alert
    test_alert = alert_manager.create_alert(
        level=AlertLevel.WARNING,
        alert_type="test",
        message="This is a test alert",
        details={"test": True}
    )
    
    if test_alert:
        print(f"Created test alert: {test_alert.alert_id}")
        
        # Acknowledge and resolve
        alert_manager.acknowledge_alert(test_alert.alert_id, "test_user")
        alert_manager.resolve_alert(test_alert.alert_id, "test_user")
        print("Test alert acknowledged and resolved")
    
    summary = alert_manager.get_alert_summary()
    print(f"Alert summary: {summary}")