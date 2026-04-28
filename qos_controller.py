"""
QoS Priority SDN Controller (POX)
===================================
Place this file in:  ~/pox/ext/qos_controller.py

Run with:
    cd ~/pox
    sudo ./pox.py qos_controller

Traffic priority scheme:
  ICMP  (ping)         → Priority 30  (high   – latency sensitive)
  TCP 80  (HTTP)       → Priority 20  (medium)
  TCP 443 (HTTPS)      → Priority 20  (medium)
  TCP/UDP 5001 (iperf) → Priority 20  (medium)
  Everything else      → Priority 10  (low / best-effort)
"""

import time

import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.packet import ethernet, icmp, ipv4, tcp, udp
from pox.lib.util import dpidToStr

log = core.getLogger()

# ── Traffic class definitions ─────────────────────────────────────────────────
# key: (label, openflow_priority)
CLASSES = {
    "ICMP": ("ICMP / Ping", 30),
    "HTTP": ("HTTP  TCP-80", 20),
    "HTTPS": ("HTTPS TCP-443", 20),
    "IPERF_TCP": ("iPerf TCP-5001", 20),
    "IPERF_UDP": ("iPerf UDP-5001", 20),
    "DEFAULT": ("Best-effort", 10),
}


class QoSSwitch(object):
    """Per-switch instance: learns MACs and installs QoS flow rules."""

    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}
        self.pkt_counts = {k: 0 for k in CLASSES}
        connection.addListeners(self)
        self._install_qos_rules()
        log.info(
            "Switch %s connected – QoS rules installed", dpidToStr(connection.dpid)
        )

    # ── Proactive rules ───────────────────────────────────────────────────────
    def _install_qos_rules(self):
        def send_rule(priority, match):
            msg = of.ofp_flow_mod()
            msg.priority = priority
            msg.match = match
            msg.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
            self.connection.send(msg)

        # ICMP – highest priority
        m = of.ofp_match()
        m.dl_type = 0x0800
        m.nw_proto = 1
        send_rule(CLASSES["ICMP"][1], m)

        # HTTP
        m = of.ofp_match()
        m.dl_type = 0x0800
        m.nw_proto = 6
        m.tp_dst = 80
        send_rule(CLASSES["HTTP"][1], m)

        # HTTPS
        m = of.ofp_match()
        m.dl_type = 0x0800
        m.nw_proto = 6
        m.tp_dst = 443
        send_rule(CLASSES["HTTPS"][1], m)

        # iPerf TCP
        m = of.ofp_match()
        m.dl_type = 0x0800
        m.nw_proto = 6
        m.tp_dst = 5001
        send_rule(CLASSES["IPERF_TCP"][1], m)

        # iPerf UDP
        m = of.ofp_match()
        m.dl_type = 0x0800
        m.nw_proto = 17
        m.tp_dst = 5001
        send_rule(CLASSES["IPERF_UDP"][1], m)

        # Catch-all best-effort
        send_rule(CLASSES["DEFAULT"][1], of.ofp_match())

    # ── Packet-in ─────────────────────────────────────────────────────────────
    def _handle_PacketIn(self, event):
        pkt = event.parsed
        in_port = event.port

        if not pkt.parsed:
            return

        src_mac = pkt.src
        dst_mac = pkt.dst

        # MAC learning
        self.mac_to_port[src_mac] = in_port

        # Classify
        label, priority, key = self._classify(pkt)
        self.pkt_counts[key] += 1

        # Decide output port
        out_port = self.mac_to_port.get(dst_mac, of.OFPP_FLOOD)

        log.info(
            "dpid=%s in=%s %s→%s  [%s pri=%d] →%s",
            dpidToStr(self.connection.dpid),
            in_port,
            src_mac,
            dst_mac,
            label,
            priority,
            out_port if out_port != of.OFPP_FLOOD else "FLOOD",
        )

        # Install forwarding rule once destination is known
        if out_port != of.OFPP_FLOOD:
            self._install_forward_rule(pkt, in_port, out_port, priority)

        # Forward this packet now
        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _classify(self, pkt):
        """Return (label, priority, key) for a parsed packet."""
        ip = pkt.find("ipv4")
        if ip is None:
            return (*CLASSES["DEFAULT"], "DEFAULT")

        if pkt.find("icmp"):
            return (*CLASSES["ICMP"], "ICMP")

        tc = pkt.find("tcp")
        if tc:
            if tc.dstport == 80:
                return (*CLASSES["HTTP"], "HTTP")
            if tc.dstport == 443:
                return (*CLASSES["HTTPS"], "HTTPS")
            if tc.dstport == 5001:
                return (*CLASSES["IPERF_TCP"], "IPERF_TCP")

        ud = pkt.find("udp")
        if ud and ud.dstport == 5001:
            return (*CLASSES["IPERF_UDP"], "IPERF_UDP")

        return (*CLASSES["DEFAULT"], "DEFAULT")

    def _install_forward_rule(self, pkt, in_port, out_port, priority):
        msg = of.ofp_flow_mod()
        msg.priority = priority
        msg.idle_timeout = 30
        msg.match = of.ofp_match.from_packet(pkt, in_port)
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)

    def print_stats(self):
        log.info("  Switch %s:", dpidToStr(self.connection.dpid))
        for key, count in self.pkt_counts.items():
            label, pri = CLASSES[key]
            log.info("    %-14s pri=%2d  pkts=%d", label, pri, count)


# ── Top-level component ───────────────────────────────────────────────────────
class QoSController(object):
    def __init__(self):
        self.switches = {}
        core.openflow.addListeners(self)
        from pox.lib.recoco import Timer

        Timer(15, self._print_all_stats, recurring=True)
        log.info("QoS Controller ready – waiting for switches …")

    def _handle_ConnectionUp(self, event):
        self.switches[event.dpid] = QoSSwitch(event.connection)

    def _handle_ConnectionDown(self, event):
        self.switches.pop(event.dpid, None)
        log.info("Switch %s disconnected", dpidToStr(event.dpid))

    def _print_all_stats(self):
        log.info("══ Traffic Stats ══════════════════")
        for sw in self.switches.values():
            sw.print_stats()
        log.info("═══════════════════════════════════")


def launch():
    core.registerNew(QoSController)
