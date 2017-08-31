#!/bin/sh
set -xe
brctl addbr br-iptables
brctl addif br-iptables eth0
brctl addif br-iptables eth1
# brctl stp br-iptables on
ip link set br-iptables up
