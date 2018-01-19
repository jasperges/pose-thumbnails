def pyside_cache(propname):
    """Decorator, stores the result of the decorated callable in Python-managed memory.

    This is to work around the warning at
    https://www.blender.org/api/blender_python_api_master/bpy.props.html#bpy.props.EnumProperty
    """

    if callable(propname):
        raise TypeError('Usage: pyside_cache("property_name")')

    def decorator(wrapped):
        """Stores the result of the callable in Python-managed memory.

        This is to work around the warning at
        https://www.blender.org/api/blender_python_api_master/bpy.props.html#bpy.props.EnumProperty
        """

        import functools

        @functools.wraps(wrapped)
        # We can't use (*args, **kwargs), because EnumProperty explicitly checks
        # for the number of fixed positional arguments.
        def wrapper(self, context):
            result = None
            try:
                result = wrapped(self, context)
                return result
            finally:
                rna_type, rna_info = getattr(self.bl_rna, propname)
                rna_info['_cached_result'] = result
        return wrapper
    return decorator
