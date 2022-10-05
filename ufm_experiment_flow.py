import os
import subprocess
import itertools
import math
import matplotlib
import numpy as np
import time
import copy
import ufm_delete_invalid_conflict_subckt
import argparse
class ufm_experiment_flow:
    def __init__(self, strDataRoot, strRecordFile, strRTL_LUTRoot):
        self.strRTL_LUTRoot = strRTL_LUTRoot
        self.listLUTFiles = self.get_exist_lut_files(self.strRTL_LUTRoot)
        self.strRecordFile = strRecordFile
        self.strInvalidConflictSubcktFile = os.path.join(os.path.split(self.strRecordFile)[0], 'InvalidConflictSubckt.txt')
        self.workdir = os.getcwd()
        self.path_abc = os.path.abspath('/home/UFAD/guor/Codes/Python/MyDemo/UFM/abc-master-Sazadur/abc')
        self.path_sld = os.path.abspath('/home/UFAD/guor/Codes/Python/MyDemo/UFM/FromSazadur/Rui/spramod-host15-logic-encryption-7fdc93c47b0e/bin/sld')
        self.path_template_modify_iters_csh = os.path.join(self.workdir, 'modify_iters.csh')
        self.path_template_modify_top_plx = os.path.join(self.workdir, 'modify_top.plx')
        self.path_template_run_compile_dc_tcl = os.path.join(self.workdir, 'run_compile_dc.tcl')
        self.path_template_get_bench_tcl = os.path.join(self.workdir, 'get_bench.tcl')
        self.strDataRoot = strDataRoot
        self.strScriptsRoot = os.path.split(self.strDataRoot)[0]
        self.strDataRootName = os.path.split(self.strDataRoot)[1]
        self.strIntermediatePath = ""
        self.strIntermediatePath_iter = ""
        self.listGeneratedLut = []
        self.delete_conflict_sub_ckt = False
        self.dictConflictSubCktRecord = {}
        self.listDeleteSubckt = []
        self.listCorrectSubckt = []
        self.nLenDeleteSubcktLastTime = 0
        self.kickone = 0
        self.last_conflict_num = 0
        self.last_regular_num = 0
    
    def get_exist_lut_files(self, strRTL_LUTRoot):
        self.listLUTFiles = os.listdir(strRTL_LUTRoot)
        return self.listLUTFiles


    def modify_iters_csh(self, strIterNum, intReplacement):
        with open(self.path_template_modify_iters_csh, 'r') as fmicsh:
            lines = fmicsh.readlines()
        
        for i in range(len(lines)):
            if('ITERNUM' in lines[i]):
                lines[i] = lines[i].replace('ITERNUM', strIterNum)

            if('STRCIRCUITDATAFOLDER' in lines[i]):
                lines[i] = lines[i].replace('STRCIRCUITDATAFOLDER', self.strDataRoot)

            if('REPLACEMENTNUM' in lines[i]):
                lines[i] = lines[i].replace('REPLACEMENTNUM', str(intReplacement))


        newScriptFile = os.path.join(self.strIntermediatePath, 'modify_iters.csh')
        with open(newScriptFile, 'w') as nfmicsh:
            for line in lines:
                nfmicsh.write(line)
        
        print("Modify csh file finish.")

        os.chdir(self.strIntermediatePath)
        shell = 'modify_iters.csh'
        f = open(shell, 'r')
        cmd = f.read()
        status = subprocess.call(cmd, shell=True, executable='/bin/bash')
        if(0 == status):
            print("Generate read_%s.tcl finish." % strIterNum)
        else:
            print("===ERROR: Cannot generate read_%s.tcl!===" % strIterNum)
        os.chdir(self.workdir)

    def resort_conflict_subckt(self, listConflictSubCkt, listSubcktInfo, nSortMode=0): #Resort conflict subckt from small to large, nSortMode = 0-by input 
        listNewOrderConflictSubCkt = []
        listNewConflictSubCktInfo = []
        if(0 == nSortMode):
            for conflictsubckt in listConflictSubCkt:
                conflictsubckt = conflictsubckt.strip()
                conflictsubckt = conflictsubckt.replace('\n','')
                conflictsubckt = conflictsubckt+'\t'
                listTemp = [i for i in listSubcktInfo if conflictsubckt in i]
                if(1 != len(listTemp)):
                    print('Find more than 1 or no results including %s' % conflictsubckt)
                else:
                    if(5 <= listTemp[0].count('\t')):
                        strTemp = listTemp[0]
                        strTemp = strTemp.strip('\n')
                        while(1 < strTemp.count('\t')):
                            strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                        nInput = int(strTemp[:strTemp.find('\t')])
                        nOutput = int(strTemp[strTemp.find('\t')+len('\t'):])    
                    listTemp.append(nInput)
                    listTemp.append(nOutput)
                    listNewConflictSubCktInfo.append(listTemp)
            
            listNewConflictSubCktInfo = sorted(listNewConflictSubCktInfo,key = lambda x:x[1], reverse = False)
        
        for item in listNewConflictSubCktInfo:
            listNewOrderConflictSubCkt.append(item[0][:item[0].find('\t')])
        
        return listNewOrderConflictSubCkt


    def modify_top_plx_by_conflict_order(self, strIterNum, intReplacement, listDeleteSubckt = [], nReplaceRegularSubckt = 0):
        strIterOrderFile = os.path.join(self.strDataRoot, 'sub_circuit')
        strIterOrderFile = os.path.join(strIterOrderFile, 'iter'+strIterNum)
        strIterOrderFile = os.path.join(strIterOrderFile, '_conflict_subckt.txt')

        with open(strIterOrderFile, 'r') as iof:
            strOrder = iof.readline()
        strOrder = strOrder.replace('[','')
        strOrder = strOrder.replace(']','')
        listOriginalOrder = strOrder.split(',')
        listReplaceCircuits = []



        strIterInfoFile = os.path.join(self.strDataRoot, 'sub_circuit')
        strIterInfoFile = os.path.join(strIterInfoFile, 'iter'+strIterNum)
        strIterInfoFile = os.path.join(strIterInfoFile, '_iter'+strIterNum+'_info.txt')
        with open(strIterInfoFile, 'r') as iif:
            subcktinfo = iif.readlines()
        del(subcktinfo[0])
        del(subcktinfo[0])

        listOrder = self.resort_conflict_subckt(listConflictSubCkt=listOriginalOrder, listSubcktInfo=subcktinfo, nSortMode=0)

        listReplaceOrder = []
        strKey = 'iter'+strIterNum+'_replace'+str(intReplacement)
        self.dictConflictSubCktRecord[strKey] = []
        i = 0
        for i in range(len(listOrder)):
        # for i in range(intReplacement):
            strTemp = listOrder[i].strip()
            if(strTemp in self.listDeleteSubckt):
                continue
            for item in subcktinfo:
                strTemp1 = item[:item.find('\t')+len('\t')]
                strTemp1 = strTemp1.replace('\t','')
                strTemp1 = strTemp1.strip()
                if(strTemp == strTemp1):
                    if(5 <= item.count('\t')):
                        listReplaceOrder.append(item)
                        break
                    else:
                        if(strTemp1 not in self.listDeleteSubckt):
                            self.listDeleteSubckt.append(strTemp1)
            if(intReplacement <= len(listReplaceOrder)):
                break

        with open(self.path_template_modify_top_plx, 'r') as fmtplx:
            lines = fmtplx.readlines()
        
        listTemp = []
        strRedact = "  "
        for i in range(intReplacement):
            if(i >= len(listReplaceOrder)):
                break
            temp = listReplaceOrder[i]
            if(5 > temp.count('\t')):# no io info
                continue
            else:
                strRedact = strRedact + temp[:temp.find('\t')]
                self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                while(1 < temp.count('\t')):
                    temp = temp[temp.find('\t')+len('\t'):]
                temp = temp.replace('\n','')
                temp = temp.replace('\t',' ')
                strLutFileName = 'lut_' + temp + '.v'
                strLutFileName = strLutFileName.replace(' ','_')
                if(strLutFileName not in self.listLUTFiles):
                    self.listLUTFiles.append(strLutFileName)
                    listTemp.append(temp)
                strRedact = strRedact + "  => '" + temp + "'"
                strRedact = strRedact + ',\n  '

        listRegularSubcktRedact = []
        for i in range(len(subcktinfo)):
            if(i >= nReplaceRegularSubckt):
                break
            elif(subcktinfo[i] in listReplaceOrder):
                continue
            else:
                temp = subcktinfo[i]
                if(5 > temp.count('\t')):
                    continue
                listRegularSubcktRedact.append(temp[:temp.find('\t')])
                strRedact = strRedact + temp[:temp.find('\t')]
                while(1 < temp.count('\t')):
                    temp = temp[temp.find('\t')+len('\t'):]
                temp = temp.replace('\n','')
                temp = temp.replace('\t',' ')
                strRedact = strRedact + "  => '" + temp + "'"
                strRedact = strRedact + ',\n  '



        for item in listTemp:
            in_width = int(item[:item.find(' ')])
            out_width = int(item[item.find(' ')+len(' '):])
            # self.lut_gen1(in_width, out_width)
            # self.lut_mux_gen2(in_width, out_width)
            # self.lut_mux_gen3(in_width, out_width)
            self.lut_mux_gen4(in_width, out_width)
        
        if(',\n  ' == strRedact[-4:]):
            strRedact = strRedact[:-4]

        for i in range(len(lines)):
            if('ITERNUM' in lines[i]):
                lines[i] = lines[i].replace('ITERNUM', strIterNum)

            if('STRCIRCUITDATAFOLDER' in lines[i]):
                lines[i] = lines[i].replace('STRCIRCUITDATAFOLDER', self.strDataRoot)

            if('STRSUBCKTANDINPUTOUTPUT' in lines[i]):
                lines[i] = lines[i].replace('STRSUBCKTANDINPUTOUTPUT', strRedact)

            if('REPLACEMENTNUM' in lines[i]):
                lines[i] = lines[i].replace('REPLACEMENTNUM', str(intReplacement))

            if('RTLLUTROOT' in lines[i]):
                lines[i] = lines[i].replace('RTLLUTROOT', self.strRTL_LUTRoot)

            if('INTERMEDIATEFOLDERPATH' in lines[i]):
                lines[i] = lines[i].replace('INTERMEDIATEFOLDERPATH', self.strIntermediatePath)

            

        newScriptFile = os.path.join(self.strIntermediatePath, 'modify_top.plx')
        with open(newScriptFile, 'w') as nfmicsh:
            for line in lines:
                nfmicsh.write(line)
        
        
        print("Modify plx file finish.")

        os.chdir(self.strIntermediatePath)
        strCmd = "perl " + newScriptFile
        status = os.system(strCmd)
        # shell = 'modify_iters.csh'
        # f = open(shell, 'r')
        # cmd = f.read()
        # status = subprocess.call(cmd, shell=True, executable='/bin/bash')
        if(0 == status):
            print("Generate read_obf_%s.tcl finish." % strIterNum)
        else:
            print("===ERROR: Cannot generate read_obf_%s.tcl!===" % strIterNum)
        os.chdir(self.workdir)
        print(strKey + ':' + str(len(self.dictConflictSubCktRecord[strKey])) + str(self.dictConflictSubCktRecord[strKey]))
        
        strConflictSubcktRecord = os.path.join(self.strIntermediatePath, 'conflict_subckt_iter'+strIterNum+'_replace'+str(intReplacement)+'.txt')
        with open(strConflictSubcktRecord, 'w') as cscrf:
            cscrf.write(str(self.dictConflictSubCktRecord[strKey]))
        
        
        if(0 != len(self.listDeleteSubckt)):
            if(len(self.listDeleteSubckt) != self.nLenDeleteSubcktLastTime):
                with open(self.strInvalidConflictSubcktFile, 'a') as sdcscf:
                    sdcscf.write(str(self.listDeleteSubckt)+'\n')
                self.nLenDeleteSubcktLastTime = len(self.listDeleteSubckt)
                self.kickone = 1

                strIterInfoFileRoot = os.path.join(self.strDataRoot, 'sub_circuit')
                strIterInfoFileRoot = os.path.join(strIterInfoFileRoot, 'iter'+strIterNum)
                strInvalidSubckRecordRoot = os.path.split(self.strInvalidConflictSubcktFile)[0]
                ufm_delete_invalid_conflict_subckt.delete_invalid_conflict_subckts(strIterInfoFileRoot, strInvalidSubckRecordRoot)
        return strKey, self.dictConflictSubCktRecord[strKey], listRegularSubcktRedact

    def modify_top_plx(self, strIterNum, intReplacement):
        strIterInfoFile = os.path.join(self.strDataRoot, 'sub_circuit')
        strIterInfoFile = os.path.join(strIterInfoFile, 'iter'+strIterNum)
        strIterInfoFile = os.path.join(strIterInfoFile, '_iter'+strIterNum+'_info.txt')
        with open(strIterInfoFile, 'r') as iif:
            subcktinfo = iif.readlines()
        del(subcktinfo[0])
        del(subcktinfo[0])

        with open(self.path_template_modify_top_plx, 'r') as fmtplx:
            lines = fmtplx.readlines()
        
        listTemp = []
        strRedact = "  "
        for i in range(intReplacement):
            temp = subcktinfo[i]
            if(5 > temp.count('\t')):# no io info
                continue
            else:
                strRedact = strRedact + temp[:temp.find('\t')]
                while(1 < temp.count('\t')):
                    temp = temp[temp.find('\t')+len('\t'):]
                temp = temp.replace('\n','')
                temp = temp.replace('\t',' ')
                if(temp not in listTemp):
                    listTemp.append(temp)
                strRedact = strRedact + "  => '" + temp + "'"
                strRedact = strRedact + ',\n  '

        for item in listTemp:
            in_width = int(item[:item.find(' ')])
            out_width = int(item[item.find(' ')+len(' '):])
            # self.lut_gen1(in_width, out_width)
            # self.lut_mux_gen2(in_width, out_width)
            # self.lut_mux_gen3(in_width, out_width)
            self.lut_mux_gen4(in_width, out_width)
        
        if(',\n  ' == strRedact[-4:]):
            strRedact = strRedact[:-4]

        for i in range(len(lines)):
            if('ITERNUM' in lines[i]):
                lines[i] = lines[i].replace('ITERNUM', strIterNum)

            if('STRCIRCUITDATAFOLDER' in lines[i]):
                lines[i] = lines[i].replace('STRCIRCUITDATAFOLDER', self.strDataRootName)

            if('STRSUBCKTANDINPUTOUTPUT' in lines[i]):
                lines[i] = lines[i].replace('STRSUBCKTANDINPUTOUTPUT', strRedact)

            if('REPLACEMENTNUM' in lines[i]):
                lines[i] = lines[i].replace('REPLACEMENTNUM', str(intReplacement))


        newScriptFile = os.path.join(self.strScriptsRoot, 'modify_top.plx')
        with open(newScriptFile, 'w') as nfmicsh:
            for line in lines:
                nfmicsh.write(line)
        
        print("Modify plx file finish.")

        os.chdir(self.strScriptsRoot)
        status = os.system("perl modify_top.plx")
        # shell = 'modify_iters.csh'
        # f = open(shell, 'r')
        # cmd = f.read()
        # status = subprocess.call(cmd, shell=True, executable='/bin/bash')
        if(0 == status):
            print("Generate read_obf_%s.tcl finish." % strIterNum)
        else:
            print("===ERROR: Cannot generate read_obf_%s.tcl!===" % strIterNum)
        os.chdir(self.workdir)
    
    def lut_mux_gen2(self, in_width, out_width):
        # in_width = 7
        # out_width = 2
        os.chdir(self.strScriptsRoot)
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
                        f.write("MX4X1 mux_{0}_{1}_{9} (out{9}, out_{5}_{4}_{9}_wire, out_{6}_{4}_{9}_wire, out_{7}_{4}_{9}_wire, out_{8}_{4}_{9}_wire, in{2}, in{3});\n".format(l,j,j*2,j*2+1,j,4*l,4*l+1,4*l+2,4*l+3,o));
                    elif ((j == 0) & (i == 1) & (in_width%2 == 1)):
                        f.write("MX2X1 mux_{0}_{1}_{7} (out{7}, out_{5}_{4}_{7}_wire, out_{6}_{4}_{7}_wire, in{2});\n".format(l,j,j*2,j*2+1,j,4*l,4*l+1,o));               
                j = j + 1;
            o = o + 1;

        f.write("endmodule")
        f.close()
        os.chdir(self.workdir)
        print("Generate LUT finish.")



    def lut_mux_gen3(self, in_width, out_width):
        # !/usr/bin/env python3
        # import itertools
        # import math
        # import matplotlib
        # import numpy as np
        # in_width = 1
        # out_width = 2
        strTemp = str(in_width) + ' ' + str(out_width)
        if(strTemp in self.listGeneratedLut):
            print("lut_{1}_{0}.v already exist.".format(out_width,in_width))
            return
        os.chdir(self.strScriptsRoot)
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

        os.chdir(self.workdir)
        print("Generate lut_{1}_{0}.v finish".format(out_width,in_width))


    def lut_mux_gen4(self, in_width, out_width):
        # !/usr/bin/env python3
        # import itertools
        # import math
        # import matplotlib
        # import numpy as np
        # in_width = 1
        # out_width = 2
        strTemp = str(in_width) + ' ' + str(out_width)
        if(strTemp in self.listGeneratedLut):
            print("lut_{1}_{0}.v already exist.".format(out_width,in_width))
            return
        self.listGeneratedLut.append(strTemp)
        os.chdir(self.strScriptsRoot)
        # #!/usr/bin/env python3
        # import itertools
        # import math
        # import matplotlib
        # import numpy as np
        # in_width = 4
        # out_width = 2
        filepath = os.path.join(self.strRTL_LUTRoot, "lut_{1}_{0}.v".format(out_width,in_width))
        # f = open("./rtl/lut_{1}_{0}.v".format(out_width,in_width), "w")
        f = open(filepath, "w")



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
                f.write("//Iter - {1},{0},{2}\n".format(i, j, o))
                for l in range(i):
                    if ((j==0) & (i != 1)):
                        f.write("MX4X1 mux_{0}_{1}_{8} (out_{0}_{1}_{8}_wire, prog_key[{4}], prog_key[{5}], prog_key[{6}], prog_key[{7}], in{2}, in{3});\n".format(l,j,j*2,j*2+1,(l)*4+(o*(2**in_width)),(l)*4+1+(o*(2**in_width)),(l)*4+2+(o*(2**in_width)),(l)*4+3+(o*(2**in_width)),o));
                    elif ((j > 0) & (i != 1)):
                        f.write("MX4X1 mux_{0}_{1}_{9} (out_{0}_{1}_{9}_wire, out_{5}_{4}_{9}_wire, out_{6}_{4}_{9}_wire, out_{7}_{4}_{9}_wire, out_{8}_{4}_{9}_wire, in{2}, in{3});\n".format(l,j,j*2,j*2+1,j-1,4*l,4*l+1,4*l+2,4*l+3,o));
                    elif ((j > 0) & (i == 1) & (in_width%2 == 0)):
                        f.write("MX4X1 mux_{0}_{1}_{9} (out{9}, out_{5}_{4}_{9}_wire, out_{6}_{4}_{9}_wire, out_{7}_{4}_{9}_wire, out_{8}_{4}_{9}_wire, in{2}, in{3});\n".format(l,j,j*2,j*2+1,j-1,4*l,4*l+1,4*l+2,4*l+3,o));
                    elif ((j > 0) & (i == 1) & (in_width%2 == 1)):
                        f.write("MX2X1 mux_{0}_{1}_{7} (out{7}, out_{5}_{4}_{7}_wire, out_{6}_{4}_{7}_wire, in{2});\n".format(l,j,j*2,j*2+1,j-1,4*l,4*l+1,o));
                    elif ((j == 0) & (i == 1) & (in_width%2 == 0)):
                        f.write("MX4X1 mux_{0}_{1}_{8} (out{8}, prog_key[{4}], prog_key[{5}], prog_key[{6}], prog_key[{7}], in{2}, in{3});\n".format(l,j,j*2,j*2+1,4*l+(o*(2**in_width)),4*l+(o*(2**in_width))+1,4*l+(o*(2**in_width))+2,4*l+(o*(2**in_width))+3,o));
                    elif ((j == 0) & (i == 1) & (in_width%2 == 1)):
                        f.write("MX2X1 mux_{0}_{1}_{6} (out{6}, prog_key[{4}], prog_key[{5}],, in{2});\n".format(l,j,j*2,j*2+1,4*l+(o*(2**in_width)),4*l+(o*(2**in_width))+1,o));               
                j = j + 1;
            o = o + 1;



        f.write("endmodule")
        f.close()
        os.chdir(self.workdir)
        print("Generate lut_{1}_{0}.v finish".format(out_width,in_width))
        

    def lut_gen1(self, in_width, out_width):
        os.chdir(self.strScriptsRoot)
        f = open("rtl/lut_{1}_{0}.v".format(out_width,in_width), "w")

        f.write("module lut_{1}_{0}(\n".format(out_width,in_width))
        for IN  in range(in_width):
            f.write("  input in{},\n".format(IN))

        for OUT in range(out_width):
            f.write("  output reg out{},\n".format(OUT))

        f.write("  input [{}:0] prog_key\n);".format((2**in_width)*out_width - 1))

        f.write("\n")

        f.write("")

        f.write("  always @(")
        for IN  in range(in_width-1):
            f.write("in{},".format(IN))
        f.write("in{}".format(in_width-1))
        f.write(") begin\n")

        f.write("    case ({ ")
        for IN  in range(in_width-1):
            f.write("in{},".format(IN))
        f.write("in{}".format(in_width-1))
        f.write(" })\n")

        for IN  in range(2 ** in_width):
            f.write("      {3}'b{2:0{3}b}: ".format(IN*out_width,(IN+1)*out_width-1,IN,in_width))
            f.write("{")
            for OUT in range(out_width-1):
                f.write("out{},".format(OUT))
            f.write("out{}".format(out_width-1))
            f.write("}")
            f.write(" <= prog_key[{1}:{0}];\n".format(IN*out_width,(IN+1)*out_width-1,IN,in_width))
            
        f.write("      default: ")
        f.write("{")
        for OUT in range(out_width-1):
            f.write("out{},".format(OUT))
        f.write("out{}".format(out_width-1))
        f.write("}")
        f.write(" <= 0;\n")


        f.write("    endcase\n")
        f.write("  end\n")
        f.write("endmodule\n")
        f.close()
        print("Generate LUT Finish!")
        os.chdir(self.workdir)

    def run_compile_dc(self, inputtclfile, outputvpath):
        inputfilename = os.path.split(inputtclfile)[1]
        if('_obf_' in inputfilename):
            strTOPORTOP_OBF = 'top_obf'
        else:
            strTOPORTOP_OBF = 'top'
        with open(self.path_template_run_compile_dc_tcl, 'r') as frcdctcl:
            lines = frcdctcl.readlines()
        
        for i in range(len(lines)):
            if('INPUTTCLPATH' in lines[i]):
                lines[i] = lines[i].replace('INPUTTCLPATH', inputtclfile)

            if('OUTPUTVERILOGPATH' in lines[i]):
                lines[i] = lines[i].replace('OUTPUTVERILOGPATH', outputvpath)

            if('TOPORTOP_OBF' in lines[i]):
                lines[i] = lines[i].replace('TOPORTOP_OBF', strTOPORTOP_OBF)

            
        newScriptFile = os.path.join(self.strIntermediatePath, 'run_compile_dc_'+strTOPORTOP_OBF+'.tcl')
        with open(newScriptFile, 'w') as nfmicsh:
            for line in lines:
                nfmicsh.write(line)
        
        print("Modify tcl file for dc finish.")

        os.chdir(self.strIntermediatePath)
        # shell = 'modify_iters.csh'
        # f = open(shell, 'r')
        # cmd = f.read()
        # status = subprocess.call(cmd, shell=True, executable='/bin/bash')
        strLogFile = os.path.join(self.strIntermediatePath, 'dc_'+strTOPORTOP_OBF+'_log.log')
        strCmd = "dc_shell -f " + newScriptFile + " > " + strLogFile
        status = os.system(strCmd)
        if(0 == status):
            print("Generate %s.v finish." % strTOPORTOP_OBF)
        else:
            print("===ERROR: Cannot generate %s.v!===" % strTOPORTOP_OBF)
        os.chdir(self.workdir)

        status = 0
        ErrInfo = ""
        with open(strLogFile, 'r') as lf:
            lines = lf.readlines()
        for line in lines:
            if('Error' in line):
                status = 1
                ErrInfo = line
                break
        listStatus = []
        listStatus.append(status)
        listStatus.append(ErrInfo)
        return listStatus, strLogFile

    def convert_verilog_to_bench_by_abc(self, inputfilename, outputvpath):
        inputfilename = os.path.split(inputfilename)[1]
        if('_obf_' in inputfilename):
            strTOPORTOP_OBF = 'top_obf'
        else:
            strTOPORTOP_OBF = 'top'

        with open(self.path_template_get_bench_tcl, 'r') as fgbtcl:
            lines = fgbtcl.readlines()
        
        for i in range(len(lines)):
            if('OUTPUTVERILOGPATH' in lines[i]):
                lines[i] = lines[i].replace('OUTPUTVERILOGPATH', outputvpath)
            if('TOPORTOP_OBF' in lines[i]):
                lines[i] = lines[i].replace('TOPORTOP_OBF', strTOPORTOP_OBF)
            if('CODEROOT' in lines[i]):
                lines[i] = lines[i].replace('CODEROOT', self.workdir)

        newScriptFile = os.path.join(self.strIntermediatePath, 'get_' + strTOPORTOP_OBF + '_bench.tcl')
        with open(newScriptFile, 'w') as nfgbtcl:
            for line in lines:
                nfgbtcl.write(line)
        
        print("Modify get_bench.tcl finish.")
        strOriginalVerilogFile = os.path.join(outputvpath, strTOPORTOP_OBF+'.v')
        with open(strOriginalVerilogFile, 'r') as ovf:
            vlines = ovf.readlines()
        for i in range(len(vlines)):
            if('tri  ' in vlines[i]):
                vlines[i] = vlines[i].replace('tri  ', 'wire  ')
        with open(strOriginalVerilogFile, 'w') as ovf:
            for i in range(len(vlines)):
                ovf.write(vlines[i])
        os.chdir(self.strIntermediatePath)
        # shell = 'modify_iters.csh'
        # f = open(shell, 'r')
        # cmd = f.read()
        # status = subprocess.call(cmd, shell=True, executable='/bin/bash')
        strCmd = self.path_abc + " -f " + newScriptFile + ' > ' + os.path.join(self.strIntermediatePath, 'abc_' + strTOPORTOP_OBF + '_log.log')
        status = os.system(strCmd)
        if(0 == status):
            print("Generate %s.bench finish." % strTOPORTOP_OBF)
        else:
            print("===ERROR: Cannot generate %s.bench!===" % strTOPORTOP_OBF)
        strOutputFile = os.path.abspath(os.path.join(outputvpath, strTOPORTOP_OBF+'.bench'))
        os.chdir(self.workdir)

        return strOutputFile
        

    def optimize_bench_file(self, benchfile):
        with open(benchfile, 'r') as bf:
            lines = bf.readlines()
        flagBar = 0
        strReplaceVdd = ""
        with open(benchfile, 'w') as bf:
            for line in lines:
                if(0 == flagBar):
                    if(('INPUT' in line) and ('keyinput' not in line)):
                        strSignalName = line[line.find('(')+len('('):line.find(')')]
                        strSignalBarName = strSignalName+"_bar"
                        strSignalBar = strSignalBarName+" = NOT("+strSignalName+")\n"
                        strReplaceVdd = '= OR('+strSignalName+','+strSignalBarName+')\n'
                        line = line+strSignalBar
                        flagBar = 1
                line = line.replace('[','q')
                line = line.replace(']','p')
                if("" != strReplaceVdd):
                    line = line.replace('= vdd\n',strReplaceVdd)
                bf.write(line)
        return benchfile

    def sat_attack(self, listbench, outputlogpath, SATtimeout):
        bench_obf = listbench[1]
        bench_ori = listbench[0]
        strTime = time.strftime("%Y%m%d%H%M%S", time.localtime())
        strOutputLog = os.path.join(outputlogpath, 'SAT_log_' + strTime + '.log')
        flagTimeout = 0
        listCmd = []
        listCmd.append(self.path_sld)
        listCmd.append(bench_obf)
        listCmd.append(bench_ori)

        if(SATtimeout <= 0): # no limit
            with open(strOutputLog, 'w') as oplf:
                status = subprocess.call(listCmd, stdout=oplf)
        else:
            try:
                # subprocess.call("notepad", timeout=3)

                # shell = 'modify_iters.csh'
                # f = open(shell, 'r')
                # cmd = f.read()
                with open(strOutputLog, 'w') as oplf:
                    status = subprocess.call(listCmd, timeout=SATtimeout, stdout=oplf)
            except subprocess.TimeoutExpired:
                with open(strOutputLog, 'a') as oplf:
                    oplf.write('Timeout')
                flagTimeout = 1
            else:
                flagTimeout = 0

        # strCmd = self.path_sld + ' ' + bench_obf + ' ' + bench_ori + '>' + strOutputLog
        # os.system(strCmd)
        return strOutputLog, flagTimeout

    def read_sat_log_results(self, satlogfile, strBenchName, nIter, nReplacement, strOverhead):
        with open(satlogfile, 'r') as slf:
            lines = slf.readlines()
        strKeybits = ""
        strTime = ""
        for line in lines:
            if("Error. Original (simulation) and encrypted designs don't match." in line):
                self.delete_conflict_sub_ckt = True
                break
            if(('inputs=' in line) and (' keys=' in line) and (' outputs=' in line) and (' gates=' in line)):
                strKeybits = line[line.find(' keys=')+len(' keys='):line.find(' outputs=')]
                continue
            if(('iteration=' in line) and ('; backbones_count=' in line) and ('; cube_count=' in line) and ('; cpu_time=' in line)):
                strTime = line[line.find('; cpu_time=')+len('; cpu_time='):line.find('; maxrss=')]
        if("" != strKeybits):
            self.delete_conflict_sub_ckt = False
        strWrite = strBenchName + '\titer' + str(nIter) + '\treplace#' + str(nReplacement) + '\tkey=' + strKeybits + '\tcpu_time=' + strTime + '\tOverhead ' + strOverhead + '\n'
        print(strWrite)
        with open(self.strRecordFile, 'a') as rrf:
            rrf.write(strWrite)
        
    def check_iter_replacement_parameters_by_iterinfo(self, nIter, nReplacement, strSubcktRoot):
        strConflictFileRoot = os.path.join(strSubcktRoot, 'iter'+str(nIter))
        strConflictFile = os.path.join(strConflictFileRoot, '_iter'+str(nIter)+'_info.txt')
        with open(strConflictFile, 'r') as cf:
            lines = cf.readlines()
        
        del(lines[0])
        del(lines[0])
        listRemove = []
        for line in lines:
            if(5 > line.count('\t')):
                listRemove.append(line)
        
        for lineremove in listRemove:
            lines.remove(lineremove)

        if(nReplacement > len(lines)):
            nReplacement = len(lines)
        return nIter, nReplacement

    def check_iter_replacement_parameters_only_conflict_subckts(self, nIter, nReplacement, strSubcktRoot):
        strConflictFileRoot = os.path.join(strSubcktRoot, 'iter'+str(nIter))
        strConflictFile = os.path.join(strConflictFileRoot, '_conflict_subckt.txt')
        with open(strConflictFile, 'r') as cf:
            line = cf.readline()
        listConflictSubckt = []
        line = line.replace('[', '')
        line = line.replace(']', '')
        listConflictSubckt = line.split(',')

        if(nReplacement > len(listConflictSubckt)):
            nReplacement = len(listConflictSubckt)
        return nIter, nReplacement


    def find_dc_timing_warnings(self, dc_log):
        listTempDeleteSubckt = []
        with open(dc_log, 'r') as dclf:
            while(True):
                strLine = dclf.readline()
                if(not strLine):
                    break
                if('Warning: Disabling timing arc between' in strLine):
                    strCktName = strLine[strLine.find("on cell '")+len("on cell '"):strLine.rfind("/")]
                    if('sub_ckt' in strCktName):
                        strCktName = strCktName[strCktName.find('sub_ckt'):]
                        # if(strCktName not in self.listDeleteSubckt):
                        #     self.listDeleteSubckt.append(strCktName)
                        if(strCktName not in listTempDeleteSubckt):
                            listTempDeleteSubckt.append(strCktName)
        
        return listTempDeleteSubckt



    def prepare_folders(self, strIterNum, intReplacement):
        strIntermediatePath = os.path.split(self.strRecordFile)[0]
        # strIntermediatePath = os.path.join(self.strScriptsRoot, 'intermediate_files')
        strIntermediatePath = os.path.join(strIntermediatePath, 'iter'+strIterNum)
        self.strIntermediatePath_iter = strIntermediatePath
        strIntermediatePath = os.path.join(strIntermediatePath, 'replace_'+str(intReplacement))
        self.strIntermediatePath = strIntermediatePath
        
        if(False ==  os.path.exists(strIntermediatePath)):
            os.makedirs(strIntermediatePath)
        return strIntermediatePath
    
    def get_area_from_dc_log_file(self, dclogfile):
        strArea = ""
        with open(dclogfile, 'r') as lf:
            lines = lf.readlines()
        
        flagArea = 0
        flagBegin = 0
        flagCount = 0
        for line in lines:
            if('Beginning Area-Recovery Phase  (cleanup)' in line):
                flagArea = 1
                continue

            if("Loading db file '/home/UFAD/guor/Public/library/slow_vdd1v0_basicCells_mod.db'" in line):
                flagBegin = 0
                flagArea = 0
                flagCount = flagCount + 1
                if(2 == flagCount):
                    break

            if(1 == flagArea):
                if('--------- --------- --------- --------- --------- -------------------------' in line):
                    flagBegin = 1
                    continue

            if((1 == flagArea) and (1 == flagBegin)):
                strTemp = line 
                strTemp = strTemp.strip('\n')
                strTemp = strTemp.strip()
                strTemp = strTemp[strTemp.find(' '):]# Time
                strTemp = strTemp.strip()
                strTemp = strTemp[:strTemp.find(' ')]# Area
                strArea = strTemp


        return strArea
        
        
def run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, SATtimeout=0, nTotalCircuitNum=-1, listFinish=[], strDefaultArea="DefaultArea"):
    nOldReplacement = nReplacement
    nReplaceRegularSubckt = 0
    nTimeout = -1
    nLastReplacement = 0
    listLastReplace = []
    while(1): 
        print("=========Iter%d, Replace%d=========" % (nIter, nReplacement))
        print(uef.strRecordFile)
        nIter, nReplacementConflictSubckts = uef.check_iter_replacement_parameters_only_conflict_subckts(nIter, nReplacement, strItersRoot)
        if(-1 == nTotalCircuitNum):
            nReplaceRegularSubckt = nOldReplacement - nReplacementConflictSubckts
        elif(nOldReplacement < nTotalCircuitNum):
            nReplaceRegularSubckt = nOldReplacement - nReplacementConflictSubckts
        else:
            nReplaceRegularSubckt = nTotalCircuitNum - nReplacementConflictSubckts
        nActuralReplaceSubckt = nReplaceRegularSubckt + nReplacementConflictSubckts

        strFinish = "iter"+str(nIter)+'\tActReplace:'+str(nActuralReplaceSubckt)+'\tConflictReplace:'+str(nReplacementConflictSubckts)+'\tRegularReplace:'+str(nReplaceRegularSubckt)
        if(strFinish in listFinish):
            print('Iter:'+str(nIter)+' Replacement:'+str(nActuralReplaceSubckt)+' Already run!')
            return nTimeout, nReplacement, listFinish
        else:
            listFinish.append(strFinish)

        nReplacement = nActuralReplaceSubckt
        listBenchFile = []
        strTempPath = uef.prepare_folders(str(nIter), nReplacement)
        uef.modify_iters_csh(str(nIter), nReplacement)
        inputtclfile = os.path.join(strTempPath, 'read_'+str(nIter)+'.tcl')
        outputvpath = strTempPath
        listStatus, strDC_top_log = uef.run_compile_dc(inputtclfile, outputvpath)
        if(1 == listStatus[0]):
            print(listStatus[1])
            return nTimeout, nReplacement, listFinish
        benchfile = uef.convert_verilog_to_bench_by_abc(inputtclfile, outputvpath) # original
        benchfile = uef.optimize_bench_file(benchfile)
        listBenchFile.append(benchfile)


        inputtclfile = os.path.join(strTempPath, 'read_obf_'+str(nIter)+'.tcl')
                
        flagbreak = 0
        dictTemp = {}
        while(1):
            strKey, listReplaceConflictSubckt, listRegularSubcktRedact = uef.modify_top_plx_by_conflict_order(str(nIter), nReplacement, uef.listDeleteSubckt, nReplaceRegularSubckt)
            listReplace = listReplaceConflictSubckt+listRegularSubcktRedact
            dictTemp[strKey] = listReplace
            if((nReplacement == nLastReplacement) and (listReplace == listLastReplace)):
                print("=====Cannot replace anymore!=====")
                return nTimeout, nReplacement, listFinish
            else:
                nLastReplacement = nReplacement
                listLastReplace = copy.deepcopy(listReplace)
            listStatus, strDC_top_obf_log = uef.run_compile_dc(inputtclfile, outputvpath)
            listTempDeleteSubckt = uef.find_dc_timing_warnings(strDC_top_obf_log)
            if(0 == len(listTempDeleteSubckt)):      
                dictTemp[strKey].append("Good")
                if(nReplacement == nActuralReplaceSubckt):
                    flagbreak = 1
                    break
            else:
                needkickonesubckt = 1
                dictTemp[strKey].append("Error")
                for deleteitem in listTempDeleteSubckt:
                    if(deleteitem in listReplace):
                        needkickonesubckt = 0
                        uef.listDeleteSubckt.append(deleteitem)
            if(1 == needkickonesubckt):
                nMaxGood = 0
                nMinError = nActuralReplaceSubckt+1
                strMaxGoodKey = ""
                strMinErrorKey = "iter"+str(nIter)+"_replace"+str(nActuralReplaceSubckt+1)
                for key in dictTemp.keys():
                    if('Good' == dictTemp[key][-1]):
                        nLength = int(key[key.find('replace')+len('replace'):])
                        if(nLength > nMaxGood):
                            nMaxGood = nLength
                            strMaxGoodKey = key
                    elif("Error" == dictTemp[key][-1]):
                        nLength = int(key[key.find('replace')+len('replace'):])
                        if(nLength < nMinError):
                            nMinError = nLength
                            strMinErrorKey = key
                if(0 != len(listTempDeleteSubckt)):
                    if("" == strMaxGoodKey):
                        nReplacement = math.ceil(nReplacement/2)
                        continue
                    else:
                        nReplacement = math.ceil((nMinError+nMaxGood)/2)
                    if(nReplacement == nMinError):
                        uef.listDeleteSubckt.append(dictTemp[strMinErrorKey][-2])
                        nReplacement = nActuralReplaceSubckt
                else:
                    nReplacement = math.ceil((nMinError+nMaxGood)/2)
                    if(nReplacement == nMinError):
                        uef.listDeleteSubckt.append(dictTemp[strMinErrorKey][-2])
                    
        if(1 == listStatus[0]):
            print(listStatus[1])
            return nTimeout, nReplacement, listFinish
        benchfile = uef.convert_verilog_to_bench_by_abc(inputtclfile, outputvpath) # obf
        benchfile = uef.optimize_bench_file(benchfile)
        listBenchFile.append(benchfile)

        SAToutputlog, nTimeout = uef.sat_attack(listBenchFile, strTempPath, SATtimeout)
        strBenchName = os.path.split(strDataRoot)[1]
        strArea = uef.get_area_from_dc_log_file(strDC_top_obf_log)
        strOverhead = '=(' + strArea + '-' + strDefaultArea + ')/' + strDefaultArea
        uef.read_sat_log_results(SAToutputlog, strBenchName, nIter, nReplacement, strOverhead)
        if(False == uef.delete_conflict_sub_ckt):
            uef.dictConflictSubCktRecord[strKey].append('Good')
            if(nReplacement == nActuralReplaceSubckt):
                break
            else:
                uef.listCorrectSubckt = copy.deepcopy(uef.dictConflictSubCktRecord[strKey])
                uef.listCorrectSubckt.remove('Good')
                nTemp = -1
                nMinErrReplace = nOldReplacement
                nMaxGoodReplace = 0
                for key in uef.dictConflictSubCktRecord.keys():
                    nTemp = key[key.find('_'):]
                    nTemp = int(nTemp.replace('_replace',''))
                    if(uef.dictConflictSubCktRecord[key][-1] == 'MatchError'):
                        if(nTemp < nMinErrReplace):
                            nMinErrReplace = nTemp
                    elif(uef.dictConflictSubCktRecord[key][-1] == 'Good'):
                        if(nTemp > nMaxGoodReplace):
                            nMaxGoodReplace = nTemp
                if(uef.kickone == 0):
                    nReplacement = math.ceil((nMinErrReplace+nMaxGoodReplace)/2)
                else:
                    nReplacement = nMinErrReplace
                    uef.kickone = 0
        else:
            uef.dictConflictSubCktRecord[strKey].append('MatchError')
            strTemp = ""
            nMaxLength = -1
            for key in uef.dictConflictSubCktRecord.keys():
                if('Good' == uef.dictConflictSubCktRecord[key][-1]):
                    if((len(uef.dictConflictSubCktRecord[key])-1) > nMaxLength):
                        strTemp = key
                        nMaxLength = len(uef.dictConflictSubCktRecord[key])-1
            
            if("" != strTemp):
                if((len(uef.dictConflictSubCktRecord[strTemp])-1) + 1 < (len(uef.dictConflictSubCktRecord[strKey])-1)):
                    nReplacement = nMaxLength + math.ceil((len(uef.dictConflictSubCktRecord[strKey])-len(uef.dictConflictSubCktRecord[strTemp]))/2)
                else:
                    uef.listDeleteSubckt.append(uef.dictConflictSubCktRecord[strKey][-2])
            else:
                if('iter'+str(nIter)+'_replace1' in uef.dictConflictSubCktRecord.keys()):
                    uef.listDeleteSubckt.append(uef.dictConflictSubCktRecord['iter'+str(nIter)+'_replace1'][-2])
                nReplacement = 1

    return nTimeout, nReplacement, listFinish
    
def get_total_circuit_in_iter(iterfolder, nIter):
    strIter = str(nIter)
    strCircuitInfoFile = os.path.join(iterfolder, '_iter'+strIter+'_info.txt')
    strConflictSubcircuitFile = os.path.join(iterfolder, '_conflict_subckt.txt')
    nTotalCircuitNum = -1
    nConflictCircuitNum = -1
    if(False != os.path.exists(strCircuitInfoFile)):
        with open(strCircuitInfoFile, 'r') as cif:
            line = cif.readline()
        line = line.strip('\n')
        nTotalCircuitNum = int(line[line.find(', Sub ckt: ')+len(', Sub ckt: '):]) # Iteration: 8, Sub ckt: 17


    if(False != os.path.exists(strConflictSubcircuitFile)):
        listConflictSubckt = []
        with open(strConflictSubcircuitFile, 'r') as cscf:
            line = cscf.readline()
        line = line.strip('\n')
        line = line.replace('[','')
        line = line.replace(']','')
        listConflictSubckt = line.split(',')
        nConflictCircuitNum = len(listConflictSubckt) # [sub_ckt_0]
    
    return nTotalCircuitNum, nConflictCircuitNum

if __name__ == '__main__':
    strDataRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/sin_20220927111930_ms0_af_7492'
    strtime = time.strftime("%Y%m%d%H%M%S", time.localtime())
    

    nRunMode = 1 #0, 1, 2
    nIter = 0
    nMaxReplacement = 100
    nMinReplacement = 1
    nReplacement = 100
    strDefaultArea = "1"

    # arbiter: 5758.6
    # sin: 6465.5
    # square: 25439
    # log2: 42220
    # multiplier: 34586
    # div: 78787.9

    

    parser = argparse.ArgumentParser(description='Universal Function Module')
    parser.add_argument("-d", action="store", required=False, type=str, help="cpt data")
    parser.add_argument("-m", action="store", required=False, type=str, help="run mode")
    parser.add_argument("-i", action="store", required=False, type=str, help="iter number")
    parser.add_argument("-r", action="store", required=False, type=str, help="replace number")
    parser.add_argument("-o", action="store", required=False, type=str, help="output dir")
    parser.add_argument("-a", action="store", required=False, type=str, help="default area")
    args = parser.parse_args()
    if(None != args.d):
        strDataRoot = args.d
    if(None != args.m):
        nRunMode = int(args.m)
    if(None != args.i):
        nIter = int(args.i)
    if(None != args.r):
        nReplacement = int(args.r)
    if(None != args.o):
        strOutputDir = args.o
    else:
        strOutputDir = os.path.split(strDataRoot)[0]
    if(None != args.a):
        strDefaultArea = args.a
    
    strBenchName = os.path.split(strDataRoot)[1]
    strBenchName = strBenchName[:strBenchName.find('_')]

    strRTL_LUTRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/rtl'
    
    strRecordFile = os.path.join(strOutputDir,'intermediate_files_'+strBenchName+'_'+strtime)
    strRecordFile = os.path.join(strRecordFile, 'record_'+strtime+'.txt')
    # strRecordFile = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_'+strBenchName+'_'+strtime+'/record_'+strtime+'.txt'
    print(strRecordFile)
    strDataRoot = os.path.abspath(os.path.expanduser(strDataRoot))
    strItersRoot = os.path.join(strDataRoot, 'sub_circuit')
    file_name_list = os.listdir(strItersRoot)
    nTimeoutLimit = 86400 # s, 24hr

    listReplacement = [5,10,15,20,25,30]
    # listReplacement = [20,30]

    uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)

    # ===================================TEST=====================================
    # dclogfile = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_sin_20220927201525/iter0/replace_25/dc_top_obf_log.log'
    # strArea = uef.get_area_from_dc_log_file(dclogfile)
    # strOverhead = '=(' + strArea + '-' + strDefaultArea + ')/' + strDefaultArea
    # uef.modify_top_plx_by_conflict_order('3', 5, listDeleteSubckt = [], nReplaceRegularSubckt = 0)
    # strDC_top_obf_log = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_sin_20220927201525/intermediate_files_sin_20221005164310/iter3/replace_5/dc_top_obf_log.log'
    # strArea = uef.get_area_from_dc_log_file(strDC_top_obf_log)
    # strOverhead = '=(' + strArea + '-' + strDefaultArea + ')/' + strDefaultArea
    # ===================================TEST=====================================


    nTotalCircuitNum = -1
    nConflictCircuitNum = -1
    strIterFolder = os.path.join(strItersRoot, 'iter'+str(nIter))
    nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(strIterFolder, nIter)
    listFinish = []
    #==============================run one time======================
    if(0 == nRunMode):
        # nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(os.path.join(strItersRoot, iter+str(nIter)), nIter)
        nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea)
    #==============================run one time======================
    
    # #==============================run cycles======================
    elif(1 == nRunMode):      
        if(None == args.i):
            for nIter in range(len(file_name_list)):
                print("Iter"+str(nIter)+":"+str(nTotalCircuitNum)+" subckts, "+str(nConflictCircuitNum)+"")
                for nReplacement in listReplacement:
                    nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea)

        else:
            for nReplacement in listReplacement:
                nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea)

    #==============================find closer to 24hrs======================
    elif(2 == nRunMode):
        dictFinish = {}
        listFinish = []
        nReplacement = nMaxReplacement
        while(1):
            listFinish = []
            for nAlreadyFinishReplace in dictFinish.keys():
                listFinish.append(nAlreadyFinishReplace)
            if(0 != len(listFinish)):
                if(nMaxReplacement in dictFinish.keys()):
                    if(0 == dictFinish[nMaxReplacement]):
                        nReplacement = nMaxReplacement
                    else:
                        nReplacement = math.ceil((nMaxReplacement + nMinReplacement)/2)
                else:
                    nReplacement = nMaxReplacement


            if(nReplacement in listFinish):
                print("replace_%d is closest to 24 hrs." % nMinReplacement)
                break
            # nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(os.path.join(strItersRoot, iter+str(nIter)), nIter)
            nSATtimeoutStatus, nReplacement = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea)
            dictFinish[nReplacement] = nSATtimeoutStatus
            if(1 == nSATtimeoutStatus):
                nMaxReplacement = nReplacement
            else:
                nMinReplacement = nReplacement
                if(nMinReplacement == nMaxReplacement):
                    nMaxReplacement = 2*nMaxReplacement


