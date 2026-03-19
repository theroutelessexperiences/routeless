from django import template

register = template.Library()

@register.simple_tag
def query_transform(request, **kwargs):
    """
    Returns the URL-encoded query string for the current request,
    updating or adding the provided keyword arguments.
    """
    updated = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None and v != "":
            updated[k] = v
        else:
            updated.pop(k, None)  # Remove if set to None or empty string
    return updated.urlencode()
