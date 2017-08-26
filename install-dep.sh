#!/bin/bash

sudo apt update
sudo apt -y install apt-transport-https ca-certificates
sudo apt-key adv --keyserver hkp://ha.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
echo "deb https://apt.dockerproject.org/repo ubuntu-xenial main" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt -y update
sudo apt -y install linux-image-extra-$(uname -r) linux-image-extra-virtual
sudo apt -y update
sudo apt -y install docker-engine
sudo apt -y install docker-compose
sudo apt -y install openvswitch-switch
sudo apt -y install openvswitch-common

sudo apt -y install python-setuptools
sudo easy_install pip virtualenv
sudo pip install scapy ryu
