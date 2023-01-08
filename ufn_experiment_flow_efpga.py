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
import shutil
import re
import sys

import Ntk_Parser
from Ntk_Struct import *
class ufm_experiment_flow:
    def __init__(self, strDataRoot, strRecordFile, strRTL_LUTRoot):
        self.strRTL_LUTRoot = strRTL_LUTRoot
        self.listLUTFiles = self.get_exist_lut_files(self.strRTL_LUTRoot)
        self.strRecordFile = strRecordFile
        self.strInvalidConflictSubcktFile = os.path.join(os.path.split(self.strRecordFile)[0], 'InvalidConflictSubckt.txt')
        self.workdir = os.getcwd()
        self.path_abc = os.path.abspath('/home/UFAD/guor/Codes_old/Python/MyDemo/UFM/abc-master-Sazadur/abc')
        self.yosys_abc_path = ''
        r = os.popen('which yosys-abc')
        text_yosys_abc = r.read()
        text_yosys_abc = text_yosys_abc.replace('\n','')
        r.close()
        r = os.popen('which yosys')
        text_yosys = r.read()
        text_yosys = text_yosys.replace('\n','')
        r.close()
        if("which: no " in text_yosys_abc):
            self.yosys_abc_path = '/usr/local/bin/yosys-abc'
            self.yosys_path = '/usr/local/bin/yosys'
        else:
            self.yosys_abc_path = text_yosys_abc
            self.yosys_path = text_yosys
        
        if(True != os.path.exists(self.yosys_abc_path)):
            print('yosys-abc is not exist! Please install yosys first!')
        self.path_sld = os.path.abspath('/home/UFAD/guor/Codes_old/Python/MyDemo/UFM/FromSazadur/Rui/spramod-host15-logic-encryption-7fdc93c47b0e/bin/sld')
        self.path_template_modify_iters_csh = os.path.join(self.workdir, 'modify_iters.csh')
        self.path_template_modify_top_plx = os.path.join(self.workdir, 'modify_top.plx')
        self.path_template_run_compile_dc_tcl = os.path.join(self.workdir, 'run_compile_dc.tcl')
        self.path_template_get_bench_tcl = os.path.join(self.workdir, 'get_bench.tcl')
        self.path_template_run_compile_dc_lut_converter_tcl = os.path.join(self.workdir, 'run_compile_dc_lut_converter.tcl')
        self.strDataRoot = strDataRoot
        self.strScriptsRoot = os.path.split(self.strDataRoot)[0]
        self.strDataRootName = os.path.split(self.strDataRoot)[1]
        self.strIntermediatePath = ""
        self.strIntermediatePath_iter = ""
        self.listGeneratedLut = []
        self.delete_conflict_sub_ckt = False
        self.dictConflictSubCktRecord = {}
        self.dictSubCktRecordTotal = {}
        self.listDeleteSubckt = []
        self.listCorrectSubckt = []
        self.nLenDeleteSubcktLastTime = 0
        self.kickone = 0
        self.last_conflict_num = 0
        self.last_regular_num = 0
        self.circuit_graph = {}
        self.strBench_LUTRoot = ''
        self.in_port_prefix = 'i_cg_'
        self.out_port_prefix = 'o_cg_'
    
    def get_exist_lut_files(self, strRTL_LUTRoot):
        listLUTFiles = os.listdir(strRTL_LUTRoot)
        return listLUTFiles


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
        strOrder = strOrder.strip('\n')
        listOriginalOrder = strOrder.split(',')
        while('' in listOriginalOrder):
            listOriginalOrder.remove('')
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
        # self.dictSubCktRecordTotal[strKey] = []
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
                        temp = item
                        while(1 < temp.count('\t')):
                            temp = temp[temp.find('\t')+len('\t'):]
                        temp = temp.strip('\n')
                        strInput = temp[:temp.find('\t')]
                        strOutput = temp[temp.find('\t')+len('\t'):]
                        if(strInput != '0' and strOutput != '0'):
                            listReplaceOrder.append(item)
                            break
                        else:
                            if(strTemp1 not in self.listDeleteSubckt):
                                self.listDeleteSubckt.append(strTemp1)
                    else:
                        if(strTemp1 not in self.listDeleteSubckt):
                            self.listDeleteSubckt.append(strTemp1)
            if(intReplacement <= len(listReplaceOrder)):
                break

        with open(self.path_template_modify_top_plx, 'r') as fmtplx:
            lines = fmtplx.readlines()
        
        listTemp = []
        strRedact = "  "
        nTotalGates = 0
        strRedactSubcktInfo = ""
        for i in range(intReplacement):
            if(i >= len(listReplaceOrder)):
                break
            temp = listReplaceOrder[i]
            if(5 > temp.count('\t')):# no io info
                continue
            else:
                strRedact = strRedact + temp[:temp.find('\t')]
                self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                nTimes = 0
                while(1 < temp.count('\t')):
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + ', '
                    temp = temp[temp.find('\t')+len('\t'):]
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + '\n'
                        nTotalGates = nTotalGates + int(temp[:temp.find('\t')])
                    nTimes = nTimes + 1
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
        listRegularSubcktRedactInfo = []
        nSubcktinfoLens = len(subcktinfo)-1
        nCount = 0
        for i in range(nSubcktinfoLens, -1, -1):
            if(len(listRegularSubcktRedact) >= nReplaceRegularSubckt):
                break
            elif(subcktinfo[i] in listReplaceOrder):
                continue
            else:
                temp = subcktinfo[i]
                if(5 > temp.count('\t')):
                    continue
                strTemp = temp
                strTemp1 = strTemp[:strTemp.find('\t')]
                if(strTemp1 in self.listDeleteSubckt):
                    continue
                while(1 < strTemp.count('\t')):
                    strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                strTemp = strTemp.strip('\n')
                strInput = strTemp[:strTemp.find('\t')]
                strOutput = strTemp[strTemp.find('\t')+len('\t'):]
                if(strInput == '0' or strOutput == '0'):
                    if(strTemp1 not in self.listDeleteSubckt):
                        self.listDeleteSubckt.append(strTemp1)
                        continue

                listRegularSubcktRedactInfo.append(temp)
                listRegularSubcktRedact.append(temp[:temp.find('\t')])
                # self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                strRedact = strRedact + temp[:temp.find('\t')]
                nTimes = 0
                while(1 < temp.count('\t')):
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + ', '
                    temp = temp[temp.find('\t')+len('\t'):]
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + '\n'
                        nTotalGates = nTotalGates + int(temp[:temp.find('\t')])
                    nTimes = nTimes + 1
                temp = temp.replace('\n','')
                temp = temp.replace('\t',' ')
                strLutFileName = 'lut_' + temp + '.v'
                strLutFileName = strLutFileName.replace(' ','_')
                if(strLutFileName not in self.listLUTFiles):
                    self.listLUTFiles.append(strLutFileName)
                    listTemp.append(temp)
                strRedact = strRedact + "  => '" + temp + "'"
                strRedact = strRedact + ',\n  '
                nCount = nCount + 1


        listSubcktRedactTotal = listReplaceOrder + listRegularSubcktRedactInfo
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

        redactSubcktInfoFile = os.path.join(self.strIntermediatePath, 'RedactSubcktsInfo.txt')
        strRedactSubcktInfo = strRedactSubcktInfo + str(nTotalGates) + '\n'
        with open(redactSubcktInfoFile, 'w') as rsif:
                rsif.write(strRedactSubcktInfo)
        
        
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
        
        ori_read_obf_file = os.path.join(self.strIntermediatePath, 'read_obf_'+strIterNum+'.tcl')
        os.rename(ori_read_obf_file, os.path.join(self.strIntermediatePath, 'read_obf_'+strIterNum+'_by_plx.tcl'))
        originaltcl = os.path.join(self.strIntermediatePath, 'read_'+strIterNum+'.tcl')
        self.rewrite_read_obf_tcl(self.strIntermediatePath, originaltcl, listSubcktRedactTotal, strIterNum, self.strRTL_LUTRoot)

        os.chdir(self.workdir)
        print(strKey + ': Conflict subckts: ' + str(len(self.dictConflictSubCktRecord[strKey])) + str(self.dictConflictSubCktRecord[strKey]))
        print(strKey + ': Regular subckts: ' + str(len(listRegularSubcktRedact)) + str(listRegularSubcktRedact))
        
        strConflictSubcktRecord = os.path.join(self.strIntermediatePath, 'conflict_subckt_iter'+strIterNum+'_replace'+str(intReplacement)+'.txt')
        with open(strConflictSubcktRecord, 'w') as cscrf:
            cscrf.write(str(self.dictConflictSubCktRecord[strKey]))
            cscrf.write(str(listRegularSubcktRedact))
        
        
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
        
        # self.dictSubCktRecordTotal[strKey] = self.dictConflictSubCktRecord[strKey] + listRegularSubcktRedact

        return strKey, self.dictConflictSubCktRecord[strKey], listRegularSubcktRedact, nTotalGates

    def rewrite_read_obf_tcl(self, folder, originaltcl, listRedact, strIterNum, LUTFolder):
        filename = os.path.join(folder, 'read_obf_'+strIterNum+'.tcl')
        with open(originaltcl, 'r') as otclf:
            lines = otclf.readlines()
        
        for i in range(len(lines)):
            if('/sub_circuit/iter'+strIterNum+'/top.v' in lines[i]):
                strTemp = os.path.join(folder, 'plx_top_obf.v') + '\n'
                lines[i] = strTemp
                continue
            for j in listRedact:
                strTemp = j[:j.find('\t')]#/sub_ckt_4/sub_ckt_4_
                strTemp = '/'+strTemp+'/'+strTemp+'_'
                if(strTemp in lines[i]):
                    strTemp = j
                    while(1 < strTemp.count('\t')):
                        strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                    strTemp = strTemp.strip('\n')
                    strTemp = strTemp.replace('\t','_')
                    strTemp = os.path.join(LUTFolder, 'lut_'+strTemp+'.v')
                    lines[i] = strTemp+'\n'
                    break
        with open(filename, 'w') as tclf:
            for line in lines:
                tclf.write(line)
        
        print('Generate new "read_obf_" file finish!')
        return filename



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
            with open(strLogFile, 'r') as dclf:
                while(True):
                    strLine = dclf.readline()
                    if(not strLine):
                        break
                    if('Error:' in strLine):
                        status = 1
                        ErrInfo = strLine
                        break
            if(0 == status):
                print("Generate %s.v finish." % strTOPORTOP_OBF)
            else:
                print("===ERROR: Cannot generate %s.v!===" % strTOPORTOP_OBF)
        else:
            print("===ERROR: Cannot generate %s.v!===" % strTOPORTOP_OBF)
        os.chdir(self.workdir)

        ErrInfo = ""
        # status = 0
        # with open(strLogFile, 'r') as lf:
        #     lines = lf.readlines()
        # for line in lines:
        #     if('Error' in line):
        #         status = 1
        #         ErrInfo = line
        #         break
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

    def read_sat_log_results(self, satlogfile, strBenchName, nIter, nReplacement, strOverhead, nTotalGates):
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
        strWrite = strBenchName + '\titer' + str(nIter) + '\treplace#' + str(nReplacement) + '\tGates=' + str(nTotalGates) + '\tkey=' + strKeybits + '\tcpu_time=' + strTime + '\tOverhead ' + strOverhead + '\n'
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
        line = line.strip('\n')
        listConflictSubckt = line.split(',')

        while('' in listConflictSubckt):
            listConflictSubckt.remove('')
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


    def get_redacted_subckts_list(self, strIterNum, intReplacement, listDeleteSubckt = [], nReplaceRegularSubckt = 0):
        strIterOrderFile = os.path.join(self.strDataRoot, 'sub_circuit')
        strIterOrderFile = os.path.join(strIterOrderFile, 'iter'+strIterNum)
        strIterOrderFile = os.path.join(strIterOrderFile, '_conflict_subckt.txt')


        with open(strIterOrderFile, 'r') as iof:
            strOrder = iof.readline()
        strOrder = strOrder.replace('[','')
        strOrder = strOrder.replace(']','')
        strOrder = strOrder.strip('\n')
        listOriginalOrder = strOrder.split(',')
        while('' in listOriginalOrder):
            listOriginalOrder.remove('')
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
        # self.dictSubCktRecordTotal[strKey] = []
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
                        temp = item
                        while(1 < temp.count('\t')):
                            temp = temp[temp.find('\t')+len('\t'):]
                        temp = temp.strip('\n')
                        strInput = temp[:temp.find('\t')]
                        strOutput = temp[temp.find('\t')+len('\t'):]
                        if(strInput != '0' and strOutput != '0'):
                            listReplaceOrder.append(item)
                            break
                        else:
                            if(strTemp1 not in self.listDeleteSubckt):
                                self.listDeleteSubckt.append(strTemp1)
                    else:
                        if(strTemp1 not in self.listDeleteSubckt):
                            self.listDeleteSubckt.append(strTemp1)
            if(intReplacement <= len(listReplaceOrder)):
                break

        with open(self.path_template_modify_top_plx, 'r') as fmtplx:
            lines = fmtplx.readlines()
        
        listTemp = []
        strRedact = "  "
        nTotalGates = 0
        strRedactSubcktInfo = ""
        for i in range(intReplacement):
            if(i >= len(listReplaceOrder)):
                break
            temp = listReplaceOrder[i]
            if(5 > temp.count('\t')):# no io info
                continue
            else:
                strRedact = strRedact + temp[:temp.find('\t')]
                self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                nTimes = 0
                while(1 < temp.count('\t')):
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + ', '
                    temp = temp[temp.find('\t')+len('\t'):]
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + '\n'
                        nTotalGates = nTotalGates + int(temp[:temp.find('\t')])
                    nTimes = nTimes + 1
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
        listRegularSubcktRedactInfo = []
        nSubcktinfoLens = len(subcktinfo)-1
        nCount = 0
        for i in range(nSubcktinfoLens, -1, -1):
            if(len(listRegularSubcktRedact) >= nReplaceRegularSubckt):
                break
            elif(subcktinfo[i] in listReplaceOrder):
                continue
            else:
                temp = subcktinfo[i]
                if(5 > temp.count('\t')):
                    continue
                strTemp = temp
                strTemp1 = strTemp[:strTemp.find('\t')]
                if(strTemp1 in self.listDeleteSubckt):
                    continue
                while(1 < strTemp.count('\t')):
                    strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                strTemp = strTemp.strip('\n')
                strInput = strTemp[:strTemp.find('\t')]
                strOutput = strTemp[strTemp.find('\t')+len('\t'):]
                if(strInput == '0' or strOutput == '0'):
                    if(strTemp1 not in self.listDeleteSubckt):
                        self.listDeleteSubckt.append(strTemp1)
                        continue

                listRegularSubcktRedactInfo.append(temp)
                listRegularSubcktRedact.append(temp[:temp.find('\t')])
                # self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                strRedact = strRedact + temp[:temp.find('\t')]
                nTimes = 0
                while(1 < temp.count('\t')):
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + ', '
                    temp = temp[temp.find('\t')+len('\t'):]
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + '\n'
                        nTotalGates = nTotalGates + int(temp[:temp.find('\t')])
                    nTimes = nTimes + 1
                temp = temp.replace('\n','')
                temp = temp.replace('\t',' ')
                strLutFileName = 'lut_' + temp + '.v'
                strLutFileName = strLutFileName.replace(' ','_')
                if(strLutFileName not in self.listLUTFiles):
                    self.listLUTFiles.append(strLutFileName)
                    listTemp.append(temp)
                strRedact = strRedact + "  => '" + temp + "'"
                strRedact = strRedact + ',\n  '
                nCount = nCount + 1


        listSubcktRedactTotal = listReplaceOrder + listRegularSubcktRedactInfo
        return listSubcktRedactTotal

    def resort_input_and_output_ports_in_bench(self, bench_file):
        with open(bench_file, 'r') as bf:
            lines = bf.readlines()

        listInput = []
        listOutput = []

        for i in range(len(lines)):
            if('INPUT(' in lines[i]):
                strName = lines[i][lines[i].find('INPUT(')+len('INPUT('):lines[i].find(')')]
                listInput.append(strName)
                continue
            if('OUTPUT(' in lines[i]):
                strName = lines[i][lines[i].find('OUTPUT(')+len('OUTPUT('):lines[i].find(')')]
                listOutput.append(strName)
                continue
        listInput = sorted(listInput)
        listOutput = sorted(listOutput)
        bContainPorts = True
        while(True == bContainPorts):
            bContainPorts = False
            for line in lines:
                if(('INPUT(' in line) or ('OUTPUT(' in line)):
                    bContainPorts = True
                    lines.remove(line)
                    break


        for i in listOutput:
            strTemp = 'OUTPUT('+i+')\n'
            lines.insert(0,strTemp)
        for i in listInput:
            strTemp = 'INPUT('+i+')\n'
            lines.insert(0,strTemp)
        

        with open(bench_file, 'w') as bf:
            for line in lines:
                line = line.strip('\n')
                bf.write(line+'\n')
        
        return bench_file

    def bench_to_v(self, bench_file, v_file):
        bench_file = os.path.abspath(bench_file)
        v_file = os.path.abspath(v_file)
        workdir = os.path.split(bench_file)[0]
        log_filename = 'yosys-abc-out.log'
        proc = None
        sys.stdout.flush()
        cmd = []
        cmd_output = []
        strScript = 'read ' + bench_file + ';write_verilog ' + v_file
        # strScript = '"' + strScript + '"'
        cmd.append(self.yosys_abc_path)
        cmd.append('-c')
        cmd.append(strScript)
        try:
            proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,  # We grab stdout
                    stderr=subprocess.STDOUT,  # stderr redirected to stderr
                    universal_newlines=True,  # Lines always end in \n
                    cwd=str(workdir),  # Where to run the command
                )
            log_filename = workdir + '/' + log_filename
            with open(log_filename, "a") as log_f:
                    # Print the command at the top of the log
                    log_f.write(" ".join(cmd))
                    log_f.write("\n")
                    # Read from subprocess output
                    for line in proc.stdout:
                        # Send to log file
                        log_f.write(line)
                        # Save the output
                        cmd_output.append(line)
                    # Should now be finished (since we stopped reading from proc.stdout),
                    # sets the return code
                    proc.wait()
        finally:
            # Clean-up if we did not exit cleanly
            if proc:
                if proc.returncode is None:
                    # Still running, stop it
                    proc.terminate()

    def replace_square_brackets(self, desfile):
        with open(desfile, 'r') as f:
            listContent = f.readlines()
        
        for i in range(len(listContent)):
            if('//' == listContent[i][0:2]):
                continue
            else:
                listContent[i] = listContent[i].replace('[', 'q')
                listContent[i] = listContent[i].replace(']', 'p')
        
        with open(desfile, 'w') as f:
            for line in listContent:
                f.write(line)

        return desfile

    def replace_slash_and_back_slash(self, v_file, str_back_slash, str_slash):
        with open(v_file, 'r') as vf:
            listContent = vf.readlines()

        for i in range(len(listContent)):
            if('//' == listContent[i][0:2]):
                continue
            else:
                listContent[i] = listContent[i].replace('\\', str_back_slash)
                listContent[i] = listContent[i].replace('/', str_slash)
        
        with open(v_file, 'w') as vf:
            for line in listContent:
                vf.write(line)

        return v_file

    def verilog_minmodule_name_optimizer(self, v_file):
        with open(v_file,'r') as vf:
            parsed_f = (vf.read()).split(";")
        for i in range(len(parsed_f)):
            #######################################
            # match module names
            #######################################
            if(re.search(r"([\n\s(\\n)]*)module\s+.+\(", parsed_f[i])):
                strModule = re.findall(r'[\n\s]*module\s+.+\(', parsed_f[i])
                for j in range(len(strModule)):
                    old_name = ""
                    old_name = strModule[j][strModule[j].find('module')+len('module'):strModule[j].find('(')]
                    old_name = old_name.replace(' ','')
                    new_name = os.path.split(old_name)[1]
                    parsed_f[i] = parsed_f[i].replace(old_name, new_name)
                break
        output_file = os.path.join(os.path.split(v_file)[0], os.path.splitext(os.path.split(v_file)[1])[0]+'_minname.v')
        with open(output_file, 'w') as of:
            for line in parsed_f:
                if('endmodule' in line):
                    of.write(line)
                else:
                    of.write(line+';')
        return output_file

    def _eliminate_basic_syntax_errors_for_verilog(self, v_file):
        with open(v_file,'r') as vf:
            lines = vf.readlines()
        with open(v_file, 'w') as vf:
            for line in lines:
                if(re.search(r"\,[\s]*[\)\;]+", line)):
                    strErr = re.findall(r'\,[\s]*[\)\;]+', line)
                    for j in strErr:
                        strTemp = j.replace(',','')
                        line = line.replace(j,strTemp)
                
                vf.write(line)
        return v_file

    def _rename_signals_in_bench(self, bench_file): # rename signals with 'qnp' to '[n]'
        bench_file = self.resort_input_and_output_ports_in_bench(bench_file)
        
        lines = []
        with open(bench_file, 'r') as bf:
            for line in bf:
                listtemp = []
                strtemp = ''
                line = line.strip('\n')
                listtemp = re.findall(r'q+\d+p+',line)
                if(0 != len(listtemp)):
                    for substr in listtemp:
                        strtemp = substr
                        strtemp = strtemp.replace('q','[')
                        strtemp = strtemp.replace('p',']')
                        line = line.replace(substr,strtemp)
                lines.append(line)

        bf = open(bench_file, 'w').close() # delete all the content

        # listInput = []
        # listOutput = []
        # for i in range(len(lines)):
        #     if('INPUT(' in lines[i]):
        #         strName = lines[i][lines[i].find('INPUT(')+len('INPUT('):lines[i].find(')')]
        #         listInput.append(strName)
        #         continue
        #     if('OUTPUT(' in lines[i]):
        #         strName = lines[i][lines[i].find('OUTPUT(')+len('OUTPUT('):lines[i].find(')')]
        #         listOutput.append(strName)
        #         continue
        # listInput = sorted(listInput)
        # listOutput = sorted(listOutput)
        # bContainPorts = True
        # while(True == bContainPorts):
        #     bContainPorts = False
        #     for line in lines:
        #         if(('INPUT(' in line) or ('OUTPUT(' in line)):
        #             bContainPorts = True
        #             lines.remove(line)
        #             break


        # for i in listOutput:
        #     strTemp = 'OUTPUT('+i+')\n'
        #     lines.insert(0,strTemp)
        # for i in listInput:
        #     strTemp = 'INPUT('+i+')\n'
        #     lines.insert(0,strTemp)
        

        with open(bench_file, 'w') as bf:
            for line in lines:
                line = line.strip('\n')
                bf.write(line+'\n')


    def _generate_sub_circuit_graph(self, list_nodes_name, temp_circuit_graph, b_sub_circuit_or_remain_part=True): # b_sub_circuit_or_remain_part True-subckts, False-remain part
        temp_circuit_graph.PI = []
        temp_circuit_graph.PO = []
        temp_circuit_graph.PPI = []
        temp_circuit_graph.PPO = []
        in_port_prefix = 'i_cg_'
        in_port_prefix = self.in_port_prefix
        out_port_prefix = self.out_port_prefix
        # generate sub circuit graph
        if(True == b_sub_circuit_or_remain_part): # selected sub circuit
            for graph_node in self.circuit_graph.object_list:
                if(graph_node.name in list_nodes_name):
                    if(graph_node in self.circuit_graph.PI):
                        temp_circuit_graph.PI.append(temp_circuit_graph.name_to_node[graph_node.name])
                    if(graph_node in self.circuit_graph.PO):
                        temp_circuit_graph.PO.append(temp_circuit_graph.name_to_node[graph_node.name])
                    listInputName = []
                    listOutputName = []
                    # input nodes
                    for in_node in graph_node.fan_in_node:
                        if(in_node.name not in listInputName):
                            listInputName.append(in_node.name)
                    for in_node_name in listInputName:
                        if(in_node_name not in list_nodes_name):
                            temp_in_node_name = in_port_prefix + in_node_name # input_circuitgraph_[temp_in_node.name]
                            if(temp_in_node_name not in temp_circuit_graph.name_to_node.keys()):
                                temp_in_node = Ntk_Parser.NtkObject(temp_in_node_name)
                                temp_circuit_graph.add_object(temp_in_node, 'IPT')
                                temp_circuit_graph.PI.append(temp_in_node)
                            else:
                                temp_in_node = temp_circuit_graph.name_to_node[temp_in_node_name]
                            temp_circuit_graph.disconnect_objectives_by_name(in_node_name, graph_node.name)
                            temp_circuit_graph.connect_objectives_by_name(temp_in_node.name, graph_node.name)
                                
                    # output nodes
                    for out_node in graph_node.fan_out_node:
                        if(out_node.name not in listOutputName):
                            listOutputName.append(out_node.name)
                    for out_node_name in listOutputName:
                        if(out_node_name not in list_nodes_name):
                            if(temp_circuit_graph.name_to_node[graph_node.name] not in temp_circuit_graph.PO):
                                temp_circuit_graph.PO.append(temp_circuit_graph.name_to_node[graph_node.name])
                                
                            temp_circuit_graph.disconnect_objectives_by_name(graph_node.name, out_node_name)                      
      
            # re-construct node list
            listNodesName = []
            for graph_node in temp_circuit_graph.object_list:
                if(graph_node.name not in listNodesName):
                    listNodesName.append(graph_node.name)
            for graph_node_name in listNodesName:
                # if(0 == graph_node.gate_type):
                if((graph_node_name not in list_nodes_name) and (graph_node_name in self.circuit_graph.name_to_node.keys())):
                    temp_circuit_graph.disconnect_objectives_from_circuit_graph(temp_circuit_graph.name_to_node[graph_node_name]) #disconnect from whole graph
            for graph_node_name in listNodesName:
                if(graph_node_name in temp_circuit_graph.name_to_node.keys()):
                    temp_node = temp_circuit_graph.name_to_node[graph_node_name]
                    if(temp_node.name not in list_nodes_name):
                        temp_circuit_graph.remove_object(temp_node) #remove from whole graph
        else: # remain part
            for graph_node in self.circuit_graph.object_list:
                if(graph_node.name not in list_nodes_name):
                    if(graph_node in self.circuit_graph.PI):
                        temp_circuit_graph.PI.append(temp_circuit_graph.name_to_node[graph_node.name])
                    if(graph_node in self.circuit_graph.PO):
                        temp_circuit_graph.PO.append(temp_circuit_graph.name_to_node[graph_node.name])
                    # input nodes
                    for in_node in graph_node.fan_in_node:
                        if(in_node.name in list_nodes_name):
                            temp_in_node_name = in_port_prefix + in_node.name # input_circuitgraph_[temp_in_node.name]
                            if(temp_in_node_name not in temp_circuit_graph.name_to_node.keys()):
                                temp_in_node = Ntk_Parser.NtkObject(temp_in_node_name)
                                temp_circuit_graph.add_object(temp_in_node, 'IPT')
                                temp_circuit_graph.PI.append(temp_in_node)
                            else:
                                temp_in_node = temp_circuit_graph.name_to_node[temp_in_node_name]
                            temp_circuit_graph.disconnect_objectives_by_name(in_node.name, graph_node.name)
                            temp_circuit_graph.connect_objectives_by_name(temp_in_node.name, graph_node.name)
                                
                    # output nodes
                    for out_node in graph_node.fan_out_node:
                        if(out_node.name in list_nodes_name):
                            if(temp_circuit_graph.name_to_node[graph_node.name] not in temp_circuit_graph.PO):
                                temp_circuit_graph.PO.append(temp_circuit_graph.name_to_node[graph_node.name])
                                
                            temp_circuit_graph.disconnect_objectives_by_name(graph_node.name, out_node.name)                      
        
            # re-construct node list
            for graph_node in temp_circuit_graph.object_list:
                # if(0 == graph_node.gate_type):
                if(graph_node.name in list_nodes_name):
                    temp_circuit_graph.disconnect_objectives_from_circuit_graph(graph_node) #disconnect from whole graph
            for graph_node in self.circuit_graph.object_list:
                if(graph_node.name in temp_circuit_graph.name_to_node.keys()):
                    temp_node = temp_circuit_graph.name_to_node[graph_node.name]
                    if(temp_node.name in list_nodes_name):
                        temp_circuit_graph.remove_object(temp_node) #remove from whole graph

        # generate remain circuit graph
        return temp_circuit_graph

    # haven't debug!!!!!!!!!!!!!!!!!!
    def generate_bench_of_multiple_subckts(self, strIterFolder, input_path_bench, strRecordFile, intReplacement, listsubckt = []):
        circuit_graph = Ntk_Parser.ntk_parser(input_path_bench)
        remain_circuit_graph = Ntk_Parser.ntk_parser(input_path_bench)
        strIterNum = os.path.split(strIterFolder)[1].replace('iter', '')
        if(0 == len(listsubckt)):
            listReplaceSubckts = self.get_redacted_subckts_list(strIterNum, intReplacement, listDeleteSubckt = [], nReplaceRegularSubckt = 0)
        else:
            listReplaceSubckts = listsubckt
        listLUT_v = self.get_exist_lut_files(self.strRTL_LUTRoot)
        listLUT_bench = self.get_exist_lut_files(self.strBench_LUTRoot)
        listNodes = []
        nKeyInputExist = len(circuit_graph.KI)
        nKeyInputCount = nKeyInputExist

        listNodesObj = []
        list_nodes_name = []
        dictSubcktInfo = {}
        for subckt in listReplaceSubckts:
            cktname = os.path.join(strIterFolder, subckt[:subckt.find('\t')]+'.sc')
            with open(cktname, 'r') as scf:
                listNodes = scf.readlines()
            dictSubcktInfo[subckt[:subckt.find('\t')]] = len(listNodes)
            
            for i in range(len(listNodes)):
                listNodes[i] = listNodes[i].strip('\n')
                if(listNodes[i] in circuit_graph.name_to_node.keys()):
                    listNodesObj.append(circuit_graph.name_to_node[listNodes[i]])
                    list_nodes_name.append(listNodes[i])
                else:
                    print("Cannot find node in circuit graph!")
            # for node in listNodes:
            #     strTemp = node.strip('\n')
            #     if(strTemp in circuit_graph.name_to_node.keys()):
            #         listNodesObj.append(circuit_graph.name_to_node[strTemp])
            #     else:
            #         print("Cannot find node in circuit graph!")


        listInputNodes, listOutputNodes, listDeleteNodes = self.get_input_and_output(circuit_graph, listNodes, listNodesObj)

        sub_circuit_graph = self._generate_sub_circuit_graph(list_nodes_name, circuit_graph, b_sub_circuit_or_remain_part=True)
        remain_part_circuit_graph = self._generate_sub_circuit_graph(list_nodes_name, remain_circuit_graph, b_sub_circuit_or_remain_part=False)
        intermediatePath = os.path.split(strRecordFile)[0]
        if(False == os.path.exists(intermediatePath)):
            os.makedirs(intermediatePath)
        
        strLogFile = os.path.join(intermediatePath, 'RedactSubcktsInfo.txt')
        nCount = 0
        with open(strLogFile, 'w') as lf:
            for key in dictSubcktInfo.keys():
                strTemp = key + ',' + str(dictSubcktInfo[key]) + '\n'
                nCount = nCount + dictSubcktInfo[key]
                lf.write(strTemp)
            lf.write('Total Nodes: ' + str(nCount))
            # for subckt in listReplaceSubckts:
            #     cktname = subckt[:subckt.find('\t')]
            #     cktname = cktname.strip('\n')
            #     cktname = cktname+'\n'
            #     lf.write(cktname)

        strSubcktBenchFile = os.path.join(intermediatePath, 'sub_ckts.bench')
        strRemainBenchFile = os.path.join(intermediatePath, 'remain_part.bench')
        # strOriBenchFile = os.path.join(intermediatePath, 'top.bench')
        # shutil.copy()
        Ntk_Parser.ntk_to_bench(sub_circuit_graph, strSubcktBenchFile)
        Ntk_Parser.ntk_to_bench(remain_part_circuit_graph, strRemainBenchFile)
        # self._rename_signals_in_bench(strObfBenchFile)
        return strSubcktBenchFile, strRemainBenchFile




        # for subckt in listReplaceSubckts:
        #     cktname = os.path.join(strIterFolder, subckt[:subckt.find('\t')]+'.sc')
        #     with open(cktname, 'r') as scf:
        #         listNodes = scf.readlines()
        #     listNodesObj = []
        #     for i in range(len(listNodes)):
        #         listNodes[i] = listNodes[i].strip('\n')
        #         if(listNodes[i] in circuit_graph.name_to_node.keys()):
        #             listNodesObj.append(circuit_graph.name_to_node[listNodes[i]])
        #         else:
        #             print("Cannot find node in circuit graph!")
        #     # for node in listNodes:
        #     #     strTemp = node.strip('\n')
        #     #     if(strTemp in circuit_graph.name_to_node.keys()):
        #     #         listNodesObj.append(circuit_graph.name_to_node[strTemp])
        #     #     else:
        #     #         print("Cannot find node in circuit graph!")

        #     # replace subckts by lut
        #     listInputNodes, listOutputNodes, listDeleteNodes = self.get_input_and_output(circuit_graph, listNodes, listNodesObj)
        #     strLUTFileName = 'lut_'+str(len(listInputNodes)) + '_' + str(len(listOutputNodes)) + '.v'
        #     strLUTBenchName = 'lut_'+str(len(listInputNodes)) + '_' + str(len(listOutputNodes)) + '.bench'
        #     strLUTFilePath = os.path.join(self.strRTL_LUTRoot, strLUTFileName)
        #     strLUTBenchPath = os.path.join(self.strBench_LUTRoot, strLUTBenchName)
        #     if(strLUTFileName not in listLUT_v):
        #         self.generate_lut_v(strLUTFilePath)
        #     if(strLUTBenchName not in listLUT_bench):
        #         self.convert_lut_v_to_bench(strLUTFilePath, strLUTBenchPath)
        #     LUT_Circuit_Graph = Ntk_Parser.ntk_parser(strLUTBenchPath)
        #     listLUTPrimaryInput = []
        #     for node in LUT_Circuit_Graph.PI:
        #         if('prog_keyq' not in node.name):
        #             listLUTPrimaryInput.append(node)
        #     if((len(listInputNodes) != len(listLUTPrimaryInput)) or (len(listOutputNodes) != len(LUT_Circuit_Graph.PO))):
        #         print("Unequal input/output nodes!")

            
        #     # check name of nodes
        #     for obj in LUT_Circuit_Graph.object_list:
        #         if('prog_keyq' in obj.name):
        #             strNewName = 'keyinputq'+str(nKeyInputCount)+'p'
        #             LUT_Circuit_Graph.change_node_name(obj, strNewName)
        #             nKeyInputCount = nKeyInputCount + 1
        #         elif(obj.name in circuit_graph.name_to_node.keys()): # name already exist
        #             strNewName = obj.name+'_rename_'+cktname
        #             nCount = 0
        #             while(strNewName in circuit_graph.name_to_node.keys()):
        #                 strNewName = strNewName + str(nCount)
        #                 nCount = nCount + 1
        #             LUT_Circuit_Graph.change_node_name(obj, strNewName)
        #         circuit_graph.add_object(obj)
        #         if('keyinputq' in obj.name):
        #             circuit_graph.KI.append(obj)

            
        #     # map input/output nodes
        #     dictInputNodesMap = {}
        #     dictOutputNodesMap = {}
        #     for i in range(len(listInputNodes)):
        #         if(listInputNodes[i][1] == 'PI'):
        #             circuit_graph.add_PI(circuit_graph.name_to_node(listLUTPrimaryInput[i].name))
        #         elif(listInputNodes[i][1] == 'normal'):
        #             dictInputNodesMap[listInputNodes[i][0].name] = listLUTPrimaryInput[i].name
        #             # replace LUT's input nodes by outer nodes
        #             for opt_node in circuit_graph.name_to_node[listLUTPrimaryInput[i].name].fan_out_node:
        #                 circuit_graph.connect_objectives(listInputNodes[i][0], opt_node)
        #             circuit_graph.disconnect_objectives_from_circuit_graph(circuit_graph.name_to_node[listLUTPrimaryInput[i].name])
        #             circuit_graph.remove_object(circuit_graph.name_to_node[listLUTPrimaryInput[i].name])
        #     for i in range(len(listOutputNodes)):
        #         if(listOutputNodes[i][1] == 'PO'):
        #             circuit_graph.add_PO(circuit_graph.name_to_node[LUT_Circuit_Graph.PO[i].name])
        #         elif(listOutputNodes[i][1] == 'normal'):
        #             dictOutputNodesMap[LUT_Circuit_Graph.PO[i].name] = listOutputNodes[i][0].name
        #             # replace LUT's output nodes by outer nodes
        #             circuit_graph.connect_objectives(circuit_graph.name_to_node[LUT_Circuit_Graph.PO[i].name], listOutputNodes[i][0])


        #     # delete old subckt
        #     for deletenode in listDeleteNodes:
        #         circuit_graph.disconnect_objectives_from_circuit_graph(deletenode)
        #         circuit_graph.remove_object(deletenode)
            
        # print('Subckts redaction finished!')
        # intermediatePath = os.path.split(strRecordFile)[0]
        # if(False == os.path.exists(intermediatePath)):
        #     os.makedirs(intermediatePath)
        # strObfBenchFile = os.path.join(intermediatePath, 'top_obf.bench')
        # # strOriBenchFile = os.path.join(intermediatePath, 'top.bench')
        # # shutil.copy()
        # Ntk_Parser.ntk_to_bench(circuit_graph, strObfBenchFile)
        # # self._rename_signals_in_bench(strObfBenchFile)
        # return strObfBenchFile
        
        

            
    def copy_original_bench_to_intermediate_folder(self, strOriginalBenchFile, strIntermediateFolder):
        strDestBenchFile = os.path.join(strIntermediateFolder, 'top.bench')
        shutil.copy(strOriginalBenchFile, strDestBenchFile)
        return strDestBenchFile

            

    def convert_lut_v_to_bench(self, strLUTFilePath, strLUTBenchPath):
        lut_gl = self._convert_lut_v_to_gatelavel(strLUTFilePath, strLUTBenchPath)
        lut_bench = self._convert_lut_gl_to_bench(lut_gl, strLUTBenchPath)
        self.listLUT_bench = self.get_exist_lut_files(self.strBench_LUTRoot)

    def _convert_lut_gl_to_bench(self, LUT_gate_level, strLUTBenchPath):
        lut_name = os.path.splitext(os.path.split(LUT_gate_level)[1])[0]
        strIntermediatePath = os.path.split(LUT_gate_level)[0]
        currentPath = os.getcwd()

        os.chdir(strIntermediatePath)
        with open(self.path_template_get_bench_tcl, 'r') as fgbtcl:
            lines = fgbtcl.readlines()
        
        for i in range(len(lines)):
            if('OUTPUTVERILOGPATH/TOPORTOP_OBF.v' in lines[i]):
                lines[i] = lines[i].replace('OUTPUTVERILOGPATH/TOPORTOP_OBF.v', LUT_gate_level)
                continue
            if('OUTPUTVERILOGPATH/TOPORTOP_OBF.bench' in lines[i]):
                lines[i] = lines[i].replace('OUTPUTVERILOGPATH/TOPORTOP_OBF.bench', strLUTBenchPath)
                continue
            if('CODEROOT' in lines[i]):
                lines[i] = lines[i].replace('CODEROOT', self.workdir)
                continue

        newScriptFile = os.path.join(strIntermediatePath, lut_name + '_bench.tcl')
        with open(newScriptFile, 'w') as nfgbtcl:
            for line in lines:
                nfgbtcl.write(line)
        
        print("Modify %s_bench.tcl finish." % lut_name)
        strCmd = self.path_abc + " -f " + newScriptFile + ' > ' + os.path.join(strIntermediatePath, 'abc_' + lut_name + '_log.log')
        status = os.system(strCmd)
        if(0 == status):
            print("Generate %s.bench finish." % lut_name)
        else:
            print("===ERROR: Cannot generate %s.bench!===" % lut_name)
        os.chdir(currentPath)
        
        return newScriptFile



    def _convert_lut_v_to_gatelavel(self, strLUTFilePath, strLUTBenchPath):
        LUT_MODULE_NAME = os.path.splitext(os.path.split(strLUTFilePath)[1])[0]
        tempath = os.path.join(os.path.split(strLUTBenchPath)[0],'temp')
        tempath = os.path.join(tempath, LUT_MODULE_NAME)
        currentPath = os.getcwd()
        if(False == os.path.exists(tempath)):
            os.makedirs(tempath)
        os.chdir(tempath)
        

        OUTPUT_LUT_GATELEVEL_VERILOG_FILE = os.path.join(tempath, os.path.split(strLUTFilePath)[1])
        with open(self.path_template_run_compile_dc_lut_converter_tcl, 'r') as luttclf:
            lines = luttclf.readlines()
        
        for i in range(len(lines)):
            if('LUT_MODULE_NAME' in lines[i]):
                lines[i] = lines[i].replace('LUT_MODULE_NAME', LUT_MODULE_NAME)
                continue
            if('INPUT_LUT_VERILOG_FILE' in lines[i]):
                lines[i] = lines[i].replace('INPUT_LUT_VERILOG_FILE', strLUTFilePath)
                continue
            if('OUTPUT_LUT_GATELEVEL_VERILOG_FILE' in lines[i]):
                lines[i] = lines[i].replace('OUTPUT_LUT_GATELEVEL_VERILOG_FILE', OUTPUT_LUT_GATELEVEL_VERILOG_FILE)
                continue

        newScriptFile = os.path.join(tempath, 'run_compile_dc.tcl')
        with open(newScriptFile, 'w') as tclf:
            for i in range(len(lines)):
                tclf.write(lines[i])

        print("Generate tcl file to convert lut.v to gate level!")

        strLogFile = os.path.join(tempath, LUT_MODULE_NAME+'_log.log')
        strCmd = "dc_shell -f " + newScriptFile + " > " + strLogFile
        status = os.system(strCmd)
        if(0 == status):
            with open(strLogFile, 'r') as dclf:
                while(True):
                    strLine = dclf.readline()
                    if(not strLine):
                        break
                    if('Error:' in strLine):
                        status = 1
                        ErrInfo = strLine
                        break
            if(0 == status):
                print("Generate %s.v finish." % os.path.split(strLUTBenchPath)[1])
            else:
                print("===ERROR: Cannot generate %s.v!===" % os.path.split(strLUTBenchPath)[1])
        else:
            print("===ERROR: Cannot generate %s.v!===" % os.path.split(strLUTBenchPath)[1])
        os.chdir(currentPath)

        return OUTPUT_LUT_GATELEVEL_VERILOG_FILE
        

            


    def generate_lut_v(self, strLUTFilePath):
        lut_name = os.path.splitext(os.path.split(strLUTFilePath)[1])[0]
        
        in_width = int(lut_name[lut_name.find('lut_')+len('lut_'):lut_name.rfind('_')])
        out_width = int(lut_name[lut_name.rfind('_')+len('_'):])
        self.lut_mux_gen4(in_width, out_width)
        self.listLUTFiles = self.get_exist_lut_files(self.strRTL_LUTRoot)

    def get_input_and_output(self, circuit_graph, listNodes, listNodesObj):
        listInputNodes = []
        listOutputNodes = []
        listDeleteNodes = []
        for node in listNodesObj:# name
            listTemp = []
            if(0 == len(node.fan_in_node)):
                for PInode in circuit_graph.PI:
                    listTemp = []
                    if(node == PInode):
                        listTemp.append(node)
                        listTemp.append('PI')
                        listInputNodes.append(listTemp)
                        break
            else:
                for inputnode in node.fan_in_node:
                    listTemp = []
                    if(inputnode.name not in listNodes):
                        if(inputnode not in listInputNodes):
                            listTemp.append(inputnode)
                            listTemp.append('normal')
                            listInputNodes.append(listTemp)
            if(0 == len(node.fan_out_node)):
                for POnode in circuit_graph.PO:
                    listTemp = []
                    if(node == POnode):
                        listTemp.append(node)
                        listTemp.append('PO')
                        listOutputNodes.append(listTemp)
                        break
            else:
                for outputnode in node.fan_out_node:
                    listTemp = []
                    if(outputnode.name not in listNodes):
                        if(outputnode not in listOutputNodes):
                            listTemp.append(outputnode)
                            listTemp.append('normal')
                            listOutputNodes.append(listTemp)
            listDeleteNodes.append(node)
        
        return listInputNodes, listOutputNodes, listDeleteNodes
        
        
def run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, SATtimeout=0, nTotalCircuitNum=-1, listFinish=[], strDefaultArea="DefaultArea"):
    nOriginalRequiredReplacement = nReplacement
    nOldReplacement = nReplacement
    nReplaceRegularSubckt = 0
    nTimeout = -1
    nLastReplacement = 0
    listLastReplace = []

    listTXT = []
    strDataPath = os.path.join(strItersRoot, 'iter'+str(nIter))
    for item in os.listdir(strDataPath):
        if(item.endswith(".txt")):
            listTXT.append(item)
    
    bNeedCopy = True
    strSourceFile = os.path.join(strDataPath, '_conflict_subckt.txt')
    strCopiedFileName = '_conflict_subckt_original.txt'
    strDstFile = os.path.join(strDataPath, strCopiedFileName)
    for item in listTXT:
        if(strCopiedFileName in item):
            bNeedCopy = False
            break
    if(True == bNeedCopy):
        shutil.copy(strSourceFile, strDstFile)


    while(1): 
        print("=========Iter%d, Replace%d=========" % (nIter, nReplacement))
        print(uef.strRecordFile)
        nIter, nReplacementConflictSubckts = uef.check_iter_replacement_parameters_only_conflict_subckts(nIter, nReplacement, strItersRoot)
        if(-1 == nTotalCircuitNum):
            # nReplaceRegularSubckt = nOldReplacement - nReplacementConflictSubckts
            nReplaceRegularSubckt = nReplacement - nReplacementConflictSubckts
        # elif(nOldReplacement < nTotalCircuitNum):
        elif(nReplacement < nTotalCircuitNum):
            # nReplaceRegularSubckt = nOldReplacement - nReplacementConflictSubckts
            nReplaceRegularSubckt = nReplacement - nReplacementConflictSubckts
        else:
            nReplaceRegularSubckt = nTotalCircuitNum - nReplacementConflictSubckts
        nActuralReplaceSubckt = nReplaceRegularSubckt + nReplacementConflictSubckts

        strFinish = "iter"+str(nIter)+'\tActReplace:'+str(nActuralReplaceSubckt)+'\tConflictReplace:'+str(nReplacementConflictSubckts)+'\tRegularReplace:'+str(nReplaceRegularSubckt)
        if(strFinish in listFinish):
            print('Iter:'+str(nIter)+' Replacement:'+str(nActuralReplaceSubckt)+' Already run!')
            nCount = 0
            for item in listFinish:
                if(strFinish in item):
                    nCount = nCount + 1
            strRenameSuffix = "_old_" + str(nCount)
            strIntermediatePath = os.path.split(uef.strRecordFile)[0]
            strIntermediatePath = os.path.join(strIntermediatePath, 'iter'+str(nIter))
            strIntermediatePath = os.path.join(strIntermediatePath, 'replace_'+str(nActuralReplaceSubckt))
            os.rename(strIntermediatePath, strIntermediatePath+strRenameSuffix)
            listFinish.append(strFinish+strRenameSuffix)

            # return nTimeout, nReplacement, listFinish
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
            nReplaceRegularSubckt = nReplacement - nReplacementConflictSubckts
            strKey, listReplaceConflictSubckt, listRegularSubcktRedact, nTotalGates = uef.modify_top_plx_by_conflict_order(str(nIter), nReplacement, uef.listDeleteSubckt, nReplaceRegularSubckt)
            listReplace = listReplaceConflictSubckt+listRegularSubcktRedact
            dictTemp[strKey] = listReplace
            if((nReplacement == nLastReplacement) and (listReplace == listLastReplace)):
                print("=====Cannot replace anymore!=====")
                return nTimeout, nReplacement, listFinish
            else:
                nLastReplacement = nReplacement
                listLastReplace = copy.deepcopy(listReplace)
            listStatus, strDC_top_obf_log = uef.run_compile_dc(inputtclfile, outputvpath)
            if(0 != listStatus[0]):
                print(listStatus[1])
                return nTimeout, nReplacement, listFinish
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
                        # nReplacement = nActuralReplaceSubckt
                else:
                    nReplacement = math.ceil((nMinError+nMaxGood)/2)
                    if(nReplacement == nMinError):
                        uef.listDeleteSubckt.append(dictTemp[strMinErrorKey][-2])
                    
        if(0 != listStatus[0]):
            print(listStatus[1])
            return nTimeout, nReplacement, listFinish
        benchfile = uef.convert_verilog_to_bench_by_abc(inputtclfile, outputvpath) # obf
        benchfile = uef.optimize_bench_file(benchfile)
        listBenchFile.append(benchfile)

        uef.dictSubCktRecordTotal[strKey] = uef.dictConflictSubCktRecord[strKey] + listRegularSubcktRedact
        SAToutputlog, nTimeout = uef.sat_attack(listBenchFile, strTempPath, SATtimeout)
        strBenchName = os.path.split(strDataRoot)[1]
        strArea = uef.get_area_from_dc_log_file(strDC_top_obf_log)
        strOverhead = '=(' + strArea + '-' + strDefaultArea + ')/' + strDefaultArea
        uef.read_sat_log_results(SAToutputlog, strBenchName, nIter, nReplacement, strOverhead, nTotalGates)



        # ====================================================
        if(False == uef.delete_conflict_sub_ckt):
            uef.dictSubCktRecordTotal[strKey].append('Good')
            if(nOriginalRequiredReplacement == nActuralReplaceSubckt):
                break
            else:
                uef.listCorrectSubckt = copy.deepcopy(uef.dictSubCktRecordTotal[strKey])
                uef.listCorrectSubckt.remove('Good')
                nTemp = -1
                nMinErrReplace = nOldReplacement
                nMaxGoodReplace = 0
                for key in uef.dictSubCktRecordTotal.keys():
                    nTemp = key[key.find('_'):]
                    nTemp = int(nTemp.replace('_replace',''))
                    if(uef.dictSubCktRecordTotal[key][-1] == 'MatchError'):
                        if(nTemp < nMinErrReplace):
                            nMinErrReplace = nTemp
                    elif(uef.dictSubCktRecordTotal[key][-1] == 'Good'):
                        if(nTemp > nMaxGoodReplace):
                            nMaxGoodReplace = nTemp
                if(uef.kickone == 0):
                    nReplacement = math.ceil((nMinErrReplace+nMaxGoodReplace)/2)
                else:
                    nReplacement = nMinErrReplace
                    uef.kickone = 0
        else:
            uef.dictSubCktRecordTotal[strKey].append('MatchError')
            strTemp = ""
            nMaxLength = -1
            for key in uef.dictSubCktRecordTotal.keys():
                if('Good' == uef.dictSubCktRecordTotal[key][-1]):
                    if((len(uef.dictSubCktRecordTotal[key])-1) > nMaxLength):
                        strTemp = key
                        nMaxLength = len(uef.dictSubCktRecordTotal[key])-1
            
            if("" != strTemp):
                if((len(uef.dictSubCktRecordTotal[strTemp])-1) + 1 < (len(uef.dictSubCktRecordTotal[strKey])-1)):
                    nReplacement = nMaxLength + math.ceil((len(uef.dictSubCktRecordTotal[strKey])-len(uef.dictSubCktRecordTotal[strTemp]))/2)
                else:
                    uef.listDeleteSubckt.append(uef.dictSubCktRecordTotal[strKey][-2])
            else:
                if('iter'+str(nIter)+'_replace1' in uef.dictSubCktRecordTotal.keys()):
                    uef.listDeleteSubckt.append(uef.dictSubCktRecordTotal['iter'+str(nIter)+'_replace1'][-2])
                nReplacement = 1
        # ====================================================



        # if(False == uef.delete_conflict_sub_ckt):
        #     uef.dictConflictSubCktRecord[strKey].append('Good')
        #     if(nOriginalRequiredReplacement == nActuralReplaceSubckt):
        #         break
        #     else:
        #         uef.listCorrectSubckt = copy.deepcopy(uef.dictConflictSubCktRecord[strKey])
        #         uef.listCorrectSubckt.remove('Good')
        #         nTemp = -1
        #         nMinErrReplace = nOldReplacement
        #         nMaxGoodReplace = 0
        #         for key in uef.dictConflictSubCktRecord.keys():
        #             nTemp = key[key.find('_'):]
        #             nTemp = int(nTemp.replace('_replace',''))
        #             if(uef.dictConflictSubCktRecord[key][-1] == 'MatchError'):
        #                 if(nTemp < nMinErrReplace):
        #                     nMinErrReplace = nTemp
        #             elif(uef.dictConflictSubCktRecord[key][-1] == 'Good'):
        #                 if(nTemp > nMaxGoodReplace):
        #                     nMaxGoodReplace = nTemp
        #         if(uef.kickone == 0):
        #             nReplacement = math.ceil((nMinErrReplace+nMaxGoodReplace)/2)
        #         else:
        #             nReplacement = nMinErrReplace
        #             uef.kickone = 0
        # else:
        #     uef.dictConflictSubCktRecord[strKey].append('MatchError')
        #     strTemp = ""
        #     nMaxLength = -1
        #     for key in uef.dictConflictSubCktRecord.keys():
        #         if('Good' == uef.dictConflictSubCktRecord[key][-1]):
        #             if((len(uef.dictConflictSubCktRecord[key])-1) > nMaxLength):
        #                 strTemp = key
        #                 nMaxLength = len(uef.dictConflictSubCktRecord[key])-1
            
        #     if("" != strTemp):
        #         if((len(uef.dictConflictSubCktRecord[strTemp])-1) + 1 < (len(uef.dictConflictSubCktRecord[strKey])-1)):
        #             nReplacement = nMaxLength + math.ceil((len(uef.dictConflictSubCktRecord[strKey])-len(uef.dictConflictSubCktRecord[strTemp]))/2)
        #         else:
        #             uef.listDeleteSubckt.append(uef.dictConflictSubCktRecord[strKey][-2])
        #     else:
        #         if('iter'+str(nIter)+'_replace1' in uef.dictConflictSubCktRecord.keys()):
        #             uef.listDeleteSubckt.append(uef.dictConflictSubCktRecord['iter'+str(nIter)+'_replace1'][-2])
        #         nReplacement = 1

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

    #test
    # listTest = [1,2,3,4,5,6]
    # for i in listTest:
    #     listTest.remove(i)


    strDataRoot = '/home/UFAD/guor/experiment_data/UFM/Circuit_Partition_Tool_data/arbiter_20230104040630_ms0_af_5804'
    strRTL_LUTRoot = '/home/UFAD/guor/intermediate_data_files/MyDemo/UFM/rtl'
    if(False == os.path.exists(strRTL_LUTRoot)):
        os.makedirs(strRTL_LUTRoot)
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

    
    strBench_LUTRoot = os.path.join(os.path.split(strRTL_LUTRoot)[0], 'lut_bench')

    if(False == os.path.exists(strBench_LUTRoot)):
        os.makedirs(strBench_LUTRoot)

    
    strRecordFile = os.path.join(strOutputDir,'intermediate_files_efpga_'+strBenchName+'_'+strtime)
    strRecordFile = os.path.join(strRecordFile, 'record_'+strtime+'.txt')
    # strRecordFile = '/home/UFAD/guor/Codes_old/MyDemo/Circuit_Partition_Tool_data/intermediate_files_'+strBenchName+'_'+strtime+'/record_'+strtime+'.txt'
    print(strRecordFile)
    strDataRoot = os.path.abspath(os.path.expanduser(strDataRoot))
    strItersRoot = os.path.join(strDataRoot, 'sub_circuit')
    file_name_list = os.listdir(strItersRoot)
    nTimeoutLimit = 86400 # s, 24hr

    listReplacement = [5,10,15,20,25,30]
    # listReplacement = [20,30]

    

    # ===================================TEST=====================================
    # dclogfile = '/home/UFAD/guor/Codes_old/MyDemo/Circuit_Partition_Tool_data/intermediate_files_sin_20220927201525/iter0/replace_25/dc_top_obf_log.log'
    # strArea = uef.get_area_from_dc_log_file(dclogfile)
    # strOverhead = '=(' + strArea + '-' + strDefaultArea + ')/' + strDefaultArea
    # uef.modify_top_plx_by_conflict_order('3', 5, listDeleteSubckt = [], nReplaceRegularSubckt = 0)
    # strDC_top_obf_log = '/home/UFAD/guor/Codes_old/MyDemo/Circuit_Partition_Tool_data/intermediate_files_sin_20220927201525/intermediate_files_sin_20221005164310/iter3/replace_5/dc_top_obf_log.log'
    # strArea = uef.get_area_from_dc_log_file(strDC_top_obf_log)
    # strOverhead = '=(' + strArea + '-' + strDefaultArea + ')/' + strDefaultArea
    # ===================================TEST=====================================


    
    nTotalCircuitNum = -1
    nConflictCircuitNum = -1
    listFinish = []

    # #==============================run one time======================
    strIterFolder = os.path.join(strItersRoot, 'iter'+str(nIter))
    nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(strIterFolder, nIter)
    # if(0 == nRunMode):
    #     uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
    #     # nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(os.path.join(strItersRoot, iter+str(nIter)), nIter)
    #     nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea)
    # #==============================run one time======================

    # Create ckt graph
    # input_path_bench = cpt_config['temp_path'] + '/' + cpt_config['circuit_name'] + '.bench'
    listBench = []
    uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
    uef.strBench_LUTRoot = strBench_LUTRoot
    for item in os.listdir(strDataRoot):
        if(item.endswith(".bench")):
            listBench.append(os.path.join(strDataRoot, item))
    input_path_bench = listBench[0]
    # circuit_graph = Ntk_Parser.ntk_parser(input_path_bench)
    # circuit_graph.change_node_name(circuit_graph.name_to_node['START'], 'START1')
    uef.circuit_graph = Ntk_Parser.ntk_parser(input_path_bench)

    strSubcktBenchFile, strRemainBenchFile = uef.generate_bench_of_multiple_subckts(strIterFolder, input_path_bench, strRecordFile, intReplacement=5, listsubckt = [])
    uef._rename_signals_in_bench(strSubcktBenchFile)
    out_v_file = os.path.split(strSubcktBenchFile)[0] + '/sub_ckts_yosys.v'
    uef.bench_to_v(strSubcktBenchFile, out_v_file)
    out_v_file = uef._eliminate_basic_syntax_errors_for_verilog(out_v_file)
    out_v_file_minname = uef.verilog_minmodule_name_optimizer(out_v_file)
    str_back_slash = '_bs_'
    str_slash = '_s_'
    out_v_file_minname = uef.replace_slash_and_back_slash(out_v_file_minname, str_back_slash, str_slash)
    out_v_file_minname = uef.replace_square_brackets(out_v_file_minname)
    print('Multi-subckts generated!')

    uef._rename_signals_in_bench(strRemainBenchFile)
    out_v_file = os.path.split(strRemainBenchFile)[0] + '/remain_parts_yosys.v'
    uef.bench_to_v(strRemainBenchFile, out_v_file)
    out_v_file = uef._eliminate_basic_syntax_errors_for_verilog(out_v_file)
    out_v_file_minname = uef.verilog_minmodule_name_optimizer(out_v_file)
    str_back_slash = '_bs_'
    str_slash = '_s_'
    out_v_file_minname = uef.replace_slash_and_back_slash(out_v_file_minname, str_back_slash, str_slash)
    out_v_file_minname = uef.replace_square_brackets(out_v_file_minname)
    print('Remain-parts generated!')
    # strIntermediateFolder = os.path.split(strRecordFile)[0]
    # if(False == os.path.exists(strIntermediateFolder)):
    #     os.makedirs(strIntermediateFolder)
    # strOriBenchFile = uef.copy_original_bench_to_intermediate_folder(input_path_bench, strIntermediateFolder)
    # listBenchFile = [strOriBenchFile, strObfBenchFile]
    # uef._rename_signals_in_bench(listBenchFile[0])
    # uef._rename_signals_in_bench(listBenchFile[1])
    # SAToutputlog, nTimeout = uef.sat_attack(listBenchFile, strIntermediateFolder, 86400)


    

