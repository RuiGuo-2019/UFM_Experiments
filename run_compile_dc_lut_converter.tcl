exec rm -rf ./WORK
set module LUT_MODULE_NAME
define_design_lib work -path ./WORK
set target_library [list "/home/UFAD/guor/Public/library/slow_vdd1v0_basicCells_mod.db"]
set link_library [list "/home/UFAD/guor/Public/library/slow_vdd1v0_basicCells_mod.db"]
#set_dont_use [remove_from_collection [get_lib_cells slow_vdd1v0/*] [get_lib_cells {slow_vdd1v0/DFFHQX1 slow_vdd1v0/DFFSHQX1 slow_vdd1v0/DFFRHQX1 slow_vdd1v0/DFFRX1 slow_vdd1v0/NAND2X1 slow_vdd1v0/AND2X1 slow_vdd1v0/XNOR2X1 slow_vdd1v0/XOR2X1 slow_vdd1v0/NOR2X1 slow_vdd1v0/OR2X1 slow_vdd1v0/INVX1 slow_vdd1v0/TLATNX1 slow_vdd1v0/TLATX1 slow_vdd1v0/MX2X1}]]
set_dont_use [remove_from_collection [get_lib_cells slow_vdd1v0/*] [get_lib_cells {slow_vdd1v0/DFFHQX1 slow_vdd1v0/DFFSHQX1 slow_vdd1v0/DFFRHQX1 slow_vdd1v0/DFFRX1 slow_vdd1v0/NAND2X1 slow_vdd1v0/AND2X1 slow_vdd1v0/XNOR2X1 slow_vdd1v0/XOR2X1 slow_vdd1v0/NOR2X1 slow_vdd1v0/OR2X1 slow_vdd1v0/INVX1 slow_vdd1v0/TLATNX1 slow_vdd1v0/TLATX1}]]

set top $module
#source ./read_obf_2.tcl
#source /home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_b05_20221213005900/intermediate_files_b05_20221216103203/iter2/replace_23/read_2.tcl
analyze -format verilog INPUT_LUT_VERILOG_FILE

elaborate -lib work $top
current_design $top

link

#create_clock -name clk [get_ports prog_clk] -waveform {0 5} -period 10
#set_false_path -from [get_ports prog_rst]
current_design $top
#set compile_delete_unloaded_sequential_cells false
#set compile_seqmap_propagate_constants false

set_flatten true
uniquify -force
#ungroup -flatten -all

#set_app_var compile_no_new_cells_at_top_level true
compile -ungroup_all -boundary_optimization -area_effort high
#source ./dft_constraints.tcl
change_name -rules verilog -hierarchy
#exec mkdir ./netlist/${module}
#write_sdc -nosplit "./netlist/${module}/${module}_for_pd.sdc"
#write -format verilog -hierarchy -output "./netlist/${module}.v"
write -format verilog -hierarchy -output "OUTPUT_LUT_GATELEVEL_VERILOG_FILE"
#write_test_protocol -test_mode all_dft -output "./netlist/${module}/${module}_for_pd.spf"
exit
