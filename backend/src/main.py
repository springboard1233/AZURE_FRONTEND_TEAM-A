from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import api_router
from .model_manager import initialize_model_manager, get_model_manager
from .database import get_database_manager, init_database
from .scheduler import get_scheduler
from .capacity_planning import get_capacity_engine
from .accuracy_tracker import get_accuracy_tracker
from .report_generator import get_report_generator
from .model_monitor import get_model_monitor
from .auto_retrainer import get_auto_retrainer
from .alerting import get_alert_manager
from .model_versioning import get_version_manager
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Azure Demand Forecasting API", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    """Initialize model manager on startup"""
    try:
        models_dir = Path(__file__).parent.parent / "models" / "arima"
        logger.info(f"Initializing model manager with directory: {models_dir}")
        
        # Initialize database first
        try:
            dbm = get_database_manager()
            logger.info("Database manager initialized and tables ensured")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

        # Initialize model manager
        try:
            model_manager = initialize_model_manager(models_dir, preload=False)
            available_models = model_manager.get_available_combinations()
            logger.info(f"Model manager initialized with {len(available_models)} available models")
            for region, service, target in available_models:
                logger.debug(f"  - {region}/{service}/{target}")
        except Exception as e:
            logger.error(f"Failed to initialize model manager: {e}")

        # Initialize scheduler
        try:
            scheduler = get_scheduler()
            logger.info(f"Scheduler initialized (horizon={scheduler.config.forecast_horizon_days})")
        except Exception as e:
            logger.error(f"Scheduler initialization failed: {e}")

        # Initialize capacity planning engine
        try:
            capacity_engine = get_capacity_engine()
            logger.info("Capacity planning engine initialized")
        except Exception as e:
            logger.error(f"Capacity engine init failed: {e}")

        # Initialize accuracy tracker
        try:
            tracker = get_accuracy_tracker()
            logger.info("Accuracy tracker initialized")
        except Exception as e:
            logger.error(f"Accuracy tracker init failed: {e}")

        # Initialize report generator
        try:
            report_gen = get_report_generator()
            logger.info("Report generator initialized")
        except Exception as e:
            logger.error(f"Report generator init failed: {e}")

        # Initialize monitoring, retrainer, alerting, and versioning (optional)
        try:
            monitor = get_model_monitor()
            logger.info("Model monitoring initialized")
        except Exception as e:
            logger.warning(f"Model monitor not available: {e}")

        try:
            retrainer = get_auto_retrainer()
            logger.info("Auto-retrainer initialized")
        except Exception as e:
            logger.warning(f"Auto-retrainer not available: {e}")

        try:
            alert_mgr = get_alert_manager()
            logger.info("Alert manager initialized")
        except Exception as e:
            logger.warning(f"Alert manager not available: {e}")

        try:
            version_mgr = get_version_manager()
            logger.info("Model version manager initialized")
        except Exception as e:
            logger.warning(f"Model version manager not available: {e}")
            
    except Exception as e:
        logger.critical(f"Startup initialization encountered an unexpected error: {e}")
        # Don't raise to prevent uvicorn from stopping; components may be optional

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "azure-demand-forecasting-backend"}


app.include_router(api_router, prefix="/api")


