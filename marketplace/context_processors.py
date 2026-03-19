def user_role_flags(request):
    is_host_user = False
    user = getattr(request, "user", None)

    if user and user.is_authenticated:
        profile = getattr(user, "userprofile", None)
        is_host_user = bool(profile and getattr(profile, "is_host", False))

    return {
        "is_host_user": is_host_user,
    }
