# run_metrics.tcl — Paper-style FPGA metrics extraction.
#
# Matches JETC paper methodology:
#   Part:      xc7s100fgga676-2 (Spartan-7)
#   Synth:     synth_design -flatten_hierarchy rebuilt  (Default directive)
#   Impl:      opt_design; place_design; route_design   (Default directive)
#   Inverters: LUT1 cells set DONT_TOUCH after synth (preserves inverter count)
#
# Outputs a JSON with:
#   synth_luts      — LUT count after synthesis
#   synth_lut1      — LUT1 (inverter) count after synthesis
#   logic_levels    — critical-path logic levels (after synth, post-route removed)
#   impl_luts       — LUT count after place+route
#   impl_lut1       — LUT1 (inverter) count after place+route
#   delay_ns        — post-route critical-path data-path delay
#   logic_ns        — logic portion of critical-path delay
#   route_ns        — routing portion of critical-path delay
#   logic_power_mw  — on-chip logic dynamic power (mW)
#   signal_power_mw — on-chip signal dynamic power (mW)
#   dynamic_power_mw— total on-chip dynamic power (mW)
#
# Args: --verilog <path> --top <name> --part <name> --period <ns> --out-json <path>

set verilog_path ""
set top_name     "top"
set part_name    "xc7s100fgga676-2"
set clk_period   10.0
set out_json     ""

set i 0
while {$i < [llength $argv]} {
    set a [lindex $argv $i]
    switch -- $a {
        --verilog  { incr i; set verilog_path [lindex $argv $i] }
        --top      { incr i; set top_name     [lindex $argv $i] }
        --part     { incr i; set part_name    [lindex $argv $i] }
        --period   { incr i; set clk_period   [lindex $argv $i] }
        --out-json { incr i; set out_json     [lindex $argv $i] }
        default    { puts "WARN: unknown arg $a" }
    }
    incr i
}

if {$verilog_path eq "" || $out_json eq ""} {
    puts "ERROR: --verilog and --out-json are required"
    exit 1
}

puts "==== run_metrics.tcl ===="
puts "  verilog : $verilog_path"
puts "  top     : $top_name"
puts "  part    : $part_name"
puts "  period  : $clk_period ns"
puts "  out     : $out_json"

# ---- read & synthesize ----
read_verilog $verilog_path
synth_design -top $top_name -part $part_name -flatten_hierarchy rebuilt

create_clock -period $clk_period -name clk [get_ports clk]

# Preserve inverters: set DONT_TOUCH on all LUT1 cells so opt_design / P&R
# cannot absorb them into adjacent LUTs.  This mirrors the paper's explicit
# LUT1 dont_touch methodology that makes inverter reduction visible in LUT count.
set lut1_after_synth [get_cells -hierarchical -filter {REF_NAME == LUT1} -quiet]
if {[llength $lut1_after_synth] > 0} {
    set_property DONT_TOUCH true $lut1_after_synth
}

# ---- synth metrics ----
set synth_luts [llength [get_cells -hierarchical -filter {REF_NAME =~ LUT*} -quiet]]
set synth_lut1 [llength [get_cells -hierarchical -filter {REF_NAME == LUT1} -quiet]]

# Logic levels from critical path (before P&R)
set synth_paths [get_timing_paths -max_paths 1 -nworst 1 -quiet]
set logic_levels 0
if {[llength $synth_paths] > 0} {
    set logic_levels [get_property LOGIC_LEVELS [lindex $synth_paths 0]]
}

puts "  synth_luts=$synth_luts  synth_lut1=$synth_lut1  logic_levels=$logic_levels"

# ---- place & route ----
opt_design
place_design
route_design

# ---- impl metrics ----
set impl_luts [llength [get_cells -hierarchical -filter {REF_NAME =~ LUT*} -quiet]]
set impl_lut1 [llength [get_cells -hierarchical -filter {REF_NAME == LUT1} -quiet]]

puts "  impl_luts=$impl_luts  impl_lut1=$impl_lut1"

# Critical path timing: total delay, logic portion, route portion
set impl_paths [get_timing_paths -max_paths 1 -nworst 1 -quiet]
set delay_ns  0.0
set logic_ns  0.0
set route_ns  0.0

if {[llength $impl_paths] > 0} {
    set p [lindex $impl_paths 0]
    set delay_ns [get_property DATAPATH_DELAY $p]

    # Parse logic/route breakdown from report_timing text
    set rpt [report_timing -of_objects $p -return_string -quiet]
    if {[regexp {Data Path Delay:\s+\S+ns\s+\(logic\s+(\S+)ns.*route\s+(\S+)ns} $rpt -> lg rt]} {
        set logic_ns $lg
        set route_ns $rt
    }
}

puts "  delay_ns=$delay_ns  logic_ns=$logic_ns  route_ns=$route_ns"

# Power (Dynamic: Logic + Signals)
set logic_power_mw   0.0
set signal_power_mw  0.0
set dynamic_power_mw 0.0

set pwr_rpt [report_power -return_string -quiet]

# Helper: safe numeric extraction — returns 0.0 if not a number
proc safe_mw {val} {
    if {[catch {set r [expr {$val * 1000.0}]}]} { return 0.0 }
    return $r
}

# Vivado power report format (example lines, varies by version):
#   | Total On-Chip Power (W) | 0.012 |
#   | Dynamic (W)             | 0.001 |
#   |   Logic                 | 0.000 |
#   |   Signals               | 0.001 |
# We match a decimal number (not just \S+) to avoid non-numeric captures.
if {[regexp {\|\s*Dynamic\s*\(W\)\s*\|\s*([\d.eE+-]+)\s*\|} $pwr_rpt -> v]} {
    set dynamic_power_mw [safe_mw $v]
} elseif {[regexp {Total\s+On-Chip\s+Power\s*\(W\)\s*\|\s*([\d.eE+-]+)\s*\|} $pwr_rpt -> v]} {
    set dynamic_power_mw [safe_mw $v]
}
if {[regexp {\|\s*Logic\s*\|\s*([\d.eE+-]+)\s*\|} $pwr_rpt -> v]} {
    set logic_power_mw [safe_mw $v]
}
if {[regexp {\|\s*Signals?\s*\|\s*([\d.eE+-]+)\s*\|} $pwr_rpt -> v]} {
    set signal_power_mw [safe_mw $v]
}

puts "  dyn_power_mw=$dynamic_power_mw  logic_mw=$logic_power_mw  signal_mw=$signal_power_mw"

# ---- write JSON ----
set fh [open $out_json w]
puts $fh "{"
puts $fh "  \"synth_luts\": $synth_luts,"
puts $fh "  \"synth_lut1\": $synth_lut1,"
puts $fh "  \"logic_levels\": $logic_levels,"
puts $fh "  \"impl_luts\": $impl_luts,"
puts $fh "  \"impl_lut1\": $impl_lut1,"
puts $fh "  \"delay_ns\": $delay_ns,"
puts $fh "  \"logic_ns\": $logic_ns,"
puts $fh "  \"route_ns\": $route_ns,"
puts $fh "  \"logic_power_mw\": $logic_power_mw,"
puts $fh "  \"signal_power_mw\": $signal_power_mw,"
puts $fh "  \"dynamic_power_mw\": $dynamic_power_mw"
puts $fh "}"
close $fh

puts "==== run_metrics.tcl: DONE ===="
