#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import sys
from _socket import AF_INET6, AF_INET, inet_pton

import jinja2

from resources.apireader import get_api_dict, get_api_data

from resources.filereader import get_communities_data

template_dict = {"ip-netze.j2": """====IPv6====
{| class="wikitable sortable"
|- bgcolor="#efefef"
! Netzwerk
! Community
! AS
! Kontakt (tech-c)
{% for network in ipv6networks %}
|-
| {{ network.network }}
{%- if network.community_url != "" %}
| [{{ network.community_url }} {{ network.community_name }}]
{%- else %}
| {{ network.community_name }}
{%- endif %}
| {{ network.asn }}
| {% for mail in network.techc -%}
{{- "[mailto:%s Mail]"|format(mail)|replace('@','--at--') -}}
{%- if not loop.last %}, {% endif -%}
{%- endfor -%}
{%- endfor %}
|- bgcolor="#efefef"
! Netzwerk
! Community
! AS
! Kontakt (tech-c)
|}

====IPv4====
{| class="wikitable sortable"
|- bgcolor="#efefef"
! Netzwerk
! Community
! AS
! Kontakt (tech-c)
{% for network in ipv4networks %}
|-
| {{ network.network }}
{%- if network.community_url != "" %}
| [{{ network.community_url }} {{ network.community_name }}]
{%- else %}
| {{ network.community_name }}
{%- endif %}
| {{ network.asn }}
| {% for mail in network.techc -%}
{{- "[mailto:%s Mail]"|format(mail)|replace('@','--at--') -}}
{%- if not loop.last %}, {% endif -%}
{%- endfor -%}
{%- endfor %}
|- bgcolor="#efefef"
! Netzwerk
! Community
! AS
! Kontakt (tech-c)
|}"""}


def get_networklist(meta_src, api_data, family):
    """
    Returns a sorted list of all freifunk networks (family:ipv4/ipv6).
    Each entry is a dict containing the network and
    additional information about the network (asn, tech-c, community_name and community_url).
    """
    all_networks = []

    for community, data in get_communities_data(srcdir=meta_src, exclude=""):
        try:
            networks = data["networks"][family]
        except (TypeError, KeyError):  # NOTE: no networks configured
            continue

        asn = data.get("asn", "")
        techc = list(data.get("tech-c", list()))
        community_url = api_data.get(community, dict()).get("url", "")
        community_name = api_data.get(community, dict()).get("name", community)

        for network in networks:
            all_networks.append({"network": network,
                                 "community_name": community_name,
                                 "community_url": community_url,
                                 "asn": asn,
                                 "techc": techc})

    adr_family = AF_INET6 if family == "ipv6" else AF_INET
    all_networks = sorted(all_networks, key=lambda x:
                          inet_pton(adr_family, x["network"].split("/")[0]))
    return all_networks


def mkwikitable(meta_src):
    if not os.path.isdir(meta_src):
        print("Error: Couldn't find icvpn-meta repository {}.".format(meta_src), file=sys.stderr)
        return

    api_dict = get_api_dict()
    api_data = get_api_data(api_dict)

    ipv6networks = get_networklist(meta_src, api_data, family="ipv6")
    ipv4networks = get_networklist(meta_src, api_data, family="ipv4")

    template_loader = jinja2.DictLoader(template_dict)
    template_env = jinja2.Environment(loader=template_loader)

    template_name = "ip-netze.j2"
    template = template_env.get_template(template_name)
    context = {"ipv4networks": ipv4networks, "ipv6networks": ipv6networks}

    output = template.render(context)

    print(output)
