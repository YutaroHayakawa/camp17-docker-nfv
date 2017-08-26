#!/usr/bin/env python

from scapy.all import *
import time


class packet():
    def __init__(self, pkt, label):
        self.pkt = pkt
        self.label = label


pkts = []


pkts.append(packet((Ether()/Dot1Q(vlan=2)/IP()/UDP()), "case1"))
pkts.append(packet((Ether()/Dot1Q(vlan=3)/IP()/UDP()), "case2"))
#pkts.append(packet((Ether()/Dot1Q(vlan=102)/IP()/UDP()), "case3"))

for p in pkts:
    print "Emit packet case=%s" % (p.label)
    sendp(p.pkt, iface="veth_test_in_l")
    time.sleep(1)

#for p in pkts:
#    print "Emit packet case=%s" % (p.label)
#    sendp(p.pkt, iface="veth_test_out_c")
#    time.sleep(1)
