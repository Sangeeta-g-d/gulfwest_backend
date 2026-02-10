# users/context_processors.py

def user_roles(request):
    roles = []
    if request.user.is_authenticated:
        try:
            if hasattr(request.user, 'staff_profile') and request.user.staff_profile:
                roles = list(request.user.staff_profile.roles.values_list('name', flat=True))
                print(f"[DEBUG] User {request.user.email} has roles: {roles}")
            elif request.user.is_staff:
                print(f"[DEBUG] User {request.user.email} is_staff but no staff_profile")
            else:
                print(f"[DEBUG] User {request.user.email} is not staff")
        except Exception as e:
            print(f"[ERROR] Error fetching user roles: {str(e)}")
    return {
        'user_roles': roles,
        'user_role_count': len(roles),
        'has_multiple_roles': len(roles) > 2
    }
