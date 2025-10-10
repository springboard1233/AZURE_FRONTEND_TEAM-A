"""
Model Version Management System
Provides version tracking, deployment management, and rollback capabilities.
"""

import logging
import shutil
import json
import hashlib
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

class ModelStatus(Enum):
    """Status of model versions"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    TESTING = "testing"
    FAILED = "failed"

@dataclass
class ModelVersion:
    """Represents a model version"""
    version_id: str
    region: str
    service: str
    target: str
    version_number: int
    status: ModelStatus
    created_at: datetime
    deployed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    model_path: Optional[str] = None
    backup_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, float]] = None
    deployment_notes: Optional[str] = None
    created_by: str = "system"

@dataclass
class DeploymentRecord:
    """Records model deployment events"""
    deployment_id: str
    region: str
    service: str
    target: str
    old_version_id: Optional[str]
    new_version_id: str
    deployment_type: str  # "initial", "update", "rollback"
    deployed_at: datetime
    deployed_by: str
    success: bool
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None

class ModelVersionManager:
    """
    Manages model versions, deployments, and rollbacks
    """
    
    def __init__(self, models_path: Optional[Path] = None, data_path: Optional[Path] = None):
        """
        Initialize ModelVersionManager
        
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
        self.versions_path = self.models_path / "versions"
        self.metadata_path = self.models_path / "version_metadata"
        self.deployments_path = self.models_path / "deployments"
        
        # Create directories
        self.versions_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        self.deployments_path.mkdir(parents=True, exist_ok=True)
        
        # Version tracking
        self.versions: Dict[str, List[ModelVersion]] = {}
        self.active_versions: Dict[str, ModelVersion] = {}
        
        # Load existing versions
        self.load_existing_versions()
        
        logger.info(f"ModelVersionManager initialized with {len(self.versions)} model families")
    
    def get_model_key(self, region: str, service: str, target: str) -> str:
        """Generate unique key for model family"""
        return f"{region}_{service}_{target}"
    
    def generate_version_id(self, region: str, service: str, target: str, version_number: int) -> str:
        """Generate unique version ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{region}_{service}_{target}_v{version_number}_{timestamp}"
    
    def calculate_model_hash(self, model_path: str) -> str:
        """Calculate hash of model file for integrity checking"""
        try:
            with open(model_path, 'rb') as f:
                model_bytes = f.read()
                return hashlib.sha256(model_bytes).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Error calculating model hash for {model_path}: {e}")
            return "unknown"
    
    def save_version_metadata(self, version: ModelVersion) -> None:
        """Save version metadata to disk"""
        try:
            metadata_file = self.metadata_path / f"{version.version_id}.json"
            
            # Convert to JSON-serializable format
            version_dict = asdict(version)
            for key, value in version_dict.items():
                if isinstance(value, datetime):
                    version_dict[key] = value.isoformat() if value else None
                elif isinstance(value, ModelStatus):
                    version_dict[key] = value.value
            
            with open(metadata_file, 'w') as f:
                json.dump(version_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving version metadata for {version.version_id}: {e}")
    
    def load_version_metadata(self, version_id: str) -> Optional[ModelVersion]:
        """Load version metadata from disk"""
        try:
            metadata_file = self.metadata_path / f"{version_id}.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r') as f:
                version_dict = json.load(f)
            
            # Convert back from JSON format
            for key in ['created_at', 'deployed_at', 'archived_at']:
                if version_dict.get(key):
                    version_dict[key] = datetime.fromisoformat(version_dict[key])
            
            version_dict['status'] = ModelStatus(version_dict['status'])
            
            return ModelVersion(**version_dict)
            
        except Exception as e:
            logger.error(f"Error loading version metadata for {version_id}: {e}")
            return None
    
    def load_existing_versions(self) -> None:
        """Load all existing version metadata"""
        try:
            for metadata_file in self.metadata_path.glob("*.json"):
                version_id = metadata_file.stem
                version = self.load_version_metadata(version_id)
                
                if version:
                    model_key = self.get_model_key(version.region, version.service, version.target)
                    
                    if model_key not in self.versions:
                        self.versions[model_key] = []
                    
                    self.versions[model_key].append(version)
                    
                    # Track active version
                    if version.status == ModelStatus.ACTIVE:
                        self.active_versions[model_key] = version
            
            # Sort versions by version number for each model
            for model_key in self.versions:
                self.versions[model_key].sort(key=lambda v: v.version_number, reverse=True)
                
        except Exception as e:
            logger.error(f"Error loading existing versions: {e}")
    
    def get_next_version_number(self, region: str, service: str, target: str) -> int:
        """Get next version number for a model family"""
        model_key = self.get_model_key(region, service, target)
        
        if model_key not in self.versions or not self.versions[model_key]:
            return 1
        
        max_version = max(v.version_number for v in self.versions[model_key])
        return max_version + 1
    
    def create_new_version(self, region: str, service: str, target: str, 
                          model_path: str, metadata: Optional[Dict[str, Any]] = None,
                          performance_metrics: Optional[Dict[str, float]] = None,
                          created_by: str = "system") -> ModelVersion:
        """
        Create a new model version
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            model_path: Path to model file
            metadata: Additional metadata
            performance_metrics: Model performance metrics
            created_by: Who created this version
            
        Returns:
            ModelVersion object
        """
        try:
            # Get next version number
            version_number = self.get_next_version_number(region, service, target)
            version_id = self.generate_version_id(region, service, target, version_number)
            
            # Copy model to versions directory
            version_model_path = self.versions_path / f"{version_id}.pkl"
            shutil.copy2(model_path, version_model_path)
            
            # Add file hash to metadata
            if metadata is None:
                metadata = {}
            metadata["model_hash"] = self.calculate_model_hash(str(version_model_path))
            metadata["original_path"] = model_path
            metadata["file_size"] = Path(model_path).stat().st_size
            
            # Create version object
            version = ModelVersion(
                version_id=version_id,
                region=region,
                service=service,
                target=target,
                version_number=version_number,
                status=ModelStatus.TESTING,  # Start as testing
                created_at=datetime.now(),
                model_path=str(version_model_path),
                metadata=metadata,
                performance_metrics=performance_metrics,
                created_by=created_by
            )
            
            # Save version
            self.save_version_metadata(version)
            
            # Add to tracking
            model_key = self.get_model_key(region, service, target)
            if model_key not in self.versions:
                self.versions[model_key] = []
            
            self.versions[model_key].append(version)
            self.versions[model_key].sort(key=lambda v: v.version_number, reverse=True)
            
            logger.info(f"Created new model version {version_id}")
            return version
            
        except Exception as e:
            logger.error(f"Error creating new version for {region}/{service}/{target}: {e}")
            raise
    
    def deploy_version(self, version_id: str, deployment_notes: Optional[str] = None,
                      deployed_by: str = "system") -> bool:
        """
        Deploy a model version to production
        
        Args:
            version_id: Version to deploy
            deployment_notes: Optional deployment notes
            deployed_by: Who is deploying
            
        Returns:
            True if deployment successful
        """
        try:
            # Find version
            version = None
            model_key = None
            
            for key, versions in self.versions.items():
                for v in versions:
                    if v.version_id == version_id:
                        version = v
                        model_key = key
                        break
                if version:
                    break
            
            if not version:
                logger.error(f"Version {version_id} not found")
                return False
            
            # Check if model file exists
            if not version.model_path or not Path(version.model_path).exists():
                logger.error(f"Model file not found for version {version_id}")
                return False
            
            # Get current active version for rollback
            old_version = self.active_versions.get(model_key)
            
            # Deploy to production location
            production_path = self.models_path / "arima" / f"{version.region}_{version.service}_{version.target}_arima.pkl"
            production_path.parent.mkdir(exist_ok=True)
            
            # Create backup of current production model
            backup_path = None
            if production_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.versions_path / f"backup_{version.region}_{version.service}_{version.target}_{timestamp}.pkl"
                shutil.copy2(production_path, backup_path)
                version.backup_path = str(backup_path)
            
            # Copy new version to production
            shutil.copy2(version.model_path, production_path)
            
            # Update version status
            version.status = ModelStatus.ACTIVE
            version.deployed_at = datetime.now()
            version.deployment_notes = deployment_notes
            self.save_version_metadata(version)
            
            # Update active version tracking
            if old_version:
                old_version.status = ModelStatus.ARCHIVED
                old_version.archived_at = datetime.now()
                self.save_version_metadata(old_version)
            
            self.active_versions[model_key] = version
            
            # Record deployment
            deployment_record = DeploymentRecord(
                deployment_id=f"deploy_{version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                region=version.region,
                service=version.service,
                target=version.target,
                old_version_id=old_version.version_id if old_version else None,
                new_version_id=version_id,
                deployment_type="update" if old_version else "initial",
                deployed_at=datetime.now(),
                deployed_by=deployed_by,
                success=True
            )
            
            self.save_deployment_record(deployment_record)
            
            logger.info(f"Successfully deployed version {version_id} to production")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying version {version_id}: {e}")
            
            # Record failed deployment
            try:
                deployment_record = DeploymentRecord(
                    deployment_id=f"deploy_failed_{version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    region=version.region if version else "unknown",
                    service=version.service if version else "unknown",
                    target=version.target if version else "unknown",
                    old_version_id=None,
                    new_version_id=version_id,
                    deployment_type="update",
                    deployed_at=datetime.now(),
                    deployed_by=deployed_by,
                    success=False,
                    error_message=str(e)
                )
                self.save_deployment_record(deployment_record)
            except:
                pass
            
            return False
    
    def rollback_to_version(self, region: str, service: str, target: str, 
                           target_version: Optional[str] = None,
                           rollback_reason: str = "Manual rollback",
                           deployed_by: str = "system") -> bool:
        """
        Rollback to a previous version
        
        Args:
            region: Azure region
            service: Service type
            target: Target metric
            target_version: Specific version to rollback to (None for previous)
            rollback_reason: Reason for rollback
            deployed_by: Who is performing rollback
            
        Returns:
            True if rollback successful
        """
        try:
            model_key = self.get_model_key(region, service, target)
            
            if model_key not in self.versions:
                logger.error(f"No versions found for {region}/{service}/{target}")
                return False
            
            versions = self.versions[model_key]
            current_version = self.active_versions.get(model_key)
            
            # Find target version
            rollback_version = None
            
            if target_version:
                # Rollback to specific version
                for v in versions:
                    if v.version_id == target_version:
                        rollback_version = v
                        break
            else:
                # Rollback to previous version
                archived_versions = [v for v in versions if v.status == ModelStatus.ARCHIVED]
                if archived_versions:
                    # Get most recent archived version
                    rollback_version = max(archived_versions, key=lambda v: v.version_number)
            
            if not rollback_version:
                logger.error(f"No suitable rollback version found for {region}/{service}/{target}")
                return False
            
            # Verify rollback version model exists
            if not rollback_version.model_path or not Path(rollback_version.model_path).exists():
                logger.error(f"Rollback version model file not found: {rollback_version.model_path}")
                return False
            
            # Perform rollback deployment
            production_path = self.models_path / "arima" / f"{region}_{service}_{target}_arima.pkl"
            
            # Backup current version
            if production_path.exists() and current_version:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.versions_path / f"rollback_backup_{current_version.version_id}_{timestamp}.pkl"
                shutil.copy2(production_path, backup_path)
                current_version.backup_path = str(backup_path)
                self.save_version_metadata(current_version)
            
            # Deploy rollback version
            shutil.copy2(rollback_version.model_path, production_path)
            
            # Update version statuses
            if current_version:
                current_version.status = ModelStatus.ARCHIVED
                current_version.archived_at = datetime.now()
                self.save_version_metadata(current_version)
            
            rollback_version.status = ModelStatus.ACTIVE
            rollback_version.deployed_at = datetime.now()
            self.save_version_metadata(rollback_version)
            
            # Update active tracking
            self.active_versions[model_key] = rollback_version
            
            # Record rollback deployment
            deployment_record = DeploymentRecord(
                deployment_id=f"rollback_{rollback_version.version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                region=region,
                service=service,
                target=target,
                old_version_id=current_version.version_id if current_version else None,
                new_version_id=rollback_version.version_id,
                deployment_type="rollback",
                deployed_at=datetime.now(),
                deployed_by=deployed_by,
                success=True,
                rollback_reason=rollback_reason
            )
            
            self.save_deployment_record(deployment_record)
            
            logger.info(f"Successfully rolled back {region}/{service}/{target} to version {rollback_version.version_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back {region}/{service}/{target}: {e}")
            return False
    
    def save_deployment_record(self, record: DeploymentRecord) -> None:
        """Save deployment record to disk"""
        try:
            record_file = self.deployments_path / f"{record.deployment_id}.json"
            
            # Convert to JSON-serializable format
            record_dict = asdict(record)
            record_dict['deployed_at'] = record.deployed_at.isoformat()
            
            with open(record_file, 'w') as f:
                json.dump(record_dict, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving deployment record {record.deployment_id}: {e}")
    
    def get_version_history(self, region: str, service: str, target: str) -> List[ModelVersion]:
        """Get version history for a model"""
        model_key = self.get_model_key(region, service, target)
        return self.versions.get(model_key, [])
    
    def get_active_version(self, region: str, service: str, target: str) -> Optional[ModelVersion]:
        """Get currently active version for a model"""
        model_key = self.get_model_key(region, service, target)
        return self.active_versions.get(model_key)
    
    def get_version_info(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific version"""
        version = self.load_version_metadata(version_id)
        
        if not version:
            return None
        
        # Convert to dictionary
        version_dict = asdict(version)
        
        # Convert datetime objects to strings
        for key, value in version_dict.items():
            if isinstance(value, datetime):
                version_dict[key] = value.isoformat() if value else None
            elif isinstance(value, ModelStatus):
                version_dict[key] = value.value
        
        return version_dict
    
    def list_all_versions(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all versions across all models"""
        all_versions = {}
        
        for model_key, versions in self.versions.items():
            all_versions[model_key] = []
            
            for version in versions:
                version_dict = asdict(version)
                
                # Convert datetime objects to strings
                for key, value in version_dict.items():
                    if isinstance(value, datetime):
                        version_dict[key] = value.isoformat() if value else None
                    elif isinstance(value, ModelStatus):
                        version_dict[key] = value.value
                
                all_versions[model_key].append(version_dict)
        
        return all_versions
    
    def get_deployment_history(self, region: str = None, service: str = None, 
                              target: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get deployment history with optional filtering"""
        try:
            deployment_files = list(self.deployments_path.glob("*.json"))
            deployment_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            deployments = []
            
            for deployment_file in deployment_files[:limit * 2]:  # Load more than needed for filtering
                try:
                    with open(deployment_file, 'r') as f:
                        deployment_dict = json.load(f)
                    
                    # Apply filters
                    if region and deployment_dict.get('region') != region:
                        continue
                    if service and deployment_dict.get('service') != service:
                        continue
                    if target and deployment_dict.get('target') != target:
                        continue
                    
                    deployments.append(deployment_dict)
                    
                    if len(deployments) >= limit:
                        break
                        
                except Exception as e:
                    logger.error(f"Error loading deployment record {deployment_file}: {e}")
                    continue
            
            return deployments
            
        except Exception as e:
            logger.error(f"Error getting deployment history: {e}")
            return []
    
    def cleanup_old_versions(self, keep_versions: int = 10, keep_days: int = 90) -> int:
        """
        Clean up old model versions
        
        Args:
            keep_versions: Number of versions to keep per model
            keep_days: Keep versions created within this many days
            
        Returns:
            Number of versions cleaned up
        """
        cleaned_count = 0
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        try:
            for model_key, versions in self.versions.items():
                # Keep active version and recent versions
                versions_to_keep = []
                versions_to_remove = []
                
                # Always keep active version
                active_version = self.active_versions.get(model_key)
                
                # Sort by version number (descending)
                sorted_versions = sorted(versions, key=lambda v: v.version_number, reverse=True)
                
                for i, version in enumerate(sorted_versions):
                    should_keep = (
                        version == active_version or  # Keep active
                        i < keep_versions or  # Keep recent versions
                        version.created_at >= cutoff_date or  # Keep recent by date
                        version.status == ModelStatus.ACTIVE  # Keep active status
                    )
                    
                    if should_keep:
                        versions_to_keep.append(version)
                    else:
                        versions_to_remove.append(version)
                
                # Remove old versions
                for version in versions_to_remove:
                    try:
                        # Remove model file
                        if version.model_path and Path(version.model_path).exists():
                            Path(version.model_path).unlink()
                        
                        # Remove backup file
                        if version.backup_path and Path(version.backup_path).exists():
                            Path(version.backup_path).unlink()
                        
                        # Remove metadata file
                        metadata_file = self.metadata_path / f"{version.version_id}.json"
                        if metadata_file.exists():
                            metadata_file.unlink()
                        
                        cleaned_count += 1
                        logger.info(f"Cleaned up old version {version.version_id}")
                        
                    except Exception as e:
                        logger.error(f"Error cleaning up version {version.version_id}: {e}")
                
                # Update version list
                self.versions[model_key] = versions_to_keep
            
            logger.info(f"Version cleanup completed. Removed {cleaned_count} old versions.")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during version cleanup: {e}")
            return 0

# Global version manager instance
_version_manager = None

def get_version_manager() -> ModelVersionManager:
    """Get global version manager instance"""
    global _version_manager
    if _version_manager is None:
        _version_manager = ModelVersionManager()
    return _version_manager

if __name__ == "__main__":
    # Test version management system
    version_manager = get_version_manager()
    
    print("Model Version Management Test")
    print(f"Active versions: {len(version_manager.active_versions)}")
    print(f"Total model families: {len(version_manager.versions)}")
    
    # Show version summary
    for model_key, versions in version_manager.versions.items():
        active = version_manager.active_versions.get(model_key)
        print(f"  {model_key}: {len(versions)} versions, active: {active.version_id if active else 'None'}")