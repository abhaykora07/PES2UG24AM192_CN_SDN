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
```

---

## Running the Project

### Step 1 — Start POX controller (Terminal 1)

```bash
cd ~/pox
sudo ./pox.py qos_controller
```

Expected output:
```
INFO:QoS Controller ready – waiting for switches …
INFO:Switch 00-00-... connected – QoS rules installed
```

### Step 2 — Start Mininet (Terminal 2)

Interactive mode:
```bash
sudo python3 topology.py
```

Or run automated tests:
```bash
sudo python3 test_qos.py
```

---

## Manual Test Commands (inside Mininet CLI)

```bash
# Basic connectivity check
mininet> pingall

# Scenario 1a – Baseline ICMP latency (high priority)
mininet> h1 ping -c 10 h3

# Scenario 1b – ICMP under UDP flood
mininet> h3 iperf -s -u &
mininet> h2 iperf -c 10.0.0.3 -u -b 9M -t 30 &
mininet> h1 ping -c 10 h3          # RTT should stay low

# Scenario 2 – TCP throughput vs UDP flood
mininet> h3 iperf -s &
mininet> h2 iperf -c 10.0.0.3 -u -b 9M -t 30 &
mininet> h1 iperf -c 10.0.0.3 -t 15 -i 3

# View flow tables
mininet> sh ovs-ofctl dump-flows s1
mininet> sh ovs-ofctl dump-flows s2

# View port stats
mininet> sh ovs-ofctl dump-ports s1
```

---

## Expected Output

### Flow Table (after traffic)

```
priority=30,ip,nw_proto=1 actions=CONTROLLER
priority=20,tcp,tp_dst=80 actions=CONTROLLER
priority=20,tcp,tp_dst=5001 actions=output:2
priority=10 actions=output:2
```

### Scenario 1 — Latency

| Condition | Expected RTT |
|-----------|-------------|
| Baseline (no background) | ~10–12 ms |
| Under 9 Mbps UDP flood | ~12–15 ms (ICMP protected) |

### Scenario 2 — Throughput

| Stream | Expected |
|--------|----------|
| TCP iperf (priority 20) | ~6–8 Mbps |
| UDP flood (priority 10) | ~2–4 Mbps (squeezed) |

---

## Wireshark

```bash
# List Mininet virtual interfaces
ip link show | grep mn

# Capture on s1-eth1
sudo wireshark -i s1-eth1 &
```

Useful filters: `icmp`, `tcp.port == 5001`, `udp.port == 5001`

---

## SDN Concepts Demonstrated

| Concept | Location in Code |
|---------|-----------------|
| Controller–switch interaction | `_handle_ConnectionUp` |
| `packet_in` event handling | `_handle_PacketIn` |
| Match–action rule design | `_install_qos_rules`, `_install_forward_rule` |
| Proactive rule installation | `_install_qos_rules` (on switch connect) |
| Reactive MAC learning | `mac_to_port` table in `_handle_PacketIn` |
| Priority differentiation | `msg.priority` in `ofp_flow_mod` |
| Flow idle timeouts | `msg.idle_timeout = 30` |
| Performance measurement | `ping`, `iperf`, `ovs-ofctl dump-ports` |

---

## References

1. POX Documentation — https://noxrepo.github.io/pox-doc/html/
2. OpenFlow 1.0 Specification — https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf
3. Mininet Documentation — http://mininet.org/docs/
4. Open vSwitch Documentation — https://docs.openvswitch.org/
5. B. Lantz, B. Heller, N. McKeown, "A Network in a Laptop: Rapid Prototyping for Software-Defined Networks," HotNets 2010.
