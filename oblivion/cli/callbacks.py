import functools

def inject_extra_vars(callback_funcs):
    """
    Decorator that merges results from multiple callback functions
    and injects them as kwargs into the Click command.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            extra_vars = {}
            for cb in callback_funcs:
                extra_vars.update(cb())
            return func(*args, **kwargs, **extra_vars)
        return wrapper
    return decorator

