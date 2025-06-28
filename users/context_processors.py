# users/context_processors.py

def user_roles(request):
    roles = []
    if request.user.is_authenticated and hasattr(request.user, 'staff_profile'):
        roles = list(request.user.staff_profile.roles.values_list('name', flat=True))
    return {'user_roles': roles}
