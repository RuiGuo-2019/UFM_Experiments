# Modify the subcircuits of the given iteration for bus naming issue 
iter=ITERNUM
subcircuit=STRCIRCUITDATAFOLDER
replacement=REPLACEMENTNUM
sed -i 's/\[/_/g' $subcircuit/sub_circuit/iter$iter/sub_ckt_*/sub_ckt_*_yosys_minname.v
sed -i 's/\]/_/g' $subcircuit/sub_circuit/iter$iter/sub_ckt_*/sub_ckt_*_yosys_minname.v
sed -i 's/\]/_/g' $subcircuit/sub_circuit/iter$iter/top.v
sed -i 's/\[/_/g' $subcircuit/sub_circuit/iter$iter/top.v

# Find all the necessary sub-circuits and top RTLs for the given iteration
echo "analyze -format sverilog {" > read_$iter.tcl
ls $subcircuit/sub_circuit/iter$iter/top.v >> read_$iter.tcl
find $subcircuit/sub_circuit/iter$iter/ -name "sub*_yosys_minname.v" >> read_$iter.tcl
echo "}" >> read_$iter.tcl
