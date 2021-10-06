from django.utils.functional import cached_property


class AfterFetchQuerySetMixin:
    """
    QuerySet mixin to enable functions to run immediately
    after records have been fetched from the DB.
    """

    # This is most useful for registering 'prefetch_related' like operations
    # that need to be run after fetching, while still allowing chaining of other
    # QuerySet methods.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._after_fetch_callbacks = []

    def register_after_fetch_callback(self, callback):
        """
        Register a callback to be run after the QuerySet is fetched.
        The callback should be a callable that accepts a list of model instances.
        """
        self._after_fetch_callbacks.append(callback)
        return self

    # _fetch_all and _clone are Django internals.
    def _fetch_all(self):
        already_run = self._result_cache is not None
        # This super() call fills out the result cache in the QuerySet, and does
        # any prefetches.
        super()._fetch_all()
        if already_run:
            # We only run our callbacks once
            return
        # Now we run our callback.
        for c in self._after_fetch_callbacks:
            c(self._result_cache)

    def _clone(self):
        retval = super()._clone()
        retval._after_fetch_callbacks = self._after_fetch_callbacks[:]
        return retval


class ClearCachedPropertyMixin:
    """
    Model mixin that makes `refresh_from_db` clear out `cached_property` items
    """

    def refresh_from_db(self, *args, **kwargs):
        for attr, val in self.__class__.__dict__.items():
            if isinstance(val, cached_property):
                self.__dict__.pop(attr, None)

        super().refresh_from_db(*args, **kwargs)
