
class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def check_class_method(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)
    return func


def classproperty(fget, fset=None):
    fget = check_class_method(fget)
    if fset is not None:
        fset = check_class_method(fset)

    return ClassPropertyDescriptor(fget, fset)
