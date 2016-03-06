#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
from collections import defaultdict
from multiprocessing.dummy import Pool
from textwrap import dedent

from resources.filereader import get_communities_data
from resources.formatter import Formatter


def is_reachable(host, port, timeout):
    """
    Test reachability of host by opening a TCP connection to the specified
    port.
    """
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except (socket.timeout, socket.error):
        return False


def create_config(srcdir, exclude, prefix, defaulttemplate, templates, family,
                  fmtclass, timeout):
    """
    Generates a configuration using all files in srcdir
    (non-recursively) excluding communities from 'exclude'.

    The files are read in lexicographic order to produce deterministic
    results.
    """
    formatter = fmtclass()
    template = defaultdict(lambda: defaulttemplate)
    template.update(dict(map(lambda s: s.split(":"), templates)))
    peers = []

    for community, data in get_communities_data(srcdir, exclude):
        try:
            bgp = data["bgp"]
            asn = data["asn"]
        except (TypeError, KeyError):
            continue

        for host in sorted(bgp.keys()):
            d = bgp[host]
            if family not in d:
                continue

            peer = d[family]

            peers.append({
                "asn": asn,
                "host": host,
                "community": community,
                "peer": peer,
                "passive": False,
            })

    if timeout > 0:
        def update_peer_passive(peer):
            peer["passive"] = not is_reachable(peer["peer"], 179, timeout)

        Pool(len(peers)).map(update_peer_passive, peers)

        # if all peers are passive, ignore the check results
        if all(peer["passive"] for peer in peers):
            for peer in peers:
                peer["passive"] = False

    for peer in peers:
        formatter.add_data(peer["asn"], prefix + peer["host"],
                           template[peer["community"]], peer["peer"],
                           peer["passive"])

    print(formatter.finalize())


class BirdFormatter(Formatter):
    """Formatter for bind9 using type forward"""
    def add_data(self, asn, name, template, peer, passive=False):
        self.config.append(dedent("""
            protocol bgp {name} from {template} {{
                neighbor {peer} as {asn};""".format(
            peer=peer, asn=asn, name=name, template=template)))
        if passive:
            self.config.append("    passive yes;")
        self.config.append("}\n")


class QuaggaFormatter(Formatter):
    """Formatter for quagga"""

    def add_comment(self, comment):
        self.config.append("! " + "\n! ".join(comment.split("\n")))

    def add_data(self, asn, name, template, peer, passive=False):
        self.config.append(dedent("""
            neighbor {peer} remote-as {asn}
            neighbor {peer} description {name}
            neighbor {peer} peer-group {template}""".format(peer=peer, asn=asn, name=name, template=template)))
        if passive:
            self.config.append("neighbor {peer} passive".format(peer=peer))
