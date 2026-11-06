"""PROJECT AVI // RPyC classic server for the MT5 bridge (runs under 64-bit Windows Python in Wine).

Same protocol as mt5linux's generated server (rpyc SlaveService), with one addition: every
connection's namespace pre-imports `datetime`. mt5linux 0.1.9 clients only execute
`import MetaTrader5 as mt5` remotely, then send eval strings such as
`mt5.history_deals_get(datetime.datetime(...), ...)`, which otherwise fail with
NameError: name 'datetime' is not defined.

usage: python avi_rpyc_server.py [port]
"""
import sys

from rpyc.core.service import SlaveService
from rpyc.utils.server import ThreadedServer


class AviSlaveService(SlaveService):
    def on_connect(self, conn):
        super().on_connect(conn)
        exec("import datetime\nimport MetaTrader5 as mt5", self.namespace)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"[avi-rpyc] Python {sys.version.split()[0]} classic server on 0.0.0.0:{port}", flush=True)
    ThreadedServer(
        AviSlaveService,
        hostname="0.0.0.0",
        port=port,
        reuse_addr=True,
        protocol_config={"allow_all_attrs": True, "allow_pickle": True, "sync_request_timeout": 120},
    ).start()
