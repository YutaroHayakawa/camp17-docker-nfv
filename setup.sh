#!/bin/bash -x

init () {
  sudo ovs-vsctl add-br vswitch0

  sudo docker-compose up --build -d

#  sudo ip link add name veth_test_in_l type veth peer name downlink
#  sudo ip link set veth_test_in_l up
#  sudo ip link set downlink up
#  sudo ip link set veth_test_in_l promisc on
  sudo ip link set downlink promisc on

  sudo ovs-vsctl --may-exist add-port vswitch0 "downlink"

  sudo ./ovs-docker add-port vswitch0 eth0 nf1 down
  sudo ./ovs-docker add-port vswitch0 eth1 nf1 up
  sudo ip link set nf1_down up
  sudo ip link set nf1_up up

  sudo ./ovs-docker add-port vswitch0 eth0 nf2 down
  sudo ./ovs-docker add-port vswitch0 eth1 nf2 up
  sudo ip link set nf2_down up
  sudo ip link set nf2_up up

  sudo ./ovs-docker add-port vswitch0 eth0 nf3 down
  sudo ./ovs-docker add-port vswitch0 eth1 nf3 up
  sudo ip link set nf3_down up
  sudo ip link set nf3_up up

  sudo ./ovs-docker add-port vswitch0 eth0 iptables down
  sudo ./ovs-docker add-port vswitch0 eth1 iptables up
  sudo ip link set iptables_down up
  sudo ip link set iptables_up up

#  sudo ip link add name veth_test_out_l type veth peer name uplink
#  sudo ip link set veth_test_out_l up
#  sudo ip link set uplink up
#  sudo ip link set veth_test_out_l promisc on
  sudo ip link set uplink promisc on

  sudo ovs-vsctl --may-exist add-port vswitch0 "uplink"

  sudo ovs-vsctl set-controller vswitch0 tcp:127.0.0.1

  sudo docker-compose ps
  sudo ovs-vsctl show

  echo "Init done. Please execute something on container."
}

destroy () {
  sudo ./ovs-docker del-port vswitch0 eth0 nf1
  sudo ./ovs-docker del-port vswitch0 eth1 nf1

  sudo ./ovs-docker del-port vswitch0 eth0 nf2
  sudo ./ovs-docker del-port vswitch0 eth1 nf2

  sudo ./ovs-docker del-port vswitch0 eth0 nf3
  sudo ./ovs-docker del-port vswitch0 eth1 nf3

  sudo ./ovs-docker del-port vswitch0 eth0 iptables
  sudo ./ovs-docker del-port vswitch0 eth1 iptables

  sudo docker-compose down

  sudo ovs-vsctl del-br vswitch0

#  sudo ip link del uplink
#  sudo ip link del downlink

  echo "Destroy done."
}

if [ $1 = "init" ]; then
  init
  exit 0
fi

if [ $1 = "destroy" ]; then
  destroy
  exit 0
fi

echo "Invalid command $1"
exit 1
