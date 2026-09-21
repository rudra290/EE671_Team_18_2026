#!/usr/bin/env python3
"""
spice_to_sym.py: SPICE Subcircuit to Xschem Symbol (.sym) & Netlist Converter

Converts SPICE subcircuit blocks into Xschem symbol (.sym) files and extracts
clean, simulation-ready subcircuit netlists (.spice) without testbenches.
Supports both hierarchical subcircuits and fully-flattened transistor-level
(NMOS/PMOS) netlists and schematics.

Usage:
    python3 spice_to_sym.py <spice_file> "<topmost_subckt>" [options]

Examples:
    # Hierarchical extraction & symbol:
    python3 spice_to_sym.py dfxtn.sp "dfxtn"
    python3 spice_to_sym.py nand3b.sp "nand3b"

    # Flattened NMOS/PMOS level netlist:
    python3 spice_to_sym.py dfxtn.sp "dfxtn" --flat
    python3 spice_to_sym.py nand3b.sp "nand3b" --flat

    # Flattened netlist + Xschem schematic with all NMOS & PMOS devices:
    python3 spice_to_sym.py nand3b.sp "nand3b" --flat --gen-sch
    python3 spice_to_sym.py dfxtn.sp "dfxtn" --flat --gen-sch

    # Pin styles & child symbols:
    python3 spice_to_sym.py dfxtn.sp "dfxtn" --pin-style top-bottom
    python3 spice_to_sym.py nand3b.sp "nand3b" --all-syms --gen-sch
"""

import os
import sys
import re
import argparse
from typing import Dict, List, Set, Tuple, Optional


def tokenize_spice_line(line: str) -> List[str]:
    """Tokenizes a SPICE line respecting quoted expressions and key=value pairs."""
    clean = re.split(r"[\$;]", line)[0].strip()
    if not clean:
        return []
    pattern = r"[^\s\"'=]+=(?:'[^']*'|\"[^\"]*\"|[^\s]+)|'[^']*'|\"[^\"]*\"|[^\s]+"
    return re.findall(pattern, clean)


class SpiceParser:
    """Parses SPICE netlists, handles continuations, and extracts subcircuits."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.raw_lines = []
        self.merged_lines = []
        self.subckts: Dict[str, dict] = {}
        self.header_lines: List[str] = []
        self.load_and_preprocess()

    def load_and_preprocess(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Input file not found: {self.filepath}")

        with open(self.filepath, "r", encoding="utf-8", errors="ignore") as f:
            self.raw_lines = f.readlines()

        # Step 1: Merge SPICE line continuations (lines beginning with '+')
        lines = []
        for raw in self.raw_lines:
            line = raw.rstrip("\r\n")
            stripped = line.strip()
            if stripped.startswith("+"):
                continuation = stripped[1:].strip()
                if lines:
                    lines[-1] = lines[-1] + " " + continuation
                else:
                    lines.append(continuation)
            else:
                lines.append(line)
        self.merged_lines = lines

        # Step 2: Extract subcircuits and global headers (.lib, .include, .param)
        current_subckt = None
        for line in self.merged_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("*") or stripped.startswith(";"):
                continue

            tokens = tokenize_spice_line(stripped)
            if not tokens:
                continue

            first_token_lower = tokens[0].lower()

            if first_token_lower == ".subckt":
                if len(tokens) < 2:
                    continue
                name = tokens[1]
                ports = []
                params = []
                for tok in tokens[2:]:
                    if "=" in tok:
                        params.append(tok)
                    else:
                        ports.append(tok)

                current_subckt = {
                    "name": name,
                    "ports": ports,
                    "params": params,
                    "lines": [],
                    "subckt_line": line,
                    "ends_line": "",
                    "instances": [],
                    "transistors": []
                }
            elif first_token_lower == ".ends":
                if current_subckt:
                    current_subckt["ends_line"] = line
                    self.subckts[current_subckt["name"].lower()] = current_subckt
                    current_subckt = None
            else:
                if current_subckt:
                    current_subckt["lines"].append(line)
                else:
                    if first_token_lower in (".lib", ".include", ".param"):
                        self.header_lines.append(line)

        # Step 3: Classify elements within subcircuits
        for sub in self.subckts.values():
            for line in sub["lines"]:
                tokens = tokenize_spice_line(line)
                if not tokens:
                    continue
                pos_tokens = [t for t in tokens[1:] if "=" not in t]
                if not pos_tokens:
                    continue
                target = pos_tokens[-1].lower()
                tok0_lower = tokens[0].lower()

                if target in self.subckts:
                    sub["instances"].append(tokens)
                elif tok0_lower.startswith("m") or any(k in target for k in ["fet", "mos", "sky130_fd_pr"]):
                    sub["transistors"].append(tokens)
                elif tok0_lower.startswith("x"):
                    # Check if it looks like a transistor (e.g. xm, xp, xn)
                    if tok0_lower.startswith("xm") or tok0_lower.startswith("xp") or tok0_lower.startswith("xn"):
                        sub["transistors"].append(tokens)
                    else:
                        sub["instances"].append(tokens)

    def find_topmost_subckt(self) -> str:
        """Find the topmost subcircuit if not explicitly specified."""
        if not self.subckts:
            raise ValueError(f"No .subckt definitions found in {self.filepath}")

        instantiated: Set[str] = set()
        for sub in self.subckts.values():
            for inst in sub["instances"]:
                pos_tokens = [t for t in inst[1:] if "=" not in t]
                if pos_tokens:
                    target = pos_tokens[-1].lower()
                    if target in self.subckts:
                        instantiated.add(target)

        candidates = [name for name in self.subckts if name not in instantiated]
        if candidates:
            return self.subckts[candidates[-1]]["name"]
        last_key = list(self.subckts.keys())[-1]
        return self.subckts[last_key]["name"]

    def get_subcircuit(self, name: str) -> dict:
        key = name.strip().lower()
        if key not in self.subckts:
            available = [s["name"] for s in self.subckts.values()]
            raise KeyError(
                f"Subcircuit '{name}' not found in {self.filepath}.\n"
                f"Available subcircuits: {', '.join(available)}"
            )
        return self.subckts[key]

    def get_dependencies_topological(self, top_name: str) -> List[dict]:
        """Collect all dependent subcircuits in topological order (children first, top last)."""
        visited: List[str] = []

        def dfs(sub_name: str):
            key = sub_name.lower()
            if key not in self.subckts:
                return
            sub = self.subckts[key]
            for inst in sub["instances"]:
                pos_tokens = [t for t in inst[1:] if "=" not in t]
                if pos_tokens:
                    target = pos_tokens[-1].lower()
                    if target in self.subckts and target not in visited:
                        dfs(target)
            if key not in visited:
                visited.append(key)

        dfs(top_name)
        return [self.subckts[k] for k in visited]


class PinAnalyzer:
    """Analyzes and infers pin directions for a subcircuit."""

    SUPPLY_NAMES = re.compile(r"^(v(dd|ss|cc|ee)|gnd|vpwr|vgnd|vdda|vssa|vccd|vssd)$", re.IGNORECASE)
    OUTPUT_NAMES = re.compile(r"^(out.*|q.*|y.*|z.*|dout.*|cout.*|sum.*|b\d+_out)$", re.IGNORECASE)
    INPUT_NAMES = re.compile(r"^(in.*|clk.*|d.*|a.*|b.*|c.*|s.*|rst.*|reset.*|en.*|sel.*|we.*|re.*|addr.*)$", re.IGNORECASE)

    @classmethod
    def infer_direction(cls, port: str, subckt: dict, all_subckts: Dict[str, dict]) -> str:
        p_lower = port.lower()

        # 1. Supply check
        if cls.SUPPLY_NAMES.match(p_lower):
            return "inout"

        # 2. Check transistor connections inside this subcircuit
        # SPICE MOSFET: M/XM name drain gate source bulk model ...
        drives_port = False
        port_as_gate = False

        for tokens in subckt["transistors"]:
            if len(tokens) >= 5:
                drain, gate, source, bulk = [t.lower() for t in tokens[1:5]]
                if p_lower == gate:
                    port_as_gate = True
                if p_lower == drain:
                    drives_port = True

        # Check subcircuit instances
        for inst in subckt.get("instances", []):
            pos_tokens = [t for t in inst[1:] if "=" not in t]
            if len(pos_tokens) >= 2:
                inst_sub_name = pos_tokens[-1].lower()
                inst_ports = pos_tokens[:-1]
                if inst_sub_name in all_subckts:
                    target_sub = all_subckts[inst_sub_name]
                    for idx, port_node in enumerate(inst_ports):
                        if idx < len(target_sub["ports"]):
                            t_port_name = target_sub["ports"][idx]
                            t_dir = cls.infer_direction(t_port_name, target_sub, all_subckts)
                            if port_node.lower() == p_lower:
                                if t_dir == "out":
                                    drives_port = True
                                elif t_dir == "in":
                                    port_as_gate = True

        if drives_port and not port_as_gate:
            return "out"
        if port_as_gate and not drives_port:
            return "in"

        # 3. Fallback to name heuristics
        if cls.OUTPUT_NAMES.match(p_lower):
            return "out"
        if cls.INPUT_NAMES.match(p_lower):
            return "in"

        return "inout"


class NetlistFlattener:
    """Recursively flattens subcircuit hierarchy into primitive transistor-level components."""

    def __init__(self, parser: SpiceParser, delim: str = "_"):
        self.parser = parser
        self.delim = delim

    def flatten(self, top_name: str) -> dict:
        top_subckt = self.parser.get_subcircuit(top_name)
        top_ports = top_subckt["ports"]
        top_ports_map = {p.lower(): p for p in top_ports}

        flattened_lines: List[str] = []
        flattened_transistors: List[List[str]] = []
        internal_nodes: Set[str] = set()
        subckt_groups: List[dict] = []

        def expand_instance(sub_name: str, path_prefix: str, node_map: Dict[str, str], param_map: Dict[str, str]):
            sub = self.parser.get_subcircuit(sub_name)

            has_child_subckts = any(
                tokens and [t for t in tokens[1:] if "=" not in t] and [t for t in tokens[1:] if "=" not in t][-1].lower() in self.parser.subckts
                for tokens in [tokenize_spice_line(l) for l in sub["lines"]]
            )

            leaf_group = None
            if not has_child_subckts:
                leaf_group = {
                    "inst_name": path_prefix or sub["name"],
                    "cell_name": sub["name"],
                    "ports": list(sub["ports"]),
                    "node_map": dict(node_map),
                    "transistors": []
                }
                subckt_groups.append(leaf_group)

            for line in sub["lines"]:
                tokens = tokenize_spice_line(line)
                if not tokens:
                    continue

                pos_tokens = [t for t in tokens[1:] if "=" not in t]
                keyval_tokens = [t for t in tokens[1:] if "=" in t]
                inst_name = tokens[0]

                if not pos_tokens:
                    continue

                target_model_or_subckt = pos_tokens[-1]

                if target_model_or_subckt.lower() in self.parser.subckts:
                    # Nested subcircuit instance to expand
                    child_sub = self.parser.get_subcircuit(target_model_or_subckt)
                    child_inst_nodes = pos_tokens[:-1]
                    child_prefix = f"{path_prefix}{self.delim}{inst_name}" if path_prefix else inst_name

                    # Build child parameter map from defaults + instance arguments
                    child_params = {}
                    for p in child_sub.get("params", []):
                        if "=" in p:
                            k, v = p.split("=", 1)
                            child_params[k.strip().lower()] = v.strip()
                    for kv in keyval_tokens:
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            val = v.strip()
                            for pk, pv in param_map.items():
                                val = re.sub(r"\b" + re.escape(pk) + r"\b", pv, val, flags=re.IGNORECASE)
                            child_params[k.strip().lower()] = val

                    # Map formal ports to parent actual nets
                    child_node_map = {}
                    for idx, port_name in enumerate(child_sub["ports"]):
                        if idx < len(child_inst_nodes):
                            actual_net = child_inst_nodes[idx]
                            actual_lower = actual_net.lower()
                            if actual_net == "0":
                                resolved_net = "0"
                            elif actual_lower in node_map:
                                resolved_net = node_map[actual_lower]
                            else:
                                resolved_net = f"{path_prefix}{self.delim}{actual_net}" if path_prefix else actual_net
                                internal_nodes.add(resolved_net)
                            child_node_map[port_name.lower()] = resolved_net

                    flattened_lines.append(f"* --- Instance: {inst_name} ({child_sub['name']}) [Hierarchy: {child_prefix}] ---")
                    expand_instance(child_sub["name"], child_prefix, child_node_map, child_params)

                else:
                    # Primitive device (Transistor, passive, etc.)
                    # Determine new unique device instance name
                    if path_prefix:
                        lower_inst = inst_name.lower()
                        if lower_inst.startswith("xm_"):
                            leaf_id = inst_name[3:]
                            new_inst = f"XM_{path_prefix}_{leaf_id}"
                        elif lower_inst.startswith("xm"):
                            leaf_id = inst_name[2:]
                            new_inst = f"XM_{path_prefix}_M{leaf_id}" if leaf_id.isdigit() else f"XM_{path_prefix}_{leaf_id}"
                        elif lower_inst.startswith("m"):
                            leaf_id = inst_name[1:]
                            new_inst = f"M_{path_prefix}_M{leaf_id}" if leaf_id.isdigit() else f"M_{path_prefix}_{leaf_id}"
                        elif lower_inst.startswith("x"):
                            new_inst = f"X_{path_prefix}_{inst_name}"
                        else:
                            new_inst = f"{inst_name[0]}_{path_prefix}_{inst_name[1:]}"
                    else:
                        new_inst = inst_name

                    terminals = pos_tokens[:-1]
                    model = pos_tokens[-1]

                    mapped_terminals = []
                    for t in terminals:
                        if t == "0":
                            mapped_terminals.append("0")
                        elif t.lower() in node_map:
                            mapped_terminals.append(node_map[t.lower()])
                        else:
                            resolved = f"{path_prefix}{self.delim}{t}" if path_prefix else t
                            mapped_terminals.append(resolved)
                            internal_nodes.add(resolved)

                    # Parameter substitutions
                    mapped_keyval = []
                    for kv in keyval_tokens:
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            val = v
                            for pk, pv in param_map.items():
                                val = re.sub(r"\b" + re.escape(pk) + r"\b", pv, val, flags=re.IGNORECASE)
                            mapped_keyval.append(f"{k}={val}")
                        else:
                            mapped_keyval.append(kv)

                    device_tokens = [new_inst] + mapped_terminals + [model] + mapped_keyval
                    device_line = " ".join(device_tokens)
                    flattened_lines.append(device_line)
                    flattened_transistors.append(device_tokens)
                    if leaf_group is not None:
                        leaf_group["transistors"].append(device_tokens)

        # Initial top-level parameter map
        top_param_map = {}
        for p in top_subckt.get("params", []):
            if "=" in p:
                k, v = p.split("=", 1)
                top_param_map[k.strip().lower()] = v.strip()

        expand_instance(top_subckt["name"], "", top_ports_map, top_param_map)

        if not subckt_groups and flattened_transistors:
            subckt_groups.append({
                "inst_name": top_subckt["name"],
                "cell_name": top_subckt["name"],
                "ports": list(top_ports),
                "node_map": top_ports_map,
                "transistors": flattened_transistors
            })

        return {
            "name": top_subckt["name"],
            "ports": list(top_ports),
            "params": list(top_subckt["params"]),
            "lines": flattened_lines,
            "subckt_line": top_subckt["subckt_line"],
            "ends_line": top_subckt["ends_line"],
            "instances": [],  # Completely flattened
            "transistors": flattened_transistors,
            "internal_nodes": sorted(list(internal_nodes)),
            "subckt_groups": subckt_groups
        }


class XschemSymbolGenerator:
    """Generates standard Xschem .sym symbol files."""

    def __init__(self, subckt: dict, all_subckts: Dict[str, dict], netlist_filename: str, pin_style: str = "left-right", embed_spice: bool = False, full_netlist_text: str = ""):
        self.subckt = subckt
        self.all_subckts = all_subckts
        self.netlist_filename = netlist_filename
        self.pin_style = pin_style
        self.embed_spice = embed_spice
        self.full_netlist_text = full_netlist_text

    def classify_pins(self) -> Dict[str, List[str]]:
        pins = self.subckt["ports"]
        classified = {"left": [], "right": [], "top": [], "bottom": []}

        for p in pins:
            direction = PinAnalyzer.infer_direction(p, self.subckt, self.all_subckts)
            p_lower = p.lower()

            if self.pin_style == "top-bottom":
                if re.match(r"^(v(dd|cc)|vpwr|vdda)$", p_lower):
                    classified["top"].append(p)
                elif re.match(r"^(v(ss|ee)|gnd|vgnd|vssa)$", p_lower):
                    classified["bottom"].append(p)
                elif direction == "out":
                    classified["right"].append(p)
                else:
                    classified["left"].append(p)
            else:  # left-right
                if direction == "out":
                    classified["right"].append(p)
                else:
                    classified["left"].append(p)

        if not classified["left"] and not classified["right"]:
            classified["left"] = list(pins)
        elif not classified["left"]:
            classified["left"].append(classified["right"].pop(0))

        return classified

    def compute_pin_coordinates(self) -> Dict[str, Tuple[int, int, str]]:
        name = self.subckt["name"]
        ports = self.subckt["ports"]
        classified = self.classify_pins()

        left_pins = classified["left"]
        right_pins = classified["right"]
        top_pins = classified["top"]
        bottom_pins = classified["bottom"]

        n_left = len(left_pins)
        n_right = len(right_pins)

        PIN_STEP = 20  # Strict 20-unit grid snapping

        pin_coords = {}

        # Left pins: centered around 0
        if n_left == 1:
            pin_coords[left_pins[0]] = (-150, 0, "left")
        else:
            y_start = -((n_left - 1) // 2) * PIN_STEP
            for i, p in enumerate(left_pins):
                pin_coords[p] = (-150, y_start + i * PIN_STEP, "left")

        # Right pins: centered around 0
        if n_right == 1:
            pin_coords[right_pins[0]] = (150, 0, "right")
        else:
            y_start = -((n_right - 1) // 2) * PIN_STEP
            for i, p in enumerate(right_pins):
                pin_coords[p] = (150, y_start + i * PIN_STEP, "right")

        # Determine min and max Y of side pins
        all_y = [coord[1] for p, coord in pin_coords.items()]
        min_y = min(all_y) if all_y else 0
        max_y = max(all_y) if all_y else 0

        # Box vertical limits: 20 units beyond extreme pins, or minimum half-height 30
        box_half_h = max(30, max(abs(min_y), abs(max_y)) + 20)
        box_half_h = ((box_half_h + 9) // 10) * 10
        y_top = -box_half_h
        y_bot = box_half_h

        # Top pins
        if top_pins:
            n_top = len(top_pins)
            x_start = -((n_top - 1) // 2) * PIN_STEP
            for i, p in enumerate(top_pins):
                pin_coords[p] = (x_start + i * PIN_STEP, y_top - 20, "top")

        # Bottom pins
        if bottom_pins:
            n_bot = len(bottom_pins)
            x_start = -((n_bot - 1) // 2) * PIN_STEP
            for i, p in enumerate(bottom_pins):
                pin_coords[p] = (x_start + i * PIN_STEP, y_bot + 20, "bottom")

        # Box horizontal limits
        max_pin_len = max([len(p) for p in ports] + [len(name)])
        box_half_w = max(130, max_pin_len * 12 + 40)
        box_half_w = ((box_half_w + 9) // 10) * 10
        x_left = -box_half_w
        x_right = box_half_w

        # Adjust X coordinates for side pins to match box width
        for p in left_pins:
            _, y, side = pin_coords[p]
            pin_coords[p] = (x_left - 20, y, side)
        for p in right_pins:
            _, y, side = pin_coords[p]
            pin_coords[p] = (x_right + 20, y, side)

        return pin_coords

    def compute_box_bounds(self) -> Tuple[int, int, int, int]:
        name = self.subckt["name"]
        ports = self.subckt["ports"]
        classified = self.classify_pins()

        left_pins = classified["left"]
        right_pins = classified["right"]
        n_left = len(left_pins)
        n_right = len(right_pins)
        PIN_STEP = 20

        all_y = []
        if n_left == 1:
            all_y.append(0)
        elif n_left > 1:
            y_start = -((n_left - 1) // 2) * PIN_STEP
            for i in range(n_left):
                all_y.append(y_start + i * PIN_STEP)

        if n_right == 1:
            all_y.append(0)
        elif n_right > 1:
            y_start = -((n_right - 1) // 2) * PIN_STEP
            for i in range(n_right):
                all_y.append(y_start + i * PIN_STEP)

        min_y = min(all_y) if all_y else 0
        max_y = max(all_y) if all_y else 0
        box_half_h = max(30, max(abs(min_y), abs(max_y)) + 20)
        box_half_h = ((box_half_h + 9) // 10) * 10
        y_top = -box_half_h
        y_bot = box_half_h

        max_pin_len = max([len(p) for p in ports] + [len(name)])
        box_half_w = max(130, max_pin_len * 12 + 40)
        box_half_w = ((box_half_w + 9) // 10) * 10
        x_left = -box_half_w
        x_right = box_half_w

        return (x_left, x_right, y_top, y_bot)

    def generate(self) -> str:
        name = self.subckt["name"]
        ports = self.subckt["ports"]
        params = self.subckt["params"]
        pin_coords = self.compute_pin_coordinates()
        x_left, x_right, y_top, y_bot = self.compute_box_bounds()

        # Build Xschem .sym lines
        sym_lines = []
        sym_lines.append("v {xschem version=3.4.5 file_version=1.2}")
        sym_lines.append("G {}")

        template_str = "name=x1"
        if params:
            template_str += " " + " ".join(params)

        format_str = "@name @pinlist @symname"
        if params:
            for p in params:
                pname = p.split("=")[0]
                format_str += f" {pname}=@{pname}"

        k_block = [
            "K {type=subcircuit",
            f'format="{format_str}"',
            f'template="{template_str}"'
        ]

        if self.embed_spice and self.full_netlist_text:
            escaped_netlist = self.full_netlist_text.replace('"', '\\"')
            k_block.append(f'spice_sym_def="{escaped_netlist}"')
        else:
            k_block.append(f'spice_sym_def=".include {self.netlist_filename}"')

        k_block.append("}")
        sym_lines.append("\n".join(k_block))
        sym_lines.append("V {}")
        sym_lines.append("S {}")
        sym_lines.append("E {}")

        # Symbol bounding box (Layer 4)
        sym_lines.append(f"L 4 {x_left} {y_top} {x_right} {y_top} {{}}")
        sym_lines.append(f"L 4 {x_left} {y_bot} {x_right} {y_bot} {{}}")
        sym_lines.append(f"L 4 {x_left} {y_top} {x_left} {y_bot} {{}}")
        sym_lines.append(f"L 4 {x_right} {y_top} {x_right} {y_bot} {{}}")

        # Pin leads (Layer 4)
        for p in ports:
            x, y, side = pin_coords[p]
            if side == "left":
                sym_lines.append(f"L 4 {x} {y} {x_left} {y} {{}}")
            elif side == "right":
                sym_lines.append(f"L 4 {x_right} {y} {x} {y} {{}}")
            elif side == "top":
                sym_lines.append(f"L 4 {x} {y} {x} {y_top} {{}}")
            elif side == "bottom":
                sym_lines.append(f"L 4 {x} {y_bot} {x} {y} {{}}")

        # Pin boxes (B 5) in the EXACT order of the .subckt declaration
        for p in ports:
            x, y, side = pin_coords[p]
            p_dir = PinAnalyzer.infer_direction(p, self.subckt, self.all_subckts)
            sym_lines.append(f"B 5 {x - 2.5} {y - 2.5} {x + 2.5} {y + 2.5} {{name={p} dir={p_dir} }}")

        # Labels (T)
        sym_name_x = -int(len(name) * 4.5)
        sym_lines.append(f"T {{@symname}} {sym_name_x} -6 0 0 0.3 0.3 {{}}")
        sym_lines.append(f"T {{@name}} {x_right + 5} {y_top - 12} 0 0 0.2 0.2 {{}}")

        for p in ports:
            x, y, side = pin_coords[p]
            if side == "left":
                sym_lines.append(f"T {{{p}}} {x_left + 5} {y - 4} 0 0 0.2 0.2 {{}}")
            elif side == "right":
                sym_lines.append(f"T {{{p}}} {x_right - 5} {y - 4} 0 1 0.2 0.2 {{}}")
            elif side == "top":
                sym_lines.append(f"T {{{p}}} {x - 4} {y_top + 5} 1 0 0.2 0.2 {{}}")
            elif side == "bottom":
                sym_lines.append(f"T {{{p}}} {x - 4} {y_bot - 15} 1 0 0.2 0.2 {{}}")

        sym_lines.append("")
        return "\n".join(sym_lines)


class XschemSchematicGenerator:
    """Generates clean Xschem schematics (.sch) with PMOS/NMOS symbols, wire connections, and port pins."""

    @staticmethod
    def generate(subckt: dict, all_subckts: Dict[str, dict]) -> str:
        lines = []
        lines.append("v {xschem version=3.4.5 file_version=1.2}")
        lines.append("G {}")
        lines.append("K {}")
        lines.append("V {}")
        lines.append("S {}")
        lines.append("E {}")

        ports = subckt["ports"]
        input_ports = []
        output_ports = []
        supply_ports = []

        for p in ports:
            p_dir = PinAnalyzer.infer_direction(p, subckt, all_subckts)
            p_lower = p.lower()
            if re.match(r"^(v(dd|ss|cc|ee)|gnd|vpwr|vgnd|vdda|vssa)$", p_lower):
                supply_ports.append(p)
            elif p_dir == "out":
                output_ports.append(p)
            else:
                input_ports.append(p)

        instances = subckt.get("instances", [])

        # =====================================================================
        # HIERARCHICAL SCHEMATIC: Subcircuit instances with interconnected pins
        # =====================================================================
        if instances:
            pin_y = -900
            pin_idx = 1
            for p in supply_ports + input_ports:
                sym_name = "iopin.sym" if p in supply_ports else "ipin.sym"
                lines.append(f"C {{devices/{sym_name}}} 300 {pin_y} 0 0 {{name=p{pin_idx} lab={p}}}")
                lines.append(f"N 300 {pin_y} 380 {pin_y} {{lab={p}}}")
                lines.append(f"C {{devices/lab_wire.sym}} 380 {pin_y} 0 0 {{name=l_io_{pin_idx} lab={p}}}")
                pin_y += 60
                pin_idx += 1

            inst_x = 700
            inst_y = -850
            wire_id = 100

            for inst_tok in instances:
                inst_name = inst_tok[0]
                pos_tokens = [t for t in inst_tok[1:] if "=" not in t]
                if not pos_tokens:
                    continue
                sub_target = pos_tokens[-1]
                inst_nets = pos_tokens[:-1]

                lines.append(f"C {{{sub_target}.sym}} {inst_x} {inst_y} 0 0 {{name={inst_name}}}")

                if sub_target.lower() in all_subckts:
                    target_sub = all_subckts[sub_target.lower()]
                    target_ports = target_sub["ports"]
                    target_sym_gen = XschemSymbolGenerator(target_sub, all_subckts, f"{sub_target}.spice")
                    pin_coords = target_sym_gen.compute_pin_coordinates()

                    for idx, port_name in enumerate(target_ports):
                        if idx < len(inst_nets):
                            net_name = inst_nets[idx]
                            if port_name in pin_coords:
                                px, py, side = pin_coords[port_name]
                                abs_px = inst_x + px
                                abs_py = inst_y + py

                                if side == "left":
                                    lines.append(f"N {abs_px - 40} {abs_py} {abs_px} {abs_py} {{lab={net_name}}}")
                                    lines.append(f"C {{devices/lab_wire.sym}} {abs_px - 40} {abs_py} 0 0 {{name=w_{wire_id} lab={net_name}}}")
                                    wire_id += 1
                                elif side == "right":
                                    lines.append(f"N {abs_px} {abs_py} {abs_px + 40} {abs_py} {{lab={net_name}}}")
                                    lines.append(f"C {{devices/lab_wire.sym}} {abs_px + 40} {abs_py} 0 0 {{name=w_{wire_id} lab={net_name}}}")
                                    wire_id += 1
                                elif side == "top":
                                    lines.append(f"N {abs_px} {abs_py - 40} {abs_px} {abs_py} {{lab={net_name}}}")
                                    lines.append(f"C {{devices/lab_wire.sym}} {abs_px} {abs_py - 40} 0 0 {{name=w_{wire_id} lab={net_name}}}")
                                    wire_id += 1
                                elif side == "bottom":
                                    lines.append(f"N {abs_px} {abs_py} {abs_px} {abs_py + 40} {{lab={net_name}}}")
                                    lines.append(f"C {{devices/lab_wire.sym}} {abs_px} {abs_py + 40} 0 0 {{name=w_{wire_id} lab={net_name}}}")
                                    wire_id += 1

                inst_y += 180

            out_x = inst_x + 400
            out_y = -850
            for p in output_ports:
                lines.append(f"N {out_x} {out_y} {out_x + 80} {out_y} {{lab={p}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {out_x} {out_y} 0 0 {{name=w_{wire_id} lab={p}}}")
                wire_id += 1
                lines.append(f"C {{devices/opin.sym}} {out_x + 80} {out_y} 0 0 {{name=p{pin_idx} lab={p}}}")
                pin_idx += 1
                out_y += 60

            return "\n".join(lines)

        # =====================================================================
        # TRANSISTOR-LEVEL SCHEMATIC: Leaf cells or flattened netlists
        # =====================================================================
        groups = subckt.get("subckt_groups")
        if not groups:
            groups = [{
                "inst_name": subckt["name"],
                "cell_name": subckt["name"],
                "ports": list(subckt["ports"]),
                "node_map": {p.lower(): p for p in subckt["ports"]},
                "transistors": subckt.get("transistors", [])
            }]

        # 1. Place IO Pins on the left
        pin_y = -950
        pin_idx = 1
        # Supplies
        for p in supply_ports:
            lines.append(f"C {{devices/iopin.sym}} 250 {pin_y} 0 0 {{name=p{pin_idx} lab={p}}}")
            lines.append(f"N 250 {pin_y} 330 {pin_y} {{lab={p}}}")
            lines.append(f"C {{devices/lab_wire.sym}} 330 {pin_y} 0 0 {{name=l_io_{pin_idx} lab={p}}}")
            pin_y += 60
            pin_idx += 1

        # Inputs
        for p in input_ports:
            lines.append(f"C {{devices/ipin.sym}} 250 {pin_y} 0 0 {{name=p{pin_idx} lab={p}}}")
            lines.append(f"N 250 {pin_y} 330 {pin_y} {{lab={p}}}")
            lines.append(f"C {{devices/lab_wire.sym}} 330 {pin_y} 0 0 {{name=l_io_{pin_idx} lab={p}}}")
            pin_y += 60
            pin_idx += 1

        # 2. Lay out Subcircuit Groups horizontally (CMOS Top-to-Bottom topology)
        curr_x = 480
        wire_id = 1

        for group in groups:
            inst_name = group["inst_name"]
            cell_name = group["cell_name"]
            transistors = group["transistors"]

            pmos_list = [t for t in transistors if len(t) >= 6 and ("pfet" in t[5].lower() or "pmos" in t[5].lower())]
            nmos_list = [t for t in transistors if len(t) >= 6 and ("nfet" in t[5].lower() or "nmos" in t[5].lower())]

            # Detect subcircuit type
            g_type = "general"
            if len(pmos_list) == 1 and len(nmos_list) == 1:
                p_d, p_g, p_s = pmos_list[0][1], pmos_list[0][2], pmos_list[0][3]
                n_d, n_g, n_s = nmos_list[0][1], nmos_list[0][2], nmos_list[0][3]
                if p_g.lower() == n_g.lower() and (p_d.lower() == n_d.lower() or p_s.lower() == n_d.lower() or p_d.lower() == n_s.lower()):
                    g_type = "inverter"
                elif {p_d.lower(), p_s.lower()} == {n_d.lower(), n_s.lower()}:
                    g_type = "transmission_gate"
            elif len(pmos_list) >= 2 and len(pmos_list) == len(nmos_list):
                p_drains = {t[1].lower() for t in pmos_list}
                p_sources = {t[3].lower() for t in pmos_list}
                n_drains = {t[1].lower() for t in nmos_list}
                n_sources = {t[3].lower() for t in nmos_list}
                if len(p_drains) == 1 or len(p_sources) == 1:
                    g_type = "nand"
                elif len(n_drains) == 1 or len(n_sources) == 1:
                    g_type = "nor"

            # --- RENDER ACCORDING TO DETECTED TYPE ---
            if g_type == "inverter":
                p_tok = pmos_list[0]
                n_tok = nmos_list[0]
                p_inst = p_tok[0]
                p_drain, p_gate, p_source, p_bulk, p_model = p_tok[1:6]
                n_inst = n_tok[0]
                n_drain, n_gate, n_source, n_bulk, n_model = n_tok[1:6]

                in_net = p_gate
                out_net = p_drain

                # Subcircuit group header text
                lines.append(f"T {{{inst_name} ({cell_name})}} {curr_x - 40} -1070 0 0 0.25 0.25 {{}}")

                # PMOS Symbol at (curr_x, -950)
                p_params = [tok.upper() for tok in p_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                lines.append(f"C {{sky130_fd_pr/pfet_01v8.sym}} {curr_x} -950 0 0 {{name={p_inst}")
                for param in p_params:
                    lines.append(param)
                lines.append(f"model={p_model.replace('sky130_fd_pr__', '')}")
                lines.append("spiceprefix=X")
                lines.append("}")

                # PMOS Source & Bulk -> VDD
                if p_source == p_bulk:
                    lines.append(f"N {curr_x + 20} -1030 {curr_x + 20} -950 {{lab={p_source}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -1030 0 0 {{name=w_{wire_id} lab={p_source}}}")
                    wire_id += 1
                else:
                    lines.append(f"N {curr_x + 20} -980 {curr_x + 20} -1030 {{lab={p_source}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -1030 0 0 {{name=w_{wire_id} lab={p_source}}}")
                    wire_id += 1
                    lines.append(f"N {curr_x + 20} -950 {curr_x + 120} -950 {{lab={p_bulk}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 120} -950 0 1 {{name=w_{wire_id} lab={p_bulk}}}")
                    wire_id += 1

                # NMOS Symbol at (curr_x, -750)
                n_params = [tok.upper() for tok in n_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                lines.append(f"C {{sky130_fd_pr/nfet_01v8.sym}} {curr_x} -750 0 0 {{name={n_inst}")
                for param in n_params:
                    lines.append(param)
                lines.append(f"model={n_model.replace('sky130_fd_pr__', '')}")
                lines.append("spiceprefix=X")
                lines.append("}")

                # NMOS Source & Bulk -> VSS
                if n_source == n_bulk:
                    lines.append(f"N {curr_x + 20} -750 {curr_x + 20} -670 {{lab={n_source}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -670 0 0 {{name=w_{wire_id} lab={n_source}}}")
                    wire_id += 1
                else:
                    lines.append(f"N {curr_x + 20} -720 {curr_x + 20} -670 {{lab={n_source}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -670 0 0 {{name=w_{wire_id} lab={n_source}}}")
                    wire_id += 1
                    lines.append(f"N {curr_x + 20} -750 {curr_x + 120} -750 {{lab={n_bulk}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 120} -750 0 1 {{name=w_{wire_id} lab={n_bulk}}}")
                    wire_id += 1

                # Drains vertical connection (OUT)
                lines.append(f"N {curr_x + 20} -920 {curr_x + 20} -780 {{lab={out_net}}}")
                lines.append(f"N {curr_x + 20} -850 {curr_x + 70} -850 {{lab={out_net}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 70} -850 0 0 {{name=w_{wire_id} lab={out_net}}}")
                wire_id += 1

                # Gates vertical connection (IN)
                lines.append(f"N {curr_x - 20} -950 {curr_x - 20} -750 {{lab={in_net}}}")
                lines.append(f"N {curr_x - 60} -850 {curr_x - 20} -850 {{lab={in_net}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x - 60} -850 0 0 {{name=w_{wire_id} lab={in_net}}}")
                wire_id += 1

                curr_x += 240

            elif g_type == "transmission_gate":
                p_tok = pmos_list[0]
                n_tok = nmos_list[0]
                p_inst = p_tok[0]
                p_drain, p_gate, p_source, p_bulk, p_model = p_tok[1:6]
                n_inst = n_tok[0]
                n_drain, n_gate, n_source, n_bulk, n_model = n_tok[1:6]

                lines.append(f"T {{{inst_name} ({cell_name})}} {curr_x - 40} -1070 0 0 0.25 0.25 {{}}")

                # PMOS Symbol at (curr_x, -950)
                p_params = [tok.upper() for tok in p_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                lines.append(f"C {{sky130_fd_pr/pfet_01v8.sym}} {curr_x} -950 0 0 {{name={p_inst}")
                for param in p_params:
                    lines.append(param)
                lines.append(f"model={p_model.replace('sky130_fd_pr__', '')}")
                lines.append("spiceprefix=X")
                lines.append("}")

                # PMOS Gate (p_gate)
                lines.append(f"N {curr_x - 20} -950 {curr_x - 60} -950 {{lab={p_gate}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x - 60} -950 0 0 {{name=w_{wire_id} lab={p_gate}}}")
                wire_id += 1

                # PMOS Bulk (p_bulk) - tap right, rot 0 1 clear of text
                lines.append(f"N {curr_x + 20} -950 {curr_x + 120} -950 {{lab={p_bulk}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 120} -950 0 1 {{name=w_{wire_id} lab={p_bulk}}}")
                wire_id += 1

                # PMOS Source (at -980 up to -1030)
                lines.append(f"N {curr_x + 20} -980 {curr_x + 20} -1030 {{lab={p_source}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -1030 0 0 {{name=w_{wire_id} lab={p_source}}}")
                wire_id += 1

                # PMOS Drain (at -920 down to -870)
                lines.append(f"N {curr_x + 20} -920 {curr_x + 20} -870 {{lab={p_drain}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -870 0 0 {{name=w_{wire_id} lab={p_drain}}}")
                wire_id += 1

                # NMOS Symbol at (curr_x, -750)
                n_params = [tok.upper() for tok in n_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                lines.append(f"C {{sky130_fd_pr/nfet_01v8.sym}} {curr_x} -750 0 0 {{name={n_inst}")
                for param in n_params:
                    lines.append(param)
                lines.append(f"model={n_model.replace('sky130_fd_pr__', '')}")
                lines.append("spiceprefix=X")
                lines.append("}")

                # NMOS Gate (n_gate)
                lines.append(f"N {curr_x - 20} -750 {curr_x - 60} -750 {{lab={n_gate}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x - 60} -750 0 0 {{name=w_{wire_id} lab={n_gate}}}")
                wire_id += 1

                # NMOS Bulk (n_bulk) - tap right, rot 0 1 clear of text
                lines.append(f"N {curr_x + 20} -750 {curr_x + 120} -750 {{lab={n_bulk}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 120} -750 0 1 {{name=w_{wire_id} lab={n_bulk}}}")
                wire_id += 1

                # NMOS Drain (at -780 up to -830)
                lines.append(f"N {curr_x + 20} -780 {curr_x + 20} -830 {{lab={n_drain}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -830 0 0 {{name=w_{wire_id} lab={n_drain}}}")
                wire_id += 1

                # NMOS Source (at -720 down to -670)
                lines.append(f"N {curr_x + 20} -720 {curr_x + 20} -670 {{lab={n_source}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {curr_x + 20} -670 0 0 {{name=w_{wire_id} lab={n_source}}}")
                wire_id += 1

                curr_x += 240

            elif g_type == "nand":
                N = len(pmos_list)
                out_net = pmos_list[0][1]
                vdd_net = pmos_list[0][3]

                # Trace NMOS series stack
                ordered_nmos = []
                cur_net = out_net
                remaining_nmos = list(nmos_list)
                while remaining_nmos:
                    found = None
                    for candidate in remaining_nmos:
                        c_drn, c_src = candidate[1], candidate[3]
                        if c_drn == cur_net:
                            ordered_nmos.append((candidate, c_src))
                            cur_net = c_src
                            found = candidate
                            break
                        elif c_src == cur_net:
                            ordered_nmos.append((candidate, c_drn))
                            cur_net = c_drn
                            found = candidate
                            break
                    if found:
                        remaining_nmos.remove(found)
                    else:
                        ordered_nmos.append((remaining_nmos.pop(0), "unknown"))

                # Align PMOS with NMOS gate inputs
                ordered_pmos = []
                for n_entry in ordered_nmos:
                    n_tok = n_entry[0]
                    n_gate = n_tok[2]
                    match_p = next((p for p in pmos_list if p[2].lower() == n_gate.lower()), None)
                    if match_p and match_p not in ordered_pmos:
                        ordered_pmos.append(match_p)
                for p in pmos_list:
                    if p not in ordered_pmos:
                        ordered_pmos.append(p)

                # Subcircuit group header text
                lines.append(f"T {{{inst_name} ({cell_name})}} {curr_x + ((N-1)*90) - 40} -1070 0 0 0.25 0.25 {{}}")

                # Place PMOS transistors
                for i, p_tok in enumerate(ordered_pmos):
                    px = curr_x + i * 180
                    p_inst = p_tok[0]
                    p_drain, p_gate, p_source, p_bulk, p_model = p_tok[1:6]

                    p_params = [tok.upper() for tok in p_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                    lines.append(f"C {{sky130_fd_pr/pfet_01v8.sym}} {px} -950 0 0 {{name={p_inst}")
                    for param in p_params:
                        lines.append(param)
                    lines.append(f"model={p_model.replace('sky130_fd_pr__', '')}")
                    lines.append("spiceprefix=X")
                    lines.append("}")

                    # Vertical wire connecting VDD rail (-1030), Source (-980), and Bulk (-950)
                    if p_bulk == vdd_net:
                        lines.append(f"N {px + 20} -1030 {px + 20} -950 {{lab={vdd_net}}}")
                    else:
                        lines.append(f"N {px + 20} -980 {px + 20} -1030 {{lab={vdd_net}}}")
                        lines.append(f"N {px + 20} -950 {px + 120} -950 {{lab={p_bulk}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {px + 120} -950 0 1 {{name=w_{wire_id} lab={p_bulk}}}")
                        wire_id += 1

                    # Gate wire to input net
                    lines.append(f"N {px - 60} -950 {px - 20} -950 {{lab={p_gate}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {px - 60} -950 0 0 {{name=w_{wire_id} lab={p_gate}}}")
                    wire_id += 1
                    # Drain vertical wire to OUT rail (-870)
                    lines.append(f"N {px + 20} -920 {px + 20} -870 {{lab={out_net}}}")

                # Horizontal VDD rail
                x_min = curr_x + 20
                x_max = curr_x + (N - 1) * 180 + 20
                lines.append(f"N {x_min} -1030 {x_max} -1030 {{lab={vdd_net}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {x_min} -1030 0 0 {{name=w_{wire_id} lab={vdd_net}}}")
                wire_id += 1

                # Horizontal OUT rail
                lines.append(f"N {x_min} -870 {x_max} -870 {{lab={out_net}}}")
                lines.append(f"N {x_max} -870 {x_max + 60} -870 {{lab={out_net}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {x_max + 60} -870 0 0 {{name=w_{wire_id} lab={out_net}}}")
                wire_id += 1

                # Series NMOS Stack placed at center X
                x_center = curr_x + ((N - 1) // 2) * 180
                ny_top = -750
                ny_bot = -750 + (N - 1) * 140
                x_tap = x_center + 120
                vss_net = "vss"
                common_bulk = ordered_nmos[0][0][4] if ordered_nmos else "vss"

                for k, (n_tok, next_net) in enumerate(ordered_nmos):
                    ny = -750 + k * 140
                    n_inst = n_tok[0]
                    n_drain, n_gate, n_source, n_bulk, n_model = n_tok[1:6]

                    n_params = [tok.upper() for tok in n_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                    lines.append(f"C {{sky130_fd_pr/nfet_01v8.sym}} {x_center} {ny} 0 0 {{name={n_inst}")
                    for param in n_params:
                        lines.append(param)
                    lines.append(f"model={n_model.replace('sky130_fd_pr__', '')}")
                    lines.append("spiceprefix=X")
                    lines.append("}")

                    # Gate wire
                    lines.append(f"N {x_center - 60} {ny} {x_center - 20} {ny} {{lab={n_gate}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {x_center - 60} {ny} 0 0 {{name=w_{wire_id} lab={n_gate}}}")
                    wire_id += 1

                    # Bulk tap to vertical substrate rail
                    lines.append(f"N {x_center + 20} {ny} {x_tap} {ny} {{lab={n_bulk}}}")

                    if k == 0:
                        # Connect top NMOS drain up to OUT rail
                        lines.append(f"N {x_center + 20} -870 {x_center + 20} -780 {{lab={out_net}}}")
                    else:
                        # Connect previous NMOS source to this NMOS drain
                        prev_src_y = -750 + (k - 1) * 140 + 30
                        curr_drn_y = ny - 30
                        int_net = n_drain if n_source == next_net else n_source
                        lines.append(f"N {x_center + 20} {prev_src_y} {x_center + 20} {curr_drn_y} {{lab={int_net}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {x_center + 20} {(prev_src_y + curr_drn_y)//2} 0 0 {{name=w_{wire_id} lab={int_net}}}")
                        wire_id += 1

                    if k == N - 1:
                        # Bottom NMOS source down to VSS line
                        vss_net = n_source if n_source != int_net else n_drain if k > 0 else n_source
                        lines.append(f"N {x_center + 20} {ny + 30} {x_center + 20} {ny + 80} {{lab={vss_net}}}")

                # Substrate tap vertical rail and VSS tie
                lines.append(f"N {x_tap} {ny_top} {x_tap} {ny_bot + 80} {{lab={common_bulk}}}")
                if common_bulk == vss_net:
                    lines.append(f"N {x_center + 20} {ny_bot + 80} {x_tap} {ny_bot + 80} {{lab={vss_net}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {x_center + 20} {ny_bot + 80} 0 0 {{name=w_{wire_id} lab={vss_net}}}")
                    wire_id += 1
                else:
                    lines.append(f"C {{devices/lab_wire.sym}} {x_center + 20} {ny_bot + 80} 0 0 {{name=w_{wire_id} lab={vss_net}}}")
                    wire_id += 1
                    lines.append(f"C {{devices/lab_wire.sym}} {x_tap} {ny_bot + 80} 0 0 {{name=w_{wire_id} lab={common_bulk}}}")
                    wire_id += 1

                curr_x += N * 180 + 60

            elif g_type == "nor":
                N = len(nmos_list)
                out_net = nmos_list[0][1]
                vss_net = nmos_list[0][3]

                # Trace PMOS series stack
                ordered_pmos = []
                cur_net = out_net
                remaining_pmos = list(pmos_list)
                while remaining_pmos:
                    found = None
                    for candidate in remaining_pmos:
                        c_drn, c_src = candidate[1], candidate[3]
                        if c_drn == cur_net:
                            ordered_pmos.append((candidate, c_src))
                            cur_net = c_src
                            found = candidate
                            break
                        elif c_src == cur_net:
                            ordered_pmos.append((candidate, c_drn))
                            cur_net = c_drn
                            found = candidate
                            break
                    if found:
                        remaining_pmos.remove(found)
                    else:
                        ordered_pmos.append((remaining_pmos.pop(0), "unknown"))

                # Align NMOS with PMOS gate inputs
                ordered_nmos = []
                for p_entry in ordered_pmos:
                    p_tok = p_entry[0]
                    p_gate = p_tok[2]
                    match_n = next((n for n in nmos_list if n[2].lower() == p_gate.lower()), None)
                    if match_n and match_n not in ordered_nmos:
                        ordered_nmos.append(match_n)
                for n in nmos_list:
                    if n not in ordered_nmos:
                        ordered_nmos.append(n)

                lines.append(f"T {{{inst_name} ({cell_name})}} {curr_x + ((N-1)*90) - 40} -1070 0 0 0.25 0.25 {{}}")

                # Parallel NMOS at y = -750
                for j, n_tok in enumerate(ordered_nmos):
                    nx = curr_x + j * 180
                    n_inst = n_tok[0]
                    n_drain, n_gate, n_source, n_bulk, n_model = n_tok[1:6]

                    n_params = [tok.upper() for tok in n_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                    lines.append(f"C {{sky130_fd_pr/nfet_01v8.sym}} {nx} -750 0 0 {{name={n_inst}")
                    for param in n_params:
                        lines.append(param)
                    lines.append(f"model={n_model.replace('sky130_fd_pr__', '')}")
                    lines.append("spiceprefix=X")
                    lines.append("}")

                    # NMOS Drain up to OUT rail (-870)
                    lines.append(f"N {nx + 20} -780 {nx + 20} -870 {{lab={out_net}}}")
                    # NMOS Gate
                    lines.append(f"N {nx - 60} -750 {nx - 20} -750 {{lab={n_gate}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {nx - 60} -750 0 0 {{name=w_{wire_id} lab={n_gate}}}")
                    wire_id += 1
                    # NMOS Bulk and Source down to VSS rail (-670)
                    if n_bulk == vss_net:
                        lines.append(f"N {nx + 20} -750 {nx + 20} -670 {{lab={vss_net}}}")
                    else:
                        lines.append(f"N {nx + 20} -720 {nx + 20} -670 {{lab={vss_net}}}")
                        lines.append(f"N {nx + 20} -750 {nx + 120} -750 {{lab={n_bulk}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {nx + 120} -750 0 1 {{name=w_{wire_id} lab={n_bulk}}}")
                        wire_id += 1

                # Horizontal OUT rail
                x_min = curr_x + 20
                x_max = curr_x + (N - 1) * 180 + 20
                lines.append(f"N {x_min} -870 {x_max} -870 {{lab={out_net}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {x_min} -870 0 0 {{name=w_{wire_id} lab={out_net}}}")
                wire_id += 1

                # Horizontal VSS rail
                lines.append(f"N {x_min} -670 {x_max} -670 {{lab={vss_net}}}")
                lines.append(f"C {{devices/lab_wire.sym}} {x_min} -670 0 0 {{name=w_{wire_id} lab={vss_net}}}")
                wire_id += 1

                # Series PMOS Stack placed at center X
                x_center = curr_x + ((N - 1) // 2) * 180
                py_bot = -950
                py_top = -950 - (N - 1) * 140
                x_tap = x_center + 120
                vdd_net = "vdd"
                common_bulk = ordered_pmos[0][0][4] if ordered_pmos else "vdd"

                for k, (p_tok, next_net) in enumerate(ordered_pmos):
                    py = -950 - k * 140
                    p_inst = p_tok[0]
                    p_drain, p_gate, p_source, p_bulk, p_model = p_tok[1:6]

                    p_params = [tok.upper() for tok in p_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                    lines.append(f"C {{sky130_fd_pr/pfet_01v8.sym}} {x_center} {py} 0 0 {{name={p_inst}")
                    for param in p_params:
                        lines.append(param)
                    lines.append(f"model={p_model.replace('sky130_fd_pr__', '')}")
                    lines.append("spiceprefix=X")
                    lines.append("}")

                    # Gate wire
                    lines.append(f"N {x_center - 60} {py} {x_center - 20} {py} {{lab={p_gate}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {x_center - 60} {py} 0 0 {{name=w_{wire_id} lab={p_gate}}}")
                    wire_id += 1

                    # Bulk tap to vertical substrate rail
                    lines.append(f"N {x_center + 20} {py} {x_tap} {py} {{lab={p_bulk}}}")

                    if k == 0:
                        lines.append(f"N {x_center + 20} -920 {x_center + 20} -870 {{lab={out_net}}}")
                    else:
                        prev_src_y = -950 - (k - 1) * 140 - 30
                        curr_drn_y = py + 30
                        int_net = p_drain if p_source == next_net else p_source
                        lines.append(f"N {x_center + 20} {prev_src_y} {x_center + 20} {curr_drn_y} {{lab={int_net}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {x_center + 20} {(prev_src_y + curr_drn_y)//2} 0 0 {{name=w_{wire_id} lab={int_net}}}")
                        wire_id += 1

                    if k == N - 1:
                        vdd_net = p_source if p_source != next_net else p_drain
                        lines.append(f"N {x_center + 20} {py - 30} {x_center + 20} {py - 80} {{lab={vdd_net}}}")

                # Substrate tap vertical rail and VDD tie
                lines.append(f"N {x_tap} {py_top - 80} {x_tap} {py_bot} {{lab={common_bulk}}}")
                if common_bulk == vdd_net:
                    lines.append(f"N {x_center + 20} {py_top - 80} {x_tap} {py_top - 80} {{lab={vdd_net}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {x_center + 20} {py_top - 80} 0 0 {{name=w_{wire_id} lab={vdd_net}}}")
                    wire_id += 1
                else:
                    lines.append(f"C {{devices/lab_wire.sym}} {x_center + 20} {py_top - 80} 0 0 {{name=w_{wire_id} lab={vdd_net}}}")
                    wire_id += 1
                    lines.append(f"C {{devices/lab_wire.sym}} {x_tap} {py_top - 80} 0 0 {{name=w_{wire_id} lab={common_bulk}}}")
                    wire_id += 1

                curr_x += N * 180 + 60

            else:
                # GENERAL FALLBACK
                lines.append(f"T {{{inst_name} ({cell_name})}} {curr_x - 40} -1070 0 0 0.25 0.25 {{}}")
                # PMOS along -950
                for i, p_tok in enumerate(pmos_list):
                    px = curr_x + i * 200
                    p_inst = p_tok[0]
                    p_drain, p_gate, p_source, p_bulk, p_model = p_tok[1:6]

                    p_params = [tok.upper() for tok in p_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                    lines.append(f"C {{sky130_fd_pr/pfet_01v8.sym}} {px} -950 0 0 {{name={p_inst}")
                    for param in p_params:
                        lines.append(param)
                    lines.append(f"model={p_model.replace('sky130_fd_pr__', '')}")
                    lines.append("spiceprefix=X")
                    lines.append("}")

                    if p_source == p_bulk:
                        lines.append(f"N {px + 20} -1030 {px + 20} -950 {{lab={p_source}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {px + 20} -1030 0 0 {{name=w_{wire_id} lab={p_source}}}")
                        wire_id += 1
                    else:
                        lines.append(f"N {px + 20} -980 {px + 20} -1030 {{lab={p_source}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {px + 20} -1030 0 0 {{name=w_{wire_id} lab={p_source}}}")
                        wire_id += 1
                        lines.append(f"N {px + 20} -950 {px + 120} -950 {{lab={p_bulk}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {px + 120} -950 0 1 {{name=w_{wire_id} lab={p_bulk}}}")
                        wire_id += 1

                    lines.append(f"N {px - 60} -950 {px - 20} -950 {{lab={p_gate}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {px - 60} -950 0 0 {{name=w_{wire_id} lab={p_gate}}}")
                    wire_id += 1
                    lines.append(f"N {px + 20} -920 {px + 20} -870 {{lab={p_drain}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {px + 20} -870 0 0 {{name=w_{wire_id} lab={p_drain}}}")
                    wire_id += 1

                # NMOS along -750
                for j, n_tok in enumerate(nmos_list):
                    nx = curr_x + j * 200
                    n_inst = n_tok[0]
                    n_drain, n_gate, n_source, n_bulk, n_model = n_tok[1:6]

                    n_params = [tok.upper() for tok in n_tok[6:] if tok.lower().startswith("w=") or tok.lower().startswith("l=")]
                    lines.append(f"C {{sky130_fd_pr/nfet_01v8.sym}} {nx} -750 0 0 {{name={n_inst}")
                    for param in n_params:
                        lines.append(param)
                    lines.append(f"model={n_model.replace('sky130_fd_pr__', '')}")
                    lines.append("spiceprefix=X")
                    lines.append("}")

                    lines.append(f"N {nx + 20} -830 {nx + 20} -780 {{lab={n_drain}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {nx + 20} -830 0 0 {{name=w_{wire_id} lab={n_drain}}}")
                    wire_id += 1

                    lines.append(f"N {nx - 60} -750 {nx - 20} -750 {{lab={n_gate}}}")
                    lines.append(f"C {{devices/lab_wire.sym}} {nx - 60} -750 0 0 {{name=w_{wire_id} lab={n_gate}}}")
                    wire_id += 1

                    if n_source == n_bulk:
                        lines.append(f"N {nx + 20} -750 {nx + 20} -670 {{lab={n_source}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {nx + 20} -670 0 0 {{name=w_{wire_id} lab={n_source}}}")
                        wire_id += 1
                    else:
                        lines.append(f"N {nx + 20} -720 {nx + 20} -670 {{lab={n_source}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {nx + 20} -670 0 0 {{name=w_{wire_id} lab={n_source}}}")
                        wire_id += 1
                        lines.append(f"N {nx + 20} -750 {nx + 120} -750 {{lab={n_bulk}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {nx + 120} -750 0 1 {{name=w_{wire_id} lab={n_bulk}}}")
                        wire_id += 1

                curr_x += max(len(pmos_list), len(nmos_list), 1) * 200 + 40

        # 3. Output Pins on the Right
        out_y = -850
        for p in output_ports:
            lines.append(f"N {curr_x} {out_y} {curr_x + 80} {out_y} {{lab={p}}}")
            lines.append(f"C {{devices/lab_wire.sym}} {curr_x} {out_y} 0 0 {{name=w_{wire_id} lab={p}}}")
            wire_id += 1
            lines.append(f"C {{devices/opin.sym}} {curr_x + 80} {out_y} 0 0 {{name=p{pin_idx} lab={p}}}")
            pin_idx += 1
            out_y += 60

        return "\n".join(lines)


class XschemTestbenchGenerator:
    """Generates simulation-ready testbench schematics (tb_<cell>.sch)."""

    @staticmethod
    def generate(spice_parser: SpiceParser, top_name: str, sym_filename: str, subckt: dict) -> str:
        lines = []
        lines.append("v {xschem version=3.4.5 file_version=1.2}")
        lines.append("G {}")
        lines.append("K {}")
        lines.append("V {}")
        lines.append("S {}")
        lines.append("E {}")
        lines.append(f"T {{Testbench for {top_name}}} 400 -950 0 0 0.4 0.4 {{}}")
        lines.append("T {Click Simulate to run ngspice analysis} 400 -900 0 0 0.25 0.25 {}")

        # DUT Symbol
        dut_x = 750
        dut_y = -650
        lines.append(f"C {{{sym_filename}}} {dut_x} {dut_y} 0 0 {{name=x1}}")

        sym_gen = XschemSymbolGenerator(subckt, spice_parser.subckts, f"{top_name}.spice")
        pin_coords = sym_gen.compute_pin_coordinates()

        # Extract outside testbench definitions from SPICE parser
        vsource_lines = []
        ctrl_lines = []
        other_instances = []
        in_control = False
        port_to_net = {}

        in_sub = False
        for raw in spice_parser.merged_lines:
            s = raw.strip()
            if not s or s.startswith("*"):
                continue
            first = s.split()[0].lower()
            if first == ".subckt":
                in_sub = True
                continue
            elif first == ".ends":
                in_sub = False
                continue
            elif in_sub:
                continue
            elif first == ".control":
                in_control = True
                ctrl_lines.append(s)
            elif first == ".endc":
                in_control = False
                ctrl_lines.append(s)
            elif in_control:
                ctrl_lines.append(s)
            elif first in [".tran", ".dc", ".ac", ".measure", ".param", ".lib"]:
                ctrl_lines.append(s)
            elif first.startswith("v") and not first.startswith("v_subckt"):
                vsource_lines.append(s)
            elif first.startswith("x"):
                tokens = s.split()
                if tokens[-1].lower() == top_name.lower():
                    inst_nets = tokens[1:-1]
                    for idx, p in enumerate(subckt["ports"]):
                        if idx < len(inst_nets):
                            port_to_net[p] = inst_nets[idx]
                elif tokens[-1].lower() in spice_parser.subckts:
                    other_instances.append(tokens)

        # Default net mappings if not explicitly mapped by an external testbench instance
        for p in subckt["ports"]:
            if p not in port_to_net:
                if p.lower() in ["vss", "gnd", "vgnd", "vssa"]:
                    port_to_net[p] = "0"
                else:
                    port_to_net[p] = p

        # Wire DUT pins
        wire_id = 1
        for p in subckt["ports"]:
            net_name = port_to_net[p]
            if p in pin_coords:
                px, py, side = pin_coords[p]
                abs_px = dut_x + px
                abs_py = dut_y + py

                if net_name == "0":
                    if side == "left":
                        lines.append(f"N {abs_px - 40} {abs_py} {abs_px} {abs_py} {{lab=0}}")
                        lines.append(f"C {{devices/gnd.sym}} {abs_px - 40} {abs_py} 0 0 {{name=gnd_dut_{p} lab=0}}")
                    else:
                        lines.append(f"N {abs_px} {abs_py} {abs_px + 40} {abs_py} {{lab=0}}")
                        lines.append(f"C {{devices/gnd.sym}} {abs_px + 40} {abs_py} 0 0 {{name=gnd_dut_{p} lab=0}}")
                else:
                    if side == "left":
                        lines.append(f"N {abs_px - 40} {abs_py} {abs_px} {abs_py} {{lab={net_name}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {abs_px - 40} {abs_py} 0 0 {{name=w_dut_{wire_id} lab={net_name}}}")
                    else:
                        lines.append(f"N {abs_px} {abs_py} {abs_px + 40} {abs_py} {{lab={net_name}}}")
                        lines.append(f"C {{devices/lab_wire.sym}} {abs_px + 40} {abs_py} 0 0 {{name=w_dut_{wire_id} lab={net_name}}}")
                    wire_id += 1

        # Place Voltage Sources
        vs_x = 350
        vs_y = -750
        vs_idx = 1

        for vs_str in vsource_lines:
            tokens = vs_str.split()
            vs_name = tokens[0]
            pos_node = tokens[1]
            neg_node = tokens[2]
            val_str = " ".join(tokens[3:])

            lines.append(f"C {{devices/vsource.sym}} {vs_x} {vs_y} 0 0 {{name={vs_name} value=\"{val_str}\"}}")
            # Positive wire
            lines.append(f"N {vs_x} {vs_y - 30} {vs_x + 50} {vs_y - 30} {{lab={pos_node}}}")
            lines.append(f"C {{devices/lab_wire.sym}} {vs_x + 50} {vs_y - 30} 0 0 {{name=w_vs_{vs_idx} lab={pos_node}}}")
            vs_idx += 1
            # Negative wire to GND
            lines.append(f"N {vs_x} {vs_y + 30} {vs_x} {vs_y + 50} {{lab=0}}")
            lines.append(f"C {{devices/gnd.sym}} {vs_x} {vs_y + 50} 0 0 {{name=gnd_{vs_idx} lab=0}}")
            vs_idx += 1
            vs_y += 120

        # If no voltage sources were provided in .sp, supply default VDD if vdd is in ports
        if not vsource_lines:
            has_vdd = any(re.match(r"^(v(dd|cc)|vpwr|vdda)$", p.lower()) for p in subckt["ports"])
            if has_vdd:
                lines.append(f"C {{devices/vsource.sym}} {vs_x} {vs_y} 0 0 {{name=VDD value=\"DC 1.8\"}}")
                lines.append(f"N {vs_x} {vs_y - 30} {vs_x + 50} {vs_y - 30} {{lab=vdd}}")
                lines.append(f"C {{devices/lab_wire.sym}} {vs_x + 50} {vs_y - 30} 0 0 {{name=w_vs_{vs_idx} lab=vdd}}")
                vs_idx += 1
                lines.append(f"N {vs_x} {vs_y + 30} {vs_x} {vs_y + 50} {{lab=0}}")
                lines.append(f"C {{devices/gnd.sym}} {vs_x} {vs_y + 50} 0 0 {{name=gnd_{vs_idx} lab=0}}")
                vs_idx += 1

        # Place load or peripheral instances if any (e.g. XLOAD)
        load_x = dut_x + 500
        load_y = -650
        for inst_tok in other_instances:
            inst_name = inst_tok[0]
            pos_tokens = [t for t in inst_tok[1:] if "=" not in t]
            if not pos_tokens:
                continue
            sub_target = pos_tokens[-1]
            inst_nets = pos_tokens[:-1]
            lines.append(f"C {{{sub_target}.sym}} {load_x} {load_y} 0 0 {{name={inst_name}}}")

            if sub_target.lower() in spice_parser.subckts:
                target_sub = spice_parser.subckts[sub_target.lower()]
                target_sym_gen = XschemSymbolGenerator(target_sub, spice_parser.subckts, f"{sub_target}.spice")
                inst_pin_coords = target_sym_gen.compute_pin_coordinates()
                for idx, port_name in enumerate(target_sub["ports"]):
                    if idx < len(inst_nets):
                        net_name = inst_nets[idx]
                        if port_name in inst_pin_coords:
                            px, py, side = inst_pin_coords[port_name]
                            abs_px = load_x + px
                            abs_py = load_y + py
                            if net_name == "0":
                                if side == "left":
                                    lines.append(f"N {abs_px - 40} {abs_py} {abs_px} {abs_py} {{lab=0}}")
                                    lines.append(f"C {{devices/gnd.sym}} {abs_px - 40} {abs_py} 0 0 {{name=gnd_load_{wire_id} lab=0}}")
                                else:
                                    lines.append(f"N {abs_px} {abs_py} {abs_px + 40} {abs_py} {{lab=0}}")
                                    lines.append(f"C {{devices/gnd.sym}} {abs_px + 40} {abs_py} 0 0 {{name=gnd_load_{wire_id} lab=0}}")
                            else:
                                if side == "left":
                                    lines.append(f"N {abs_px - 40} {abs_py} {abs_px} {abs_py} {{lab={net_name}}}")
                                    lines.append(f"C {{devices/lab_wire.sym}} {abs_px - 40} {abs_py} 0 0 {{name=w_load_{wire_id} lab={net_name}}}")
                                else:
                                    lines.append(f"N {abs_px} {abs_py} {abs_px + 40} {abs_py} {{lab={net_name}}}")
                                    lines.append(f"C {{devices/lab_wire.sym}} {abs_px + 40} {abs_py} 0 0 {{name=w_load_{wire_id} lab={net_name}}}")
                            wire_id += 1
            load_y += 180

        # SPICE simulation commands block
        if not ctrl_lines:
            ctrl_lines = [
                ".tran 10p 20n",
                ".control",
                "run",
                "plot all",
                ".endc"
            ]

        ctrl_text = "\n".join(ctrl_lines)
        escaped_ctrl = ctrl_text.replace('"', '\\"')
        lines.append("C {devices/code_shown.sym} 1600 -850 0 0 {name=SPICE_COMMANDS\nonly_toplevel=true\nvalue=\"" + escaped_ctrl + "\"}")

        # Simulation Launcher button
        lines.append("C {devices/launcher.sym} 400 -850 0 0 {name=h1 descr=\"Simulate\" tclcommand=\"xschem netlist; xschem simulate\"}")

        return "\n".join(lines)


class NetlistExtractor:
    """Extracts clean SPICE netlists for hierarchical or flattened circuits."""

    @staticmethod
    def extract(parser: SpiceParser, top_name: str) -> str:
        deps = parser.get_dependencies_topological(top_name)

        out = []
        out.append(f"* Extracted SPICE netlist for {top_name}")
        out.append(f"* Source file: {os.path.basename(parser.filepath)}")
        out.append(f"* Topmost subcircuit: {top_name}")
        out.append("")

        if parser.header_lines:
            out.append("* --- Library and Header Inclusions ---")
            for h in parser.header_lines:
                out.append(h)
            out.append("")

        for sub in deps:
            is_top = (sub["name"].lower() == top_name.lower())
            label = "TOP-LEVEL SUBCIRCUIT" if is_top else "DEPENDENT SUBCIRCUIT"
            out.append(f"* --- {label}: {sub['name']} ---")
            out.append(sub["subckt_line"])
            for line in sub["lines"]:
                out.append(line)
            out.append(sub["ends_line"])
            out.append("")

        return "\n".join(out)

    @staticmethod
    def extract_flat(parser: SpiceParser, flat_subckt: dict) -> str:
        name = flat_subckt["name"]
        transistors = flat_subckt["transistors"]
        pmos_count = sum(1 for t in transistors if len(t) >= 6 and ("pfet" in t[5].lower() or "pmos" in t[5].lower()))
        nmos_count = sum(1 for t in transistors if len(t) >= 6 and ("nfet" in t[5].lower() or "nmos" in t[5].lower()))

        out = []
        out.append(f"* Extracted FLATTENED SPICE netlist for {name}")
        out.append(f"* Source file: {os.path.basename(parser.filepath)}")
        out.append(f"* Topmost subcircuit: {name}")
        out.append(f"* Hierarchy: Flat transistor-level ({len(transistors)} transistors: {pmos_count} PMOS, {nmos_count} NMOS)")
        out.append(f"* Internal nets: {', '.join(flat_subckt.get('internal_nodes', []))}")
        out.append("")

        if parser.header_lines:
            out.append("* --- Library and Header Inclusions ---")
            for h in parser.header_lines:
                out.append(h)
            out.append("")

        out.append(f"* --- FLATTENED TOP-LEVEL SUBCIRCUIT: {name} ---")
        out.append(flat_subckt["subckt_line"])
        for line in flat_subckt["lines"]:
            out.append(line)
        out.append(flat_subckt["ends_line"])
        out.append("")

        return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Convert SPICE subcircuits to Xschem .sym symbol files and extract clean SPICE netlists.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Hierarchical symbol + netlist:
  python3 spice_to_sym.py dfxtn.sp "dfxtn" --all-syms

  # Hierarchical symbols + block-diagram schematics + testbench:
  python3 spice_to_sym.py dfxtn.sp "dfxtn" --all-syms --gen-sch --gen-tb
  python3 spice_to_sym.py nand3b.sp "nand3b" --all-syms --gen-sch --gen-tb

  # Flattened transistor-level netlist (NMOS/PMOS only):
  python3 spice_to_sym.py dfxtn.sp "dfxtn" --flat
  python3 spice_to_sym.py nand3b.sp "nand3b" --flat

  # Flattened netlist + short-free transistor schematic + testbench:
  python3 spice_to_sym.py dfxtn.sp "dfxtn" --flat --gen-sch --gen-tb
  python3 spice_to_sym.py nand3b.sp "nand3b" --flat --gen-sch --gen-tb
        """
    )
    parser.add_argument("spice_file", help="Path to input SPICE file (e.g. dfxtn.sp, nand3b.sp)")
    parser.add_argument(
        "topmost_subckt",
        nargs="?",
        default=None,
        help="Topmost subcircuit name in \"\" (e.g. \"dfxtn\"). If omitted, auto-detected."
    )
    parser.add_argument("-o", "--sym-out", help="Output .sym file path")
    parser.add_argument("-n", "--netlist-out", help="Output .spice netlist path")
    parser.add_argument(
        "--pin-style",
        choices=["left-right", "top-bottom"],
        default="left-right",
        help="Pin layout style: 'left-right' (default, matches demo_sky130A) or 'top-bottom' (VDD on top, VSS on bottom)"
    )
    parser.add_argument(
        "--embed-spice",
        action="store_true",
        help="Embed SPICE netlist directly into the .sym symbol file"
    )
    parser.add_argument(
        "--all-syms",
        action="store_true",
        help="Also generate .sym symbol files for all child subcircuits (hierarchical mode)"
    )
    parser.add_argument(
        "--gen-sch",
        action="store_true",
        help="Also generate an Xschem schematic (.sch) file with symbols, wiring, and port pins"
    )
    parser.add_argument(
        "--gen-tb",
        action="store_true",
        help="Also generate an Xschem testbench schematic (tb_<cell>.sch) with voltage sources and simulation launcher"
    )
    parser.add_argument(
        "--flat", "--flatten",
        dest="flat",
        action="store_true",
        help="Flatten hierarchy down to transistor-level (NMOS/PMOS primitives only, no subcircuit calls)"
    )
    parser.add_argument(
        "--delim",
        default="_",
        help="Delimiter for flattened instance and internal node names (default: '_')"
    )

    args = parser.parse_args()

    spice_parser = SpiceParser(args.spice_file)

    if args.topmost_subckt:
        top_name = args.topmost_subckt.strip().strip('"').strip("'")
    else:
        top_name = spice_parser.find_topmost_subckt()
        print(f"[*] Auto-detected topmost subcircuit: '{top_name}'")

    top_subckt = spice_parser.get_subcircuit(top_name)
    actual_top_name = top_subckt["name"]
    work_dir = os.path.dirname(os.path.abspath(args.spice_file))

    # --- FLATTENED MODE ---
    if args.flat:
        flat_top_name = f"{actual_top_name}_flat"
        flattener = NetlistFlattener(spice_parser, delim=args.delim)
        flat_subckt = flattener.flatten(actual_top_name)
        flat_subckt["name"] = flat_top_name
        flat_subckt["subckt_line"] = f".subckt {flat_top_name} {' '.join(flat_subckt['ports'])}"
        flat_subckt["ends_line"] = f".ends {flat_top_name}"

        default_sym = f"{flat_top_name}.sym"
        default_netlist = f"{flat_top_name}.spice"
        default_sch = f"{flat_top_name}.sch"
        default_tb = f"tb_{flat_top_name}.sch"

        sym_path = args.sym_out or os.path.join(work_dir, default_sym)
        netlist_path = args.netlist_out or os.path.join(work_dir, default_netlist)
        sch_path = os.path.join(work_dir, default_sch)
        tb_path = os.path.join(work_dir, default_tb)
        netlist_filename = os.path.basename(netlist_path)

        clean_netlist = NetlistExtractor.extract_flat(spice_parser, flat_subckt)
        with open(netlist_path, "w", encoding="utf-8") as f:
            f.write(clean_netlist)
        print(f"[+] Flattened SPICE netlist extracted to: {netlist_path}")

        generator = XschemSymbolGenerator(
            subckt=flat_subckt,
            all_subckts=spice_parser.subckts,
            netlist_filename=netlist_filename,
            pin_style=args.pin_style,
            embed_spice=args.embed_spice,
            full_netlist_text=clean_netlist
        )
        sym_content = generator.generate()
        with open(sym_path, "w", encoding="utf-8") as f:
            f.write(sym_content)
        print(f"[+] Xschem symbol generated: {sym_path}")

        if args.gen_sch:
            sch_content = XschemSchematicGenerator.generate(flat_subckt, spice_parser.subckts)
            with open(sch_path, "w", encoding="utf-8") as f:
                f.write(sch_content)
            print(f"[+] Xschem schematic (flat NMOS/PMOS) generated: {sch_path}")

        if args.gen_tb:
            tb_content = XschemTestbenchGenerator.generate(
                spice_parser=spice_parser,
                top_name=actual_top_name,
                sym_filename=os.path.basename(sym_path),
                subckt=flat_subckt
            )
            with open(tb_path, "w", encoding="utf-8") as f:
                f.write(tb_content)
            print(f"[+] Xschem testbench schematic generated: {tb_path}")

        transistors = flat_subckt["transistors"]
        pmos_count = sum(1 for t in transistors if len(t) >= 6 and ("pfet" in t[5].lower() or "pmos" in t[5].lower()))
        nmos_count = sum(1 for t in transistors if len(t) >= 6 and ("nfet" in t[5].lower() or "nmos" in t[5].lower()))

        print("\n--- Flattened Conversion Summary ---")
        print(f"  Circuit:          {actual_top_name}")
        print(f"  Hierarchy:        Flat (Transistor-level)")
        print(f"  Total Transistors: {len(transistors)} ({pmos_count} PMOS, {nmos_count} NMOS)")
        print(f"  Internal Nets:    {len(flat_subckt['internal_nodes'])} ({', '.join(flat_subckt['internal_nodes'])})")
        print(f"  Ports ({len(flat_subckt['ports'])}):       " + ", ".join(
            f"{p} ({PinAnalyzer.infer_direction(p, flat_subckt, spice_parser.subckts)})"
            for p in flat_subckt["ports"]
        ))
        print(f"  Symbol file:      {sym_path}")
        print(f"  Netlist file:     {netlist_path}")
        if args.gen_sch:
            print(f"  Schematic file:   {sch_path}")
        if args.gen_tb:
            print(f"  Testbench file:   {tb_path}")
        print("------------------------------------\n")
        return

    # --- HIERARCHICAL MODE ---
    sym_path = args.sym_out or os.path.join(work_dir, f"{actual_top_name}.sym")
    netlist_path = args.netlist_out or os.path.join(work_dir, f"{actual_top_name}.spice")
    netlist_filename = os.path.basename(netlist_path)

    # 1. Extract clean SPICE netlist
    clean_netlist = NetlistExtractor.extract(spice_parser, actual_top_name)
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(clean_netlist)
    print(f"[+] Clean SPICE netlist extracted to: {netlist_path}")

    # 2. Generate topmost .sym symbol
    generator = XschemSymbolGenerator(
        subckt=top_subckt,
        all_subckts=spice_parser.subckts,
        netlist_filename=netlist_filename,
        pin_style=args.pin_style,
        embed_spice=args.embed_spice,
        full_netlist_text=clean_netlist
    )
    sym_content = generator.generate()
    with open(sym_path, "w", encoding="utf-8") as f:
        f.write(sym_content)
    print(f"[+] Xschem symbol generated: {sym_path}")

    # 3. Optional: generate .sch schematic
    if args.gen_sch:
        sch_path = os.path.join(work_dir, f"{actual_top_name}.sch")
        sch_content = XschemSchematicGenerator.generate(top_subckt, spice_parser.subckts)
        with open(sch_path, "w", encoding="utf-8") as f:
            f.write(sch_content)
        print(f"[+] Xschem schematic generated: {sch_path}")

    # 4. Optional: generate testbench schematic
    if args.gen_tb:
        tb_path = os.path.join(work_dir, f"tb_{actual_top_name}.sch")
        tb_content = XschemTestbenchGenerator.generate(
            spice_parser=spice_parser,
            top_name=actual_top_name,
            sym_filename=os.path.basename(sym_path),
            subckt=top_subckt
        )
        with open(tb_path, "w", encoding="utf-8") as f:
            f.write(tb_content)
        print(f"[+] Xschem testbench schematic generated: {tb_path}")

    # 5. If --all-syms requested, generate symbols for child subcircuits as well
    if args.all_syms:
        deps = spice_parser.get_dependencies_topological(actual_top_name)
        for child in deps:
            child_name = child["name"]
            if child_name.lower() == actual_top_name.lower():
                continue
            c_sym_path = os.path.join(work_dir, f"{child_name}.sym")
            c_gen = XschemSymbolGenerator(
                subckt=child,
                all_subckts=spice_parser.subckts,
                netlist_filename=netlist_filename,
                pin_style=args.pin_style,
                embed_spice=args.embed_spice,
                full_netlist_text=""
            )
            with open(c_sym_path, "w", encoding="utf-8") as f:
                f.write(c_gen.generate())
            print(f"    [+] Child symbol generated: {c_sym_path}")

            if args.gen_sch:
                c_sch_path = os.path.join(work_dir, f"{child_name}.sch")
                c_sch_content = XschemSchematicGenerator.generate(child, spice_parser.subckts)
                with open(c_sch_path, "w", encoding="utf-8") as f:
                    f.write(c_sch_content)
                print(f"    [+] Child schematic generated: {c_sch_path}")

    # Summary report
    print("\n--- Conversion Summary ---")
    print(f"  Circuit:   {actual_top_name}")
    print(f"  Ports ({len(top_subckt['ports'])}):  " + ", ".join(
        f"{p} ({PinAnalyzer.infer_direction(p, top_subckt, spice_parser.subckts)})"
        for p in top_subckt["ports"]
    ))
    deps = [d["name"] for d in spice_parser.get_dependencies_topological(actual_top_name)]
    print(f"  Included Subckts ({len(deps)}): {', '.join(deps)}")
    print(f"  Symbol file:  {sym_path}")
    print(f"  Netlist file: {netlist_path}")
    if args.gen_sch:
        print(f"  Schematic:    {os.path.join(work_dir, f'{actual_top_name}.sch')}")
    if args.gen_tb:
        print(f"  Testbench:    {os.path.join(work_dir, f'tb_{actual_top_name}.sch')}")
    print("--------------------------\n")


if __name__ == "__main__":
    main()
