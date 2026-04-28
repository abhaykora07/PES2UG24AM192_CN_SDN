#!/usr/bin/env python3
"""
QoS Mininet Topology (POX version)
====================================
Topology:
   h1 (10.0.0.1) ─┐
   h2 (10.0.0.2) ─┤── s1 ── s2 ──┬── h3 (10.0.0.3)
   h4 (10.0.0.4) ─┘               └── h5 (10.0.0.5)

Controller: POX on 127.0.0.1:6633 (POX default port)

Run:
    sudo python3 topology.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI


def build():
    setLogLevel("info")

    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
    )

    info("*** Adding POX controller\n")
    net.addController(
        "c0",
        controller=RemoteController,
        ip="127.0.0.1",
        port=6633,          # POX listens on 6633 by default
    )

    info("*** Adding switches\n")
    s1 = net.addSwitch("s1", protocols="OpenFlow10")
    s2 = net.addSwitch("s2", protocols="OpenFlow10")

    info("*** Adding hosts\n")
    h1 = net.addHost("h1", ip="10.0.0.1/24")
    h2 = net.addHost("h2", ip="10.0.0.2/24")
    h3 = net.addHost("h3", ip="10.0.0.3/24")
    h4 = net.addHost("h4", ip="10.0.0.4/24")
    h5 = net.addHost("h5", ip="10.0.0.5/24")

    info("*** Adding links (10 Mbps, 5 ms delay)\n")
    opts = dict(bw=10, delay="5ms", loss=0, use_htb=True)
    net.addLink(h1, s1, **opts)
    net.addLink(h2, s1, **opts)
    net.addLink(h4, s1, **opts)
    net.addLink(s1, s2, **opts)
    net.addLink(h3, s2, **opts)
    net.addLink(h5, s2, **opts)

    info("*** Starting network\n")
    net.start()

    info("\n*** Network ready\n")
    info("    h1=10.0.0.1  h2=10.0.0.2  h3=10.0.0.3\n")
    info("    h4=10.0.0.4  h5=10.0.0.5\n\n")
    info("    Quick tests:\n")
    info("      h1 ping -c5 h3                                   # high-priority ICMP\n")
    info("      h3 iperf -s &  h1 iperf -c 10.0.0.3 -t 10       # medium TCP\n")
    info("      h3 iperf -s -u &  h2 iperf -c 10.0.0.3 -u -b 5M -t 10  # medium UDP\n")
    info("      sh ovs-ofctl dump-flows s1                       # view flow table\n\n")

    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == "__main__":
    build()
