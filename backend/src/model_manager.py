"""
Model serving infrastructure for ARIMA demand forecasting models.
Handles model loading, caching, and metadata management.
"""
import json
import joblib
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class ARIMAModelManager:
    """
    Manages loading, caching, and serving of ARIMA models for demand forecasting.
    """
    
    def __init__(self, models_dir: Path):
        """
        Initialize the model manager.
        
        Args:
            models_dir: Directory containing ARIMA model files and metadata
        """
        self.models_dir = Path(models_dir)
        self.models_cache: Dict[Tuple[str, str, str], Any] = {}
        self.metadata_cache: Dict[Tuple[str, str, str], Dict] = {}
        self.available_models: Dict[Tuple[str, str, str], Path] = {}
        
        # Service name mapping from full names to model file names
        self.service_mapping = {
            'VirtualMachine': 'VM',
            'VM': 'VM',
            'Container': 'Container',
            'Storage': 'Storage'
        }
        
        # Load available models on initialization
        self._discover_models()
        
    def _discover_models(self):
        """Discover all available model files and their metadata."""
        if not self.models_dir.exists():
            logger.warning(f"Models directory {self.models_dir} does not exist")
            return
            
        pattern = "*_arima.pkl"
        model_files = list(self.models_dir.glob(pattern))
        
        logger.info(f"Discovered {len(model_files)} ARIMA model files")
        
        for model_file in model_files:
            try:
                # Parse filename: region__service__target_arima.pkl
                filename = model_file.stem  # Remove .pkl extension
                parts = filename.replace('_arima', '').split('__')
                
                if len(parts) == 3:
                    region, service, target = parts
                    key = (region, service, target)
                    self.available_models[key] = model_file
                    
                    # Load metadata if available
                    metadata_file = model_file.parent / f"{filename}_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            self.metadata_cache[key] = json.load(f)
                    
                    logger.debug(f"Registered model: {region}/{service}/{target}")
                else:
                    logger.warning(f"Invalid model filename format: {model_file.name}")
                    
            except Exception as e:
                logger.error(f"Error processing model file {model_file}: {e}")
    
    def get_available_combinations(self) -> list:
        """Get list of available (region, service, target) combinations."""
        return list(self.available_models.keys())
    
    def is_model_available(self, region: str, service: str, target: str) -> bool:
        """Check if a model is available for the given combination."""
        mapped_service = self.service_mapping.get(service, service)
        return (region, mapped_service, target) in self.available_models
    
    def load_model(self, region: str, service: str, target: str):
        """
        Load and cache a model for the given combination.
        
        Returns:
            The loaded ARIMA model or None if not available
        """
        # Map service name to model file service name
        mapped_service = self.service_mapping.get(service, service)
        key = (region, mapped_service, target)
        cache_key = (region, service, target)  # Use original service name for caching
        
        # Return cached model if available
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]
        
        # Check if model exists
        if key not in self.available_models:
            logger.warning(f"No model available for {region}/{service}/{target} (mapped to {mapped_service})")
            return None
        
        # Load the model
        try:
            model_path = self.available_models[key]
            model = joblib.load(model_path)
            
            # Cache the loaded model using original service name
            self.models_cache[cache_key] = model
            
            logger.info(f"Loaded model for {region}/{service}/{target} (mapped from {mapped_service})")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model for {region}/{service}/{target}: {e}")
            return None
    
    def get_model_metadata(self, region: str, service: str, target: str) -> Optional[Dict]:
        """Get metadata for a specific model."""
        mapped_service = self.service_mapping.get(service, service)
        key = (region, mapped_service, target)
        return self.metadata_cache.get(key)
    
    def get_forecast(self, region: str, service: str, target: str, steps: int = 30) -> Optional[Dict]:
        """
        Generate forecast using the appropriate model.
        
        Args:
            region: Azure region
            service: Service type (Container, VM, Storage)
            target: Target variable (usage_cpu, usage_storage)
            steps: Number of forecast steps
            
        Returns:
            Dictionary with forecast data and metadata, or None if model not available
        """
        model = self.load_model(region, service, target)
        if model is None:
            return None
        
        try:
            # Generate forecast
            forecast_result = model.get_forecast(steps=steps)
            
            # Extract forecast data
            predicted_mean = forecast_result.predicted_mean
            
            # Try to get confidence intervals
            confidence_intervals = None
            try:
                ci = forecast_result.conf_int(alpha=0.05)  # 95% confidence interval
                # Format confidence intervals as expected by scheduler
                if ci is not None and len(ci.columns) >= 2:
                    confidence_intervals = {
                        'lower': ci.iloc[:, 0].tolist(),
                        'upper': ci.iloc[:, 1].tolist()
                    }
            except:
                logger.debug(f"Confidence intervals not available for {region}/{service}/{target}")
            
            # Get model metadata
            metadata = self.get_model_metadata(region, service, target)
            
            result = {
                'region': region,
                'service': service,
                'target': target,
                'steps': steps,
                'forecast': predicted_mean.tolist(),
                'confidence_intervals': confidence_intervals,
                'model_metadata': metadata,
                'forecast_generated_at': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating forecast for {region}/{service}/{target}: {e}")
            return None
    
    def get_model_summary(self) -> Dict:
        """Get summary of all available models."""
        summary = {
            'total_models': len(self.available_models),
            'models_by_region': {},
            'models_by_service': {},
            'models_by_target': {},
            'last_updated': datetime.now().isoformat()
        }

        
        
        # Group by region, service, and target
        for (region, service, target) in self.available_models.keys():
            # By region
            if region not in summary['models_by_region']:
                summary['models_by_region'][region] = []
            summary['models_by_region'][region].append(f"{service}/{target}")
            
            # By service
            if service not in summary['models_by_service']:
                summary['models_by_service'][service] = []
            summary['models_by_service'][service].append(f"{region}/{target}")
            
            # By target
            if target not in summary['models_by_target']:
                summary['models_by_target'][target] = []
            summary['models_by_target'][target].append(f"{region}/{service}")
        
        return summary
    
    def clear_cache(self):
        """Clear the model cache to free memory."""
        self.models_cache.clear()
        logger.info("Model cache cleared")
    
    def preload_all_models(self):
        """Preload all available models into cache."""
        logger.info("Preloading all models...")
        
        for region, service, target in self.available_models.keys():
            self.load_model(region, service, target)
        
        logger.info(f"Preloaded {len(self.models_cache)} models")


# Global model manager instance
model_manager: Optional[ARIMAModelManager] = None

def get_model_manager() -> ARIMAModelManager:
    """Get the global model manager instance."""
    global model_manager
    if model_manager is None:
        from pathlib import Path
        models_dir = Path(__file__).parent.parent / "models" / "arima"
        model_manager = ARIMAModelManager(models_dir)
    return model_manager

def initialize_model_manager(models_dir: Path, preload: bool = True):
    """Initialize the global model manager."""
    global model_manager
    model_manager = ARIMAModelManager(models_dir)
    
    
    if preload:
        model_manager.preload_all_models()
    
    return model_manager