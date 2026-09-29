set part xc7z020clg400-1
set top  mic_frontend
set out  ./build/synth_frontend_shared

file mkdir $out
read_verilog [list ./rtl/cic_bank.v ./rtl/fir_bank.v ./rtl/mic_frontend.v]
read_xdc -mode out_of_context ./constraints/ooc_clock.xdc
synth_design -top $top -part $part -mode out_of_context -generic {COEF_FILE="rtl/fir_coefficients.hex"}
report_utilization -file $out/utilization_synth.txt
report_utilization -hierarchical -hierarchical_depth 2 -file $out/utilization_hier.txt
opt_design
place_design
route_design
report_utilization -file $out/utilization.txt
report_timing_summary -file $out/timing.txt
report_power -file $out/power.txt
exit
