#!/bin/bash -x

init () {
  sudo ovs-vsctl add-br vswitch0

  sudo docker-compose up --build -d

  # sudo ip link add name test_in_l type veth peer name downlink
  # sudo ip link set test_in_l up
  # sudo ip link set downlink up
  # sudo ip link set test_in_l promisc on
  sudo ip link set eno1 down
  sudo ip link set eno1 name downlink
  sudo ip link set downlink up
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

  # sudo ip link add name test_out_l type veth peer name uplink
  # sudo ip link set test_out_l up
  # sudo ip link set uplink up
  # sudo ip link set test_out_l promisc on
  sudo ip link set eno2 down
  sudo ip link set eno2 name uplink
  sudo ip link set uplink up
  sudo ip link set uplink promisc on

  sudo ovs-vsctl --may-exist add-port vswitch0 "uplink"

  sudo ovs-vsctl set-controller vswitch0 tcp:127.0.0.1

  sudo ovs-vsctl set-fail-mode vswitch0 secure
  sudo ovs-vsctl set controller vswitch0 connection-mode=out-of-band

  sudo docker-compose ps
  sudo ovs-vsctl show

  # Setting for ip tables container
  sudo sh -c "echo 1 > /proc/sys/net/bridge/bridge-nf-filter-vlan-tagged"

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

  sudo ip link set downlink down
  sudo ip link set downlink promisc off
  sudo ip link set downlink name eno1
  sudo ip link set eno1 up

  sudo ip link set uplink down
  sudo ip link set uplink promisc off
  sudo ip link set uplink name eno2
  sudo ip link set eno2 up

  # Setting for ip tables container
  sudo sh -c "echo 0 > /proc/sys/net/bridge/bridge-nf-filter-vlan-tagged"

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
