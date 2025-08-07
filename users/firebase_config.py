# firebase_config.py (create this new file)
import firebase_admin
from firebase_admin import credentials
import os
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    try:
        if not firebase_admin._apps:
            # Get absolute path to service account file
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            service_account_path = os.path.join(BASE_DIR, 'serviceAccountKey.json')
            
            if not os.path.exists(service_account_path):
                raise FileNotFoundError(f"Service account file not found at {service_account_path}")

            cred = credentials.Certificate(service_account_path)
            app = firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized successfully")
            return app
        return firebase_admin.get_app()
    except Exception as e:
        logger.error(f"🔥 Critical Firebase initialization error: {str(e)}")
        raise