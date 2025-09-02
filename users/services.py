from django.utils import timezone

def anonymize_user(user):
    """
    Replace PII, deactivate the account, keep the row for reporting.
    Ensures unique placeholders for unique fields (email/phone).
    """
    stamp = f"{user.id}-{int(timezone.now().timestamp())}"

    # Optional: delete profile file from storage
    if user.profile:
        try:
            user.profile.delete(save=False)
        except Exception:
            pass

    user.email = f"deleted_user_{stamp}@deleted.local"
    user.phone_number = f"deleted_{user.id}"
    user.name = "Deleted User"
    user.gender = None
    user.dob = None
    user.zone = ""
    user.area = ""
    user.city = ""
    user.latitude = None
    user.longitude = None
    user.is_phone_verified = False
    user.is_active = False      # prevent login
    user.flag = False           # just in case you use it for any gating

    user.save()
    return user
