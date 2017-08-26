from cmd import Cmd
import json
import pprint

import click
import requests


class DockerNfvCli(Cmd):
    def __init__(self, controller, port):
        Cmd.__init__(self)

        self.controller_str = "%s:%d" % (controller, port)
        self.prompt = "docker-nfv @ %s > " % self.controller_str
        self.intro = "=== Docker NFV CLI ==="
        self.datapath = {}

    def preloop(self):
        r = requests.get("http://%s/camp-nfv/api/get-available-datapath" % self.controller_str)

        if (r.status_code != 200):
            print "Failed to get datapath information (status: %d)" % r.status_code

        dp_info = r.json()

        print "Creating dpid alias"
        for i, dp in enumerate(dp_info["datapath"]):
            self.datapath["dp%d" % i] = dp
            print "dp%d: %s" % (i, dp)

        print ""

    def emptyline(self):
        pass

    def do_show(self, target):
        if target == "dp":
            pprint.pprint(self.datapath)
        else:
            print "Invalid target %s" % target

    def do_get_chain_info(self, dp):
        if dp not in self.datapath:
            print "No such datapath %s" % dp
            return

        r = requests.get("http://%s/camp-nfv/api/%s/get-chain-info" % (self.controller_str, self.datapath[dp]))

        if (r.status_code != 200):
            print "Failed to get port information (status: %d)" % r.status_code
            return

        pprint. pprint(r.json())

    # input format <dp>,<vlan>,<nf1>,...,<nfN>
    def do_add_chain(self, arg):
        spl = arg.split(" ")
        if len(spl) < 3:
            print "Invalid input string"
            return

        dp = spl[0]
        vlan = int(spl[1])
        nfs = spl[2:-1]

        if dp not in self.datapath:
            print "No such datapath %s" % dp
            return

        if vlan > pow(2, 12) or vlan < 0:
            print "Invalid vlan id %d" % vlan

        post_data = json.dumps({ "vlan": vlan, "chain": nfs })

        r = requests.post("http://%s/camp-nfv/api/%s/add-chain" % (self.controller_str, self.datapath[dp]), data=post_data)
        if (r.status_code != 200):
            print "Failed to add new chain (status: %d)" % r.status_code
            return None

        print "Successfully added chain"


@click.command()
@click.option('--controller', '-c', default="localhost")
@click.option('--controller-port', '-p', default=8080)
def main(controller, controller_port):
    cli = DockerNfvCli(controller, controller_port)
    cli.cmdloop()


if __name__ == '__main__':
    main()
