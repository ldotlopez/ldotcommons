from appkit import application


class Service(application.Extension):
    def __init__(self, app):
        super().__init__()
        self.app = app


class ApplicationMixin:
    SERVICE_EXTENSION_POINT = Service

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_extension_point(self.__class__.SERVICE_EXTENSION_POINT)
        self._services = {}

    def register_extension_class(self, cls):
        super().register_extension_class(cls)
        if issubclass(cls, self.__class__.SERVICE_EXTENSION_POINT):
            self._services[cls.__extension_name__] = cls(self)

    def get_extension(self, extension_point, name, *args, **kwargs):
        assert isinstance(extension_point, type)
        assert isinstance(name, str)

        # Check requested extension is a service
        if extension_point == self.__class__.SERVICE_EXTENSION_POINT and \
           name in self._services:
            return self._services[name]

        return super().get_extension(extension_point, name,
                                     *args, **kwargs)

    def get_service(self, name):
        return self.get_extension(self.__class__.SERVICE_EXTENSION_POINT, name)
