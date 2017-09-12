import structlog


log = structlog.getLogger()


class Registry(object):
    def register(self, name):
        log.info('Registering {}'.format(name))
        return True

    def test(self):
        raise NameError('blah')
