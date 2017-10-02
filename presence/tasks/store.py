import structlog

log = structlog.getLogger()


class Store(object):
    def add_dhcp(self, mac, ip, hostname):
        return True
