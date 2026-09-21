#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

iverilog -g2012 -s inv_tb -o "$build_dir/inv_tb" Verilog/inv.v Verilog/inv_tb.v
vvp "$build_dir/inv_tb"
