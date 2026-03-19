from django.utils.deprecation import MiddlewareMixin
from marketplace.models import UserEvent, Experience

class UserBehaviorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically track user behavior like page views and searches.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        # We only log GET requests to avoid inflating counts on form submissions.
        if request.method != "GET":
            return None

        path = request.path_info
        
        try:
            # Check if it's an Experience Detail view
            if path.startswith("/experiences/") and "slug" in view_kwargs:
                slug = view_kwargs["slug"]
                experience = Experience.objects.filter(slug=slug).first()
                if experience:
                    self._log_event(request, 'VIEW', experience=experience)

            # Check if it's a Search/Listing view
            elif path == "/experiences/" and request.GET:
                # Log search queries
                query = request.GET.get('q', '')
                location = request.GET.get('location', '')
                if query or location:
                    self._log_event(request, 'SEARCH', metadata={'query': query, 'location': location})

            # Check if it's a Checkout view
            elif path.startswith("/checkout/"):
                experience_id = view_kwargs.get('pk')
                if experience_id:
                    experience = Experience.objects.filter(id=experience_id).first()
                    if experience:
                        self._log_event(request, 'BOOK', experience=experience)

        except Exception as e:
            # Failsafe so tracking doesn't break the app
            import logging
            logging.getLogger(__name__).error(f"Error tracking user behavior: {e}")

        return None

    def _log_event(self, request, event_type, experience=None, metadata=None):
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key

        UserEvent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key if not request.user.is_authenticated else None,
            event_type=event_type,
            experience=experience,
            metadata=metadata or {}
        )
