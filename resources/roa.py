#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from textwrap import dedent

from resources.filereader import get_communities_data
from resources.formatter import Formatter


def add_roa(formatter, asn, community, network, prefixlen, default_max_prefixlen):
    formatter.add_data(asn, community, network, max(prefixlen, default_max_prefixlen))


def create_config(srcdir, exclude, family, fmtclass, default_max_prefixlen):
    """
    Generates a configuration using all files in srcdir
    (non-recursively) excluding communities from 'exclude'.

    The files are read in lexicographic order to produce deterministic
    results.
    """
    formatter = fmtclass()

    if default_max_prefixlen is None:
        if family == 'ipv6':
            default_max_prefixlen = 64
        elif family == 'ipv4':
            default_max_prefixlen = 24

    for community, data in get_communities_data(srcdir, exclude):
        try:
            networks = data['networks'][family]
            asn = data['asn']
            for network in sorted(networks):
                prefixlen = int(network.split("/")[1])
                add_roa(formatter, asn, community, network, prefixlen, default_max_prefixlen)
        except (TypeError, KeyError):
            pass

        delegate = data.get('delegate', {})
        for delegate_asn, delegate_networks in delegate.items():
            for delegate_network in delegate_networks:
                # not very beautiful, but everything more proper requires including a library
                if family == 'ipv6' and '.' in delegate_network:
                    continue
                if family == 'ipv4' and ':' in delegate_network:
                    continue
                prefixlen = int(delegate_network.split("/")[1])
                add_roa(formatter, delegate_asn, "{} (delegation)".format(community), delegate_network, prefixlen,
                        default_max_prefixlen)

    print(formatter.finalize())


class BirdRoaFormatter(Formatter):
    """
    Formatter for roa table in bird format
    """

    def __init__(self):
        self.config = []
        self.data = []
        self.add_comment(dedent(
            """
            This file is automatically generated.
            You need to add the surrounding roa table statement yourself.
            So Include it via:
              roa table icvpn { include "roa.con?" }
            """
        ))

    def add_data(self, asn, name, network, max_prefixlen):
        self.data.append((network, max_prefixlen, asn, name))

    def finalize(self):
        maxlen_net = str(max(map(lambda x: len(x[0]), self.data)))
        maxlen_asn = str(max(map(lambda x: len(str(x[2])), self.data)))

        for entry in self.data:
            self.config.append(
                "roa {subnet:<{len_net}} max {max_prefix_len:>3} as {asn:>{len_asn}}; # {community}".format(
                    subnet=entry[0], max_prefix_len=entry[1], asn=entry[2], community=entry[3],
                    len_net=maxlen_net, len_asn=maxlen_asn
                ))

        return "\n".join(self.config)