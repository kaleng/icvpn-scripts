#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
from collections import defaultdict
from ipaddress import ip_network, summarize_address_range, ip_address

from resources.filereader import get_communities_data


class Prefix:
    def __init__(self, net, community='', visible=True):
        self.net = net
        self.children = set()
        self.community = community
        self.visible = visible


PREFIX = ip_network('10.0.0.0/8')


def add_net(nets, net, community):
    try:
        net = ip_network(net)
    except ValueError:
        return

    if PREFIX.overlaps(net):
        nets[net.prefixlen].append(Prefix(net, community))


def get_nets(srcdir):
    nets = defaultdict(list)
    for community, data in get_communities_data(srcdir, []):
        if 'networks' in data:
            if 'ipv4' in data['networks']:
                for net in data['networks']['ipv4']:
                    add_net(nets, net, community)

        if 'delegate' in data:
            for d in data['delegate']:
                for net in data['delegate'][d]:
                    add_net(nets, net, community)

    return nets


def insert(net, tree):
    for candidate in tree.children:
        if candidate.net == net.net:
            return

        if candidate.net.overlaps(net.net):
            insert(net, candidate)
            return

    tree.children.add(net)


def build_prefixtree(nets):
    tree = Prefix(PREFIX, 'root')

    # iterate over prefixes - biggest first
    for k, v in nets.items():
        for net in v:
            insert(net, tree)

    return tree


def insert_empty_nets(tree):
    children = set()
    old_children = sorted(tree.children, key=lambda x: int(x.net.network_address))
    prev = None
    for child in old_children:
        insert_empty_nets(child)
        children.add(child)
        if prev is not None:
            start = int(prev.net.broadcast_address) + 1
            end = int(child.net.network_address) - 1
            if end > start:
                internets = summarize_address_range(ip_address(start), ip_address(end))
                for internet in internets:
                    children.add(Prefix(internet, 'free', False))
        prev = child
    tree.children = children

    return tree


def insert_json(tree):
    tmp = {'prefix': tree.net.compressed,
           'size': tree.net.num_addresses,
           'children': list()}

    for child in tree.children:
        tmp['children'].append(insert_json(child))

    tmp['children'] = sorted(tmp['children'], key=lambda x: int(ip_network(x['prefix']).network_address))

    if not tree.visible:
        tmp['display'] = 'none'

    return tmp


def get_inetnum(net, status='assigned'):
    inetnum = {'admin-c': list(),
               'status': list(),
               'inetnum': list(),
               'netname': list()}

    inetnum['admin-c'].append(net.community)
    inetnum['status'].append(status)
    inetnum['inetnum'].append("{} - {}".format(net.net.network_address, net.net.broadcast_address))
    inetnum['netname'].append(net.community)

    return inetnum


def build_inetnums(nets):
    inetnums = dict()
    for k, v in nets.items():
        for net in v:
            inetnums[net.net.compressed] = get_inetnum(net)
    inetnums[PREFIX.compressed] = get_inetnum(Prefix(PREFIX, 'Freifunk'), 'ask')
    return inetnums


def get_prefix_count(nets):
    return sum([len(prefixes) for prefixes in nets.values()])


def generate(srcdir, destdir):
    nets = get_nets(srcdir)
    prefix_tree = build_prefixtree(nets)
    json_tree = insert_json(insert_empty_nets(prefix_tree))
    json_tree['prefixes'] = get_prefix_count(nets)
    json_tree['origin'] = 'icvpn-meta'
    json_tree['date'] = time.time()

    with open(destdir + '/registry-prefixes.json', 'w') as outfile:
        json.dump(json_tree, outfile)

    with open(destdir + '/registry-inetnums.json', 'w') as outfile:
        json.dump(build_inetnums(nets), outfile)
