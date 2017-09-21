import structlog

log = structlog.getLogger()


class Registry(object):
    def register(self, name):
        return True
