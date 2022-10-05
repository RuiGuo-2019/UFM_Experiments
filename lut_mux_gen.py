#!/usr/bin/env python3
import itertools
import math
import matplotlib
import numpy as np
in_width = 2
out_width = 2
f = open("./rtl/lut_{1}_{0}.v".format(out_width,in_width), "w")



f.write("module lut_{1}_{0}(\n".format(out_width,in_width))
for IN  in range(in_width):
    f.write("  input in{},\n".format(IN))



for OUT in range(out_width):
    f.write("  output reg out{},\n".format(OUT))



f.write("  input [{}:0] prog_key\n);".format((2**in_width)*out_width - 1))
f.write("\n")



o = 0;
while(o < out_width):
    i = 2**in_width;
    j = 0
    while i > 1:
        i = math.ceil(i / 4);
        f.write("//Iter - {1},{0}\n".format(i, j))
        for l in range(i):
            if ((j==0) & (i != 1)):
                f.write("MX4X1 mux_{0}_{1}_{8} (out_{0}_{1}_{8}_wire, prog_key[{4}], prog_key[{5}], prog_key[{6}], prog_key[{7}], in{2}, in{3});\n".format(l,j,j*2,j*2+1,l*4,l*4+1,l*4+2,l*4+3,o));
            elif ((j > 0) & (i != 1)):
                f.write("MX4X1 mux_{0}_{1}_{9} (out_{0}_{1}_{9}_wire, out_{5}_{4}_{9}_wire, out_{6}_{4}_{9}_wire, out_{7}_{4}_{9}_wire, out_{8}_{4}_{9}_wire, in{2}, in{3});\n".format(l,j,j*2,j*2+1,j-1,4*l,4*l+1,4*l+2,4*l+3,o));
            elif ((j > 0) & (i == 1) & (in_width%2 == 0)):
                f.write("MX4X1 mux_{0}_{1}_{9} (out{9}, out_{5}_{4}_{9}_wire, out_{6}_{4}_{9}_wire, out_{7}_{4}_{9}_wire, out_{8}_{4}_{9}_wire, in{2}, in{3});\n".format(l,j,j*2,j*2+1,j-1,4*l,4*l+1,4*l+2,4*l+3,o));
            elif ((j > 0) & (i == 1) & (in_width%2 == 1)):
                f.write("MX2X1 mux_{0}_{1}_{7} (out{7}, out_{5}_{4}_{7}_wire, out_{6}_{4}_{7}_wire, in{2});\n".format(l,j,j*2,j*2+1,j-1,4*l,4*l+1,o));
            elif ((j == 0) & (i == 1) & (in_width%2 == 0)):
                f.write("MX4X1 mux_{0}_{1}_{8} (out{8}, prog_key[{4}], prog_key[{5}], prog_key[{6}], prog_key[{7}], in{2}, in{3});\n".format(l,j,j*2,j*2+1,4*l,4*l+1,4*l+2,4*l+3,o));
            elif ((j == 0) & (i == 1) & (in_width%2 == 1)):
                f.write("MX2X1 mux_{0}_{1}_{6} (out{6}, prog_key[{4}], prog_key[{5}],, in{2});\n".format(l,j,j*2,j*2+1,4*l,4*l+1,o));               
        j = j + 1;
    o = o + 1;



f.write("endmodule")
f.close()