#!/usr/bin/env python3
"""
QoS Validation Script (POX version)
======================================
Runs two test scenarios automatically:

  Scenario 1 – Latency impact
      Ping h1→h3 baseline, then ping h1→h3 under UDP flood from h2→h3
      Expected: ICMP RTT stays low (high priority) even under congestion

  Scenario 2 – Throughput fairness
      TCP iperf h1→h3 (medium priority) vs UDP flood h2→h3 (best-effort)
      Expected: TCP maintains bandwidth; UDP is squeezed out

Results saved to: results/test_results.txt

Run:
    sudo python3 test_qos.py
"""

import os
import sys
import time

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel

RESULT_DIR  = "results"
RESULT_FILE = os.path.join(RESULT_DIR, "test_results.txt")
os.makedirs(RESULT_DIR, exist_ok=True)


def sep(label, f):
    line = "=" * 60
    msg  = f"\n{line}\n  {label}\n{line}\n"
    print(msg); f.write(msg)


def build_net():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
    )
    net.addController("c0", controller=RemoteController,
                      ip="127.0.0.1", port=6633)

    s1 = net.addSwitch("s1", protocols="OpenFlow10")
    s2 = net.addSwitch("s2", protocols="OpenFlow10")

    h1 = net.addHost("h1", ip="10.0.0.1/24")
    h2 = net.addHost("h2", ip="10.0.0.2/24")
    h3 = net.addHost("h3", ip="10.0.0.3/24")

    opts = dict(bw=10, delay="5ms", loss=0, use_htb=True)
    net.addLink(h1, s1, **opts)
    net.addLink(h2, s1, **opts)
    net.addLink(s1, s2, **opts)
    net.addLink(h3, s2, **opts)

    net.start()
    time.sleep(3)   # give POX time to push rules
    return net


def dump_flows(net, f):
    sep("Flow Tables", f)
    for sw in net.switches:
        msg = f"\n--- {sw.name} ---\n"
        out = sw.cmd("ovs-ofctl dump-flows " + sw.name)
        print(msg + out); f.write(msg + out + "\n")


def scenario1(net, f):
    sep("Scenario 1 – Latency: ICMP Priority vs UDP Flood", f)
    h1, h2, h3 = net.get("h1", "h2", "h3")

    msg = "\n[1a] Baseline ping h1→h3 (no background traffic)\n"
    print(msg); f.write(msg)
    out = h1.cmd("ping -c 10 -i 0.2 10.0.0.3")
    print(out); f.write(out)

    msg = "\n[1b] Starting UDP flood h2→h3 (best-effort) …\n"
    print(msg); f.write(msg)
    h3.cmd("iperf -s -u &")
    time.sleep(0.5)
    h2.cmd("iperf -c 10.0.0.3 -u -b 9M -t 25 &")
    time.sleep(1)

    msg = "\n[1b] Ping h1→h3 UNDER UDP flood (ICMP = high priority)\n"
    print(msg); f.write(msg)
    out = h1.cmd("ping -c 10 -i 0.2 10.0.0.3")
    print(out); f.write(out)

    h2.cmd("kill %iperf"); h3.cmd("kill %iperf")
    time.sleep(1)


def scenario2(net, f):
    sep("Scenario 2 – Throughput: TCP medium vs UDP best-effort", f)
    h1, h2, h3 = net.get("h1", "h2", "h3")

    h3.cmd("iperf -s &")
    h3.cmd("iperf -s -u &")
    time.sleep(0.5)

    msg = "\n[2] UDP best-effort flood h2→h3 …\n"
    print(msg); f.write(msg)
    h2.cmd("iperf -c 10.0.0.3 -u -b 9M -t 25 &")
    time.sleep(1)

    msg = "\n[2] TCP iperf h1→h3 (medium priority, port 5001) …\n"
    print(msg); f.write(msg)
    out = h1.cmd("iperf -c 10.0.0.3 -t 15 -i 3")
    print(out); f.write(out)

    h2.cmd("kill %iperf"); h3.cmd("kill %iperf")
    time.sleep(1)


def dump_ports(net, f):
    sep("Port Statistics", f)
    for sw in net.switches:
        msg = f"\n--- {sw.name} ---\n"
        out = sw.cmd("ovs-ofctl dump-ports " + sw.name)
        print(msg + out); f.write(msg + out + "\n")


def main():
    setLogLevel("warning")
    print("=== QoS Validation Script (POX) ===")
    print(f"Saving results to: {RESULT_FILE}\n")

    net = build_net()

    with open(RESULT_FILE, "w") as f:
        f.write("QoS SDN Controller (POX) – Test Results\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        dump_flows(net, f)
        scenario1(net, f)
        scenario2(net, f)
        dump_ports(net, f)

        sep("DONE", f)
        f.write(f"Results saved to {RESULT_FILE}\n")

    net.stop()


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("ERROR: Run with sudo"); sys.exit(1)
    main()
