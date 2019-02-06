from django.dispatch import Signal

# Sent just after a review was posted. This signal is sent at more or less
# the same time (just after, actually) as the Review object's save signal,
# except that the HTTP request is sent along with this signal.
review_was_posted = Signal(providing_args=["review", "request"])
