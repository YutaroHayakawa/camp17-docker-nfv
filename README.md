# Docker NFV Platform for WIDE Camp 2017 Net

This platform uses OVS + OpenFlow + Ryu controller application for chaining.

## Quick Start

### Install dependencies
```
$ ./install-dep.sh
```

### Running test case
```
$ ./setup.sh init
$ ryu-manager controller/controller.py

// In another window
$ cd packet-gen
$ sudo python test-case.py
```

## Requirements for running NFs

- OVS need to have attached interface named "downlink" and "uplink".
- Foreach NFs, we need two interface which has following naming convension \<nf name\>\_\<up \| down\>.
  Interface \<nf name\>\_up is for uplink side chaining. Interface \<nf name\>\_down is for downlink side chining.
- Incoming packets are needed to be tagged by 802.1Q.
- IPv4 only.
- You shouldn't touch to IPv4 DSCP field in your NF.

## Configuring switch

Our controller has REST API endpoint. You can configure switch through that.
It listen to TCP port 8080 by default.

### End points

1. /camp-nfv/api/get-available-datapath

- Method: GET
- Parameter: None
- Output: JSON which contains configurable datapath from the controller
- Example Output

```
{
  "datapath": ["00001e9302ed1640", "00003e9402ed1640"]
}
```

2. /camp-nfv/api/{dpid}/get-chain-info

- Method: GET
- Parameter: Datapath Id needed to be embedded to URI
- Output: JSON which contains available downlink, uplink, service function chain and VNF
- Example Output
```
{
  "downlink": 1,
  "sf_chains": [],
  "uplink": 8,
  "vnf": {
    "nf1": {
      "down_port": 2,
      "up_port": 3
    },
    "nf2": {
      "down_port": 4,
      "up_port": 5
    },
    "nf3": {
      "down_port": 6,
      "up_port": 7
    }
  }
}
```

3. /camp-nfv/api/{dpid}/add-chain

- Method: POST
- Parameter: JSON with following format
```
{
  "vlan": <VLAN ID for discriminate flow>,
  "chain": [<list of name string of nfs>]
}
```
- Output: None

## Using CLI

We have simple CLI which can easily configure switch through REST API

### Installation
```
$ cd cli
$ pip install -r requirements.txt
$ python cli.py
```

You can see supported commands by typing "help".
Most commands are straightly corresponding to API endpoint.
