# SDN QoS Priority Controller — Mininet + POX

> **Orange Problem** — SDN Mininet Simulation Project  
> Individual submission | OpenFlow 1.0 | POX Controller

---

## Problem Statement

Without traffic differentiation, a UDP flood can starve latency-sensitive ICMP pings or real-time streams. This project implements an **SDN QoS controller** using **POX** and **Mininet** that identifies traffic types, assigns OpenFlow priorities, installs flow rules, and measures the latency impact.

---

## Traffic Priority Scheme

| Traffic Class | Match | OpenFlow Priority |
|--------------|-------|-------------------|
| ICMP / Ping | `nw_proto=1` | **30** (highest) |
| HTTP | `nw_proto=6, tp_dst=80` | 20 |
| HTTPS | `nw_proto=6, tp_dst=443` | 20 |
| iPerf TCP | `nw_proto=6, tp_dst=5001` | 20 |
| iPerf UDP | `nw_proto=17, tp_dst=5001` | 20 |
| Best-effort | catch-all | **10** (lowest) |

---

## Topology

```
  h1 (10.0.0.1) ─┐
  h2 (10.0.0.2) ─┤── s1 ── s2 ──┬── h3 (10.0.0.3)
  h4 (10.0.0.4) ─┘               └── h5 (10.0.0.5)
```

- **s1, s2** — OVS switches (OpenFlow 1.0)
- Links: **10 Mbps**, **5 ms delay** via TCLink/HTB
- POX controller on `127.0.0.1:6633`

---

## Repository Structure

```
.
├── qos_controller.py   # POX QoS controller  →  copy to ~/pox/ext/
├── topology.py         # Mininet topology (interactive CLI)
├── test_qos.py         # Automated test + validation script
├── results/            # Auto-created; holds test_results.txt
└── README.md
```

---

## Setup & Installation

### Prerequisites

```bash
sudo apt install -y mininet openvswitch-switch iperf wireshark net-tools
git clone https://github.com/noxrepo/pox ~/pox
```

### Install controller file

```bash
cp qos_controller.py ~/pox/ext/


## References

1. POX Documentation — https://noxrepo.github.io/pox-doc/html/
2. OpenFlow 1.0 Specification — https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf
3. Mininet Documentation — http://mininet.org/docs/
4. Open vSwitch Documentation — https://docs.openvswitch.org/
5. B. Lantz, B. Heller, N. McKeown, "A Network in a Laptop: Rapid Prototyping for Software-Defined Networks," HotNets 2010.
