from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.cli import CLI


class CampNFTopo(Topo):
    def build(self, n):
        switch = self.addSwitch("s1", protocols='OpenFlow13')

        host = self.addHost(name="peer1")
        self.addLink(host, switch)

        for h in range(n):
            host = self.addHost(name="h%s" % h)
            self.addLink(host, switch)
            self.addLink(host, switch)

        host = self.addHost(name="peer2")
        self.addLink(host, switch)


def simpleTest():
    "Create and test a simple network"
    topo = CampNFTopo(n=3)
    net = Mininet(topo, controller=RemoteController('c0', ip='127.0.0.1'))

    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    simpleTest()
