# Copyright (C) 2017 Yutaro Hayakawa
#
# Licensed under the Apache License, Versio.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib import dpid as dpid_lib
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response

import pprint
import json
import logging
import traceback
import collections


# Logging settings
logger = logging.getLogger(__name__)

camp_nfv_instance_name = 'camp_nfv_api_app'


class Switch(object):
    def __init__(self, dpobj, ports):
        self.dpobj = dpobj

        # Check for uplink port
        uplink = filter(lambda p:p.name == 'uplink', ports)
        if len(uplink) == 0:
            logger.error('no uplink port in this switch')
            raise Exception
        elif len(uplink) > 1:
            logger.error('more than two uplink ports in this switch')
            raise Exception
        else:
            self.uplink = uplink[0].port_no

        # Check for downlink port
        downlink = filter(lambda p:p.name == 'downlink', ports)
        if len(downlink) == 0:
            logger.error('no downlink port in this switch')
            raise Exception
        elif len(downlink) > 1:
            logger.error('more than two downlink ports in this switch')
            raise Exception
        else:
            self.downlink = downlink[0].port_no

        # Check for downlink port
        vnf_dict = {}

        for p in ports:
            if p.name == 'uplink' or p.name == 'downlink':
                continue

            # vnf port naming convention: <vnf name>_<direction>
            spl = p.name.split("_")
            if len(spl) != 2:
                logger.error('invalid port name %s' % p.name)

            vnf_name = spl[0]
            vnf_dir = spl[1]

            if vnf_name not in vnf_dict:
                vnf_dict[vnf_name] = { 'up_port': None, 'down_port': None }

            if vnf_dir == 'up':
                if vnf_dict[vnf_name]['up_port'] == None:
                    vnf_dict[vnf_name]['up_port'] = p.port_no
                else:
                    logger.error('more than two up ports for vnf %s' % vnf_name)
                    raise Exception
            elif vnf_dir == 'down':
                if vnf_dict[vnf_name]['down_port'] == None:
                    vnf_dict[vnf_name]['down_port'] = p.port_no
                else:
                    logger.error('more than two down ports for vnf %s' % vnf_name)
                    raise Exception
            else:
                logger.error('invalid direction %s' % vnf_dir)
                raise Exception

        # Make sure each vnf has two direction ports
        for vnf in vnf_dict:
            if vnf_dict[vnf]['up_port'] == None:
                logger.error('vnf %s has no up_port')

            if vnf_dict[vnf]['down_port'] == None:
                logger.error('vnf %s has no down_port')

        self.vnf_dict = vnf_dict
        self.sf_chains = []


class VlanDscpMapper(object):
    def __init__(self):
        self.id_pool = [True] * pow(2, 6)
        self.map = {}

    def register_vid(self, vid):
        for i, is_available in enumerate(self.id_pool):
            if is_available:
                self.id_pool[i] = False
                self.map[vid] = i
                print "Registered vlan id %d mapping id is %d" % (vid, i)
                return i

        return None

    def unregister_vid(self, vid):
        idx = self.map[vid]
        del self.map[vid]
        self.id_pool[idx] = True

    def get_mapping_id(self, vid):
        if vid in self.map:
            return self.map[vid]
        else:
            return None


class CampNFVRest(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(CampNFVRest, self).__init__(*args, **kwargs)

        # REST API related settings
        self.switches = {}
        wsgi = kwargs['wsgi']
        wsgi.register(CampNFVController,
                      { camp_nfv_instance_name: self })

        # Initialization of chaining related members
        self.chain_info = {}

        self.mapper = VlanDscpMapper()

    def dump_available_dp_json(self):
        return json.dumps({ "datapath": self.switches.keys() })

    def dump_chain_json(self, dpid):
        if dpid not in self.switches:
            raise

        sw = self.switches[dpid]

        ret_dict = {
            "uplink": sw.uplink,
            "downlink": sw.downlink,
            "vnf": sw.vnf_dict,
            "sf_chains": sw.sf_chains
        }

        return json.dumps(ret_dict)

    def create_flowmod(self, datapath, match, inst, priority, tid, update):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # if entry already exists, update it
        command = ofproto.OFPFC_MODIFY if update else ofproto.OFPFC_ADD

        # inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, match=match, instructions=inst,
                command=command, priority=priority, table_id=tid)

        return mod

    def add_chain(self, dpid, new_chain):
        if dpid not in self.switches:
            raise Exception

        datapath = self.switches[dpid].dpobj
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        sf_chains = self.switches[dpid].sf_chains

        dup = False

        # for ipv4, we only allow 2^6 vlan id
        if len(sf_chains) + 1 > pow(2, 6):
            raise Exception

        # We don't allow duplicate of vlan id
        for c in sf_chains:
            if new_chain['vlan'] == c['vlan']:
                raise Exception

        sf_chains.append(new_chain)

        try:
            self.emit_chain_flowmod(dpid, new_chain, dup)
        except:
            print traceback.format_exc()
            c = sf_chains.pop()
            logger.error('failed to emit flowmod for chain %s' % str(c))
            raise Exception

    def remove_chain(self, dpid, vlan):
        datapath = self.switches[dpid].dpobj
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        flow_mods = []

        match = parser.OFPMatch(vlan_vid=vlan)
        instructions = []
        mod = parser.OFPFlowMod(datapath, 0, 0, 0, ofproto.OFPFC_DELETE, 0, 0, 1,
                ofproto.OFPCML_NO_BUFFER, ofproto.OFPP_ANY, ofproto.OFPG_ANY, 0, match, instructions)
        flow_mods.append(mod)

        match = parser.OFPMatch(ip_dscp=self.mapper.get_mapping_id(vlan))
        instructions = []
        mod = parser.OFPFlowMod(datapath, 0, 0, 0, ofproto.OFPFC_DELETE, 0, 0, 1,
                ofproto.OFPCML_NO_BUFFER, ofproto.OFPP_ANY, ofproto.OFPG_ANY, 0, match, instructions)
        flow_mods.append(mod)

        for mod in flow_mods:
            datapath.send_msg(mod)

        self.mapper.unregister_vid(vlan)

    def _emit_chain_flowmod(self, dpid, new_chain, dup, direction):
        datapath = self.switches[dpid].dpobj
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        sw = self.switches[dpid]
        vnf_dict = sw.vnf_dict
        vlan = new_chain['vlan']
        chain = new_chain['chain']

        mapping_id = self.mapper.get_mapping_id(vlan)
        if mapping_id == None:
            mapping_id = self.mapper.register_vid(vlan)
            if mapping_id == None:
                raise Exception

        if direction == 'up':
            entry = sw.downlink
            exit = sw.uplink
            inport = 'down_port'
            outport = 'up_port'
        elif direction == 'down':
            entry = sw.uplink
            exit = sw.downlink
            inport = 'up_port'
            outport = 'down_port'
            # incoming network traffic should go through vnfs in reverse order
            chain.reverse()
        else:
            logger.error('invalid direction')
            raise Exception


        flow_mods = []

        # Initial flow entry. Modify dscp field for remembering vlan id.
        match = parser.OFPMatch(in_port=entry, vlan_vid=vlan|ofproto_v1_3.OFPVID_PRESENT,
                eth_type=ether_types.ETH_TYPE_IP)
        actions = [
                parser.OFPActionSetField(ip_dscp=mapping_id),
                parser.OFPActionOutput(vnf_dict[chain[0]][inport])
        ]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flow_mods.append(self.create_flowmod(datapath, match, inst, 1, 0, dup))

        for i, c in enumerate(chain):
            if i == len(chain) - 1:
                break

            vnf1 = vnf_dict[c]
            vnf2 = vnf_dict[chain[i + 1]]

            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_dscp=mapping_id, in_port=vnf1[outport])
            actions = [
                    parser.OFPActionOutput(vnf2[inport])
            ]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            flow_mods.append(self.create_flowmod(datapath, match, inst, 1, 0, dup))

        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ip_dscp=mapping_id, in_port=vnf_dict[chain[-1]][outport])
        actions = [
                parser.OFPActionPushVlan(ether_types.ETH_TYPE_8021Q),
                parser.OFPActionSetField(vlan_vid=vlan|ofproto_v1_3.OFPVID_PRESENT),
                parser.OFPActionSetField(ip_dscp=1),
                parser.OFPActionOutput(exit)
        ]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flow_mods.append(self.create_flowmod(datapath, match, inst, 1, 0, dup))

        # Emit all flowmods
        for msg in flow_mods:
            print ''
            pprint.pprint('flow_mods: %s' % str(msg))
            datapath.send_msg(msg)

    def emit_chain_flowmod(self, dpid, new_chain, dup):
        self._emit_chain_flowmod(dpid, new_chain, dup, "up")
        self._emit_chain_flowmod(dpid, new_chain, dup, "down")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg

        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Emit table miss flowmod
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                   ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        datapath.send_msg(self.create_flowmod(datapath, match, inst, 0, 0, False))

        # Send port stat request
        req = parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        # extract port stats except port 4294967294
        ports = filter(lambda s:s.port_no!=4294967294, [ stat for stat in ev.msg.body ])

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = dpid_lib.dpid_to_str(datapath.id)

        try:
            self.switches[dpid] = Switch(datapath, ports)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception

        # Emit arp passthrough rules
        match = parser.OFPMatch(in_port=self.switches[dpid].uplink, eth_type=ether_types.ETH_TYPE_ARP)
        actions = [parser.OFPActionOutput(self.switches[dpid].downlink)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        datapath.send_msg(self.create_flowmod(datapath, match, inst, 3, 0, False))

        match = parser.OFPMatch(in_port=self.switches[dpid].downlink, eth_type=ether_types.ETH_TYPE_ARP)
        actions = [parser.OFPActionOutput(self.switches[dpid].uplink)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        datapath.send_msg(self.create_flowmod(datapath, match, inst, 3, 0, False))

        logger.info('----------------')
        logger.info('Registered switch dpid <%s>' % dpid)
        logger.info('uplink:    %s' % self.switches[dpid].uplink)
        logger.info('downlink:  %s' % self.switches[dpid].downlink)
        logger.info('vnf_dict:\n%s' % pprint.pformat(self.switches[dpid].vnf_dict))
        logger.info('----------------')

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        pkt = packet.Packet(ev.msg.data)
        pprint.pprint('packet in: %s' % str(ev.msg))
        pprint.pprint('packet in: %s' % str(pkt))


class CampNFVController(ControllerBase):

    def __init__(self, req, link, data, *args, **config):
        super(CampNFVController, self).__init__(req, link, data, **config)
        self.camp_nfv_app = data[camp_nfv_instance_name]

    @route('camp-nfv', '/camp-nfv/api/get-available-datapath', methods=['GET'])
    def get_available_datapath(self, req, **kwargs):
        camp_nfv = self.camp_nfv_app

        try:
            body = camp_nfv.dump_available_dp_json()
            return Response(content_type='application/json', body=body)
        except Exception as e:
            return Response(status=500)

    @route('camp-nfv', '/camp-nfv/api/{dpid}/get-chain-info', methods=['GET'],
            requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_chain_info(self, req, **kwargs):
        camp_nfv = self.camp_nfv_app

        try:
            body = camp_nfv.dump_chain_json(kwargs['dpid'])
            return Response(content_type='application/json', body=body)
        except Exception as e:
            return Response(status=500)

    @route('camp-nfv', '/camp-nfv/api/{dpid}/add-chain', methods=['POST'],
            requirements={'dpid': dpid_lib.DPID_PATTERN})
    def add_chain(self, req, **kwargs):
        camp_nfv = self.camp_nfv_app

        print req.json

        try:
            new = req.json
            camp_nfv.add_chain(kwargs['dpid'], new)
        except ValueError:
            print traceback.format_exc()
            return Response(status=500)

    @route('camp-nfv', '/camp-nfv/api/{dpid}/remove-chain', methods=['POST'],
            requirements={'dpid': dpid_lib.DPID_PATTERN})
    def remove_chain(self, req, **kwargs):
        camp_nfv = self.camp_nfv_app

        try:
            vlan = req.json['vlan']
            camp_nfv.remove_chain(kwargs['dpid'], int(vlan))
        except Exception as e:
            print traceback.format_exc()
            return Response(status=500)
