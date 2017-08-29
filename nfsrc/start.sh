#!/bin/sh
brctl addbr br-iptables
brctl addif br-iptables eth0
brctl addif br-iptables eth1
ip link set br-iptables up
