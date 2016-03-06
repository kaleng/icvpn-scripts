#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from textwrap import dedent

from resources.filereader import get_communities_data
from resources.formatter import Formatter


class SmokePingFormatter(Formatter):
    """
    Formatter for SmokePing (http://oss.oetiker.ch/smokeping/)
    """
    def add_data(self, name, ip, probe):
        self.config.append(dedent("""
            ++ %(name)s
            menu = %(name)s
            title = %(name)s
            probe = %(probe)s
            host = %(ip)s
            #alerts = someloss

            """ % {"name": name, "ip": ip, "probe": probe}))

    def add_section(self, name):
        self.config.append(dedent("""
            + %(name)s
            menu = %(name)s
            title = %(name)s

            """ % {"name": name}))


def create_config(srcdir, exclude, fmtclass):
    """
    Generates a configuration using all files in srcdir
    (non-recursively) excluding communities from 'exclude'.

    The files are read in lexicographic order to produce deterministic
    results.
    """
    formatter = fmtclass()

    for community, data in get_communities_data(srcdir, exclude):
        try:
            bgp = data['bgp']
        except (TypeError, KeyError):
            continue

        formatter.add_section(community)

        for host in sorted(bgp.keys()):
            d = bgp[host]
            if 'ipv4' in d:
                peer = d['ipv4']
                formatter.add_data("ipv4-{}".format(host), peer, 'FPing')
            if 'ipv6' in d:
                peer = d['ipv6']
                formatter.add_data("ipv6-{}".format(host), peer, 'FPing6')

    print(formatter.finalize())
