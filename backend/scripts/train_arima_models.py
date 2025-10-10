"""
Train separate ARIMA models for each (region, service, target) combination
"""
import pandas as pd
import numpy as np
import pickle
import joblib
import json
from pathlib import Path
from datetime import datetime
import warnings
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings('ignore')

def mape(y_true, y_pred):
    """Calculate Mean Absolute Percentage Error"""
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def train_arima_for_combination(data, region, service, target, output_dir):
    """
    Train ARIMA model for specific region/service/target combination
    """
    print(f"Training ARIMA for {region}/{service}/{target}...")
    
    # Prepare time series
    ts_data = data.sort_values('date').set_index('date')[target]
    ts_data = ts_data.asfreq('D').fillna(method='ffill')
    
    # Check if we have enough data
    if len(ts_data) < 30:
        print(f"  Insufficient data ({len(ts_data)} points), skipping...")
        return None
    
    # Split for training and validation
    split_point = int(len(ts_data) * 0.8)
    train_data = ts_data[:split_point]
    test_data = ts_data[split_point:]
    
    if len(test_data) < 5:
        print(f"  Insufficient test data ({len(test_data)} points), using all data for training...")
        train_data = ts_data
        test_data = None
    
    try:
        # Fit ARIMA model (trying different orders)
        best_model = None
        best_aic = float('inf')
        best_order = None
        
        # Try different ARIMA orders
        orders_to_try = [(1,1,1), (2,1,1), (1,1,2), (2,1,2), (0,1,1), (1,0,1)]
        
        for order in orders_to_try:
            try:
                model = ARIMA(train_data, order=order)
                fitted_model = model.fit()
                
                if fitted_model.aic < best_aic:
                    best_aic = fitted_model.aic
                    best_model = fitted_model
                    best_order = order
            except:
                continue
        
        if best_model is None:
            print(f"  Failed to fit any ARIMA model, skipping...")
            return None
        
        # Calculate metrics if we have test data
        metrics = {}
        if test_data is not None and len(test_data) > 0:
            try:
                forecast_result = best_model.get_forecast(steps=len(test_data))
                forecast = forecast_result.predicted_mean
                
                mae = mean_absolute_error(test_data, forecast)
                rmse = np.sqrt(mean_squared_error(test_data, forecast))
                mape_val = mape(test_data, forecast)
                
                metrics = {
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'mape': float(mape_val),
                    'aic': float(best_aic),
                    'test_size': len(test_data)
                }
            except Exception as e:
                print(f"  Warning: Could not calculate validation metrics: {e}")
                metrics = {'aic': float(best_aic)}
        else:
            metrics = {'aic': float(best_aic)}
        
        # Prepare model metadata
        metadata = {
            'region': region,
            'service': service,
            'target': target,
            'model_type': 'ARIMA',
            'model_order': best_order,
            'trained_on': datetime.now().isoformat(),
            'model_version': '1.0',
            'train_size': len(train_data),
            'metrics': metrics,
            'data_range': {
                'start_date': str(train_data.index[0].date()),
                'end_date': str(train_data.index[-1].date())
            }
        }
        
        # Save model and metadata
        model_filename = f"{region}__{service}__{target}_arima.pkl"
        metadata_filename = f"{region}__{service}__{target}_arima_metadata.json"
        
        model_path = output_dir / model_filename
        metadata_path = output_dir / metadata_filename
        
        # Save the fitted model
        joblib.dump(best_model, model_path)
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  ✓ Saved model: {model_filename}")
        print(f"  ✓ AIC: {best_aic:.2f}, Order: {best_order}")
        if 'mae' in metrics:
            print(f"  ✓ Validation MAE: {metrics['mae']:.2f}, RMSE: {metrics['rmse']:.2f}")
        
        return metadata
        
    except Exception as e:
        print(f"  ✗ Error training model: {e}")
        return None

def main():
    """Main training function"""
    # Setup paths
    backend_dir = Path(__file__).parent.parent
    data_path = backend_dir / "data" / "processed" / "feature_engineered.csv"
    models_dir = backend_dir / "models" / "arima"
    
    # Create models directory
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("Loading feature engineered data...")
    df = pd.read_csv(data_path, parse_dates=['date'])
    
    # Get unique combinations
    combinations = df[['region', 'resource_type']].drop_duplicates()
    targets = ['usage_cpu', 'usage_storage']
    
    print(f"Found {len(combinations)} region/service combinations")
    print(f"Training models for targets: {targets}")
    print(f"Output directory: {models_dir}")
    print("-" * 60)
    
    # Train models for each combination and target
    all_metadata = []
    
    for _, row in combinations.iterrows():
        region = row['region']
        service = row['resource_type']
        
        # Filter data for this combination
        combo_data = df[(df['region'] == region) & (df['resource_type'] == service)].copy()
        
        # Train models for both CPU and Storage
        for target in targets:
            metadata = train_arima_for_combination(
                combo_data, region, service, target, models_dir
            )
            if metadata:
                all_metadata.append(metadata)
        
        print()  # Empty line for readability
    
    # Save summary metadata
    summary_path = models_dir / "models_summary.json"
    summary = {
        'training_date': datetime.now().isoformat(),
        'total_models': len(all_metadata),
        'models': all_metadata
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Training complete! Saved {len(all_metadata)} models")
    print(f"Summary saved to: {summary_path}")

if __name__ == "__main__":
    main()