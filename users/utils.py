
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import os
import firebase_admin
from firebase_admin import credentials

def login_required_nocache(view_func):
    return login_required(never_cache(view_func), login_url='/')


def initialize_firebase():
    """Initialize Firebase only once"""
    try:
        if not firebase_admin._apps:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            service_account_path = os.path.join(BASE_DIR, 'firebase_service_key.json')

            if not os.path.exists(service_account_path):
                raise FileNotFoundError(f"Service account file not found at {service_account_path}")

            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'projectId': cred.project_id,
                'storageBucket': f"{cred.project_id}.appspot.com"
            })
            print("✅ Firebase initialized successfully")
        else:
            print("ℹ️ Firebase already initialized, skipping...")
    except Exception as e:
        print(f"🔥 Firebase initialization error: {str(e)}")
        raise RuntimeError("Firebase initialization failed") from e