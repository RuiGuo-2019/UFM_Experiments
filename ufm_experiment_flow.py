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

class ufm_experiment_flow:
    def __init__(self, strDataRoot, strRecordFile, strRTL_LUTRoot):
        self.strRTL_LUTRoot = strRTL_LUTRoot
        self.listLUTFiles = self.get_exist_lut_files(self.strRTL_LUTRoot)
        self.strRecordFile = strRecordFile
        self.strInvalidConflictSubcktFile = os.path.join(os.path.split(self.strRecordFile)[0], 'InvalidConflictSubckt.txt')
        self.workdir = os.getcwd()
        self.path_abc = os.path.abspath('/home/UFAD/guor/Codes_old/Python/MyDemo/UFM/abc-master-Sazadur/abc')
        self.path_sld = os.path.abspath('/home/UFAD/guor/Codes_old/Python/MyDemo/UFM/FromSazadur/Rui/spramod-host15-logic-encryption-7fdc93c47b0e/bin/sld')
        self.path_template_modify_iters_csh = os.path.join(self.workdir, 'modify_iters.csh')
        self.path_template_modify_top_plx = os.path.join(self.workdir, 'modify_top.plx')
        self.path_template_run_compile_dc_tcl = os.path.join(self.workdir, 'run_compile_dc.tcl')
        self.path_template_get_bench_tcl = os.path.join(self.workdir, 'get_bench.tcl')
        self.subckt_list_file_name = '_recommend_sub_ckt.txt'
        # self.subckt_list_file_name = '_conflict_subckt.txt'
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
        self.IO_location = 6 # 6th'\t': input num 6th\t output num
    
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
                    if((self.IO_location - 1) <= listTemp[0].count('\t')):
                        strTemp = listTemp[0]
                        strTemp = strTemp.strip('\n')
                        # while(1 < strTemp.count('\t')):
                        for tabsigncount in range(self.IO_location - 1):
                            strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                        indices = [ind for ind, c in enumerate(strTemp) if c == '\t']
                        if(1 < len(indices)):
                            endindex = indices[1]
                        else:
                            endindex = len(strTemp)
                        nInput = int(strTemp[:strTemp.find('\t')])
                        nOutput = int(strTemp[strTemp.find('\t')+len('\t'):endindex])    
                    listTemp.append(nInput)
                    listTemp.append(nOutput)
                    listNewConflictSubCktInfo.append(listTemp)
            
            listNewConflictSubCktInfo = sorted(listNewConflictSubCktInfo,key = lambda x:x[1], reverse = False)
        
            for item in listNewConflictSubCktInfo:
                listNewOrderConflictSubCkt.append(item[0][:item[0].find('\t')])
        elif(1 == nSortMode): # 1-score from high to low
            for conflictsubckt in listConflictSubCkt:
                conflictsubckt = conflictsubckt.strip()
                conflictsubckt = conflictsubckt.replace('\n','')
                listNewOrderConflictSubCkt.append(conflictsubckt)
        
        return listNewOrderConflictSubCkt


    def modify_top_plx_by_conflict_order(self, strIterNum, intReplacement, listDeleteSubckt = [], nReplaceRegularSubckt = 0):
        strIterOrderFile = os.path.join(self.strDataRoot, 'sub_circuit')
        strIterOrderFile = os.path.join(strIterOrderFile, 'iter'+strIterNum)
        # strIterOrderFile = os.path.join(strIterOrderFile, '_conflict_subckt.txt')
        strIterOrderFile = os.path.join(strIterOrderFile, self.subckt_list_file_name)


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

        while('#' == subcktinfo[0][0]):
            subcktinfo.pop(0)
        # del(subcktinfo[0])
        # del(subcktinfo[0])

        if('_recommend_sub_ckt.txt' in strIterOrderFile):
            listOrder = self.resort_conflict_subckt(listConflictSubCkt=listOriginalOrder, listSubcktInfo=subcktinfo, nSortMode=1)
        elif('_conflict_subckt.txt' in strIterOrderFile):
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
                    if((self.IO_location - 1) <= item.count('\t')):
                        temp = item
                        # while(1 < temp.count('\t')):
                        for tabsigncount in range(self.IO_location - 1):
                            temp = temp[temp.find('\t')+len('\t'):]
                        indices = [ind for ind, c in enumerate(temp) if c == '\t']
                        if(1 < len(indices)):
                            endindex = indices[1]
                        else:
                            endindex = len(temp)
                        temp = temp.strip('\n')
                        strInput = temp[:temp.find('\t')]
                        strOutput = temp[temp.find('\t')+len('\t'):endindex]
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
        
        while(len(listReplaceOrder) > intReplacement):
            listReplaceOrder.pop(-1)

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
            if((self.IO_location - 1) > temp.count('\t')):# no io info
                continue
            else:
                strRedact = strRedact + temp[:temp.find('\t')]
                self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                nTimes = 0
                # while(1 < temp.count('\t')):
                for tabsigncount in range(self.IO_location - 1):
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + ', '
                    temp = temp[temp.find('\t')+len('\t'):]
                    if(0 == nTimes):
                        strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + '\n'
                        nTotalGates = nTotalGates + int(temp[:temp.find('\t')])
                    nTimes = nTimes + 1
                indices = [ind for ind, c in enumerate(temp) if c == '\t']
                if(1 < len(indices)):
                    endindex = indices[1]
                else:
                    endindex = len(temp)
                temp = temp[:endindex]
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
        nReplaceRegularSubckt = intReplacement - len(listReplaceOrder)
        if('_conflict_subckt.txt' in strIterOrderFile):
            for i in range(nSubcktinfoLens, -1, -1):
                if(len(listRegularSubcktRedact) >= nReplaceRegularSubckt):
                    break
                elif(subcktinfo[i] in listReplaceOrder):
                    continue
                else:
                    temp = subcktinfo[i]
                    if((self.IO_location - 1) > temp.count('\t')):
                        continue
                    strTemp = temp
                    strTemp1 = strTemp[:strTemp.find('\t')]
                    if(strTemp1 in self.listDeleteSubckt):
                        continue
                    # while(1 < strTemp.count('\t')):
                    for tabsigncount in range(self.IO_location - 1):
                        strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                    indices = [ind for ind, c in enumerate(strTemp) if c == '\t']
                    if(1 < len(indices)):
                        endindex = indices[1]
                    else:
                        endindex = len(strTemp)
                    strTemp = strTemp.strip('\n')
                    strInput = strTemp[:strTemp.find('\t')]
                    strOutput = strTemp[strTemp.find('\t')+len('\t'):endindex]
                    if(strInput == '0' or strOutput == '0'):
                        if(strTemp1 not in self.listDeleteSubckt):
                            self.listDeleteSubckt.append(strTemp1)
                            continue

                    listRegularSubcktRedactInfo.append(temp)
                    listRegularSubcktRedact.append(temp[:temp.find('\t')])
                    # self.dictConflictSubCktRecord[strKey].append(temp[:temp.find('\t')])
                    strRedact = strRedact + temp[:temp.find('\t')]
                    nTimes = 0
                    # while(1 < temp.count('\t')):
                    for tabsigncount in range(self.IO_location - 1):
                        if(0 == nTimes):
                            strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + ', '
                        temp = temp[temp.find('\t')+len('\t'):]
                        if(0 == nTimes):
                            strRedactSubcktInfo = strRedactSubcktInfo + temp[:temp.find('\t')] + '\n'
                            nTotalGates = nTotalGates + int(temp[:temp.find('\t')])
                        nTimes = nTimes + 1
                    indices = [ind for ind, c in enumerate(temp) if c == '\t']
                    if(1 < len(indices)):
                        endindex = indices[1]
                    else:
                        endindex = len(temp)
                    temp = temp[:endindex]
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
                # ufm_delete_invalid_conflict_subckt.delete_invalid_conflict_subckts(strIterInfoFileRoot, strInvalidSubckRecordRoot)
                ufm_delete_invalid_conflict_subckt.delete_invalid_subckts(self.subckt_list_file_name, strIterInfoFileRoot, strInvalidSubckRecordRoot)
        
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
                    # while(1 < strTemp.count('\t')):
                    for tabsigncount in range(self.IO_location - 1):
                        strTemp = strTemp[strTemp.find('\t')+len('\t'):]
                    indices = [ind for ind, c in enumerate(strTemp) if c == '\t']
                    if(1 < len(indices)):
                        endindex = indices[1]
                    else:
                        endindex = len(strTemp)
                    strTemp = strTemp[:endindex]
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
            if((self.IO_location - 1) > temp.count('\t')):# no io info
                continue
            else:
                strRedact = strRedact + temp[:temp.find('\t')]
                # while(1 < temp.count('\t')):
                for tabsigncount in range(self.IO_location - 1):
                    temp = temp[temp.find('\t')+len('\t'):]
                indices = [ind for ind, c in enumerate(temp) if c == '\t']
                if(1 < len(indices)):
                    endindex = indices[1]
                else:
                    endindex = len(temp)
                temp = temp[:endindex]
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

    def rename_signals_in_verilog(self, strtop_v, strtop_obf_v):
        with open(strtop_v, 'r') as tvf:
            lines = tvf.readlines()

        dictDFFStandard = {}
        nMaxWire = 0
        strMaxWire = ''
        for i in range(len(lines)): # get standard D and Q
            if('DFFRHQX1 ' in lines[i]):
                strInstName = lines[i][lines[i].find('DFFRHQX1 ') + len('DFFRHQX1 '): lines[i].find(' ( .D(')]
                strD = lines[i][lines[i].find(' ( .D(') + len(' ( .D('): lines[i].find('), .CK(')]
                if(strInstName not in dictDFFStandard.keys()):
                    dictDFFStandard[strInstName] = {}
                    dictDFFStandard[strInstName]['D'] = strD
            if(re.search(r", n[\d]+;", lines[i])):
                nTemp = int(lines[i][lines[i].rfind(', n')+len(', n'):lines[i].rfind(';')])
                if(nTemp > nMaxWire):
                    nMaxWire = nTemp
                    strMaxWire = 'n'+str(nMaxWire)

        
        with open(strtop_obf_v, 'r') as tovf:
            linesobf = tovf.readlines()
        
        dictDFFobf = {}
        for i in range(len(linesobf)): # get standard D and Q
            if('DFFRHQX1 ' in linesobf[i]):
                strInstName = linesobf[i][linesobf[i].find('DFFRHQX1 ') + len('DFFRHQX1 '): linesobf[i].find(' ( .D(')]
                strD = linesobf[i][linesobf[i].find(' ( .D(') + len(' ( .D('): linesobf[i].find('), .CK(')]
                if(strInstName not in dictDFFobf.keys()):
                    dictDFFobf[strInstName] = {}
                    dictDFFobf[strInstName]['D'] = strD
            if(re.search(r", n[\d]+;", linesobf[i])):
                nTemp = int(linesobf[i][linesobf[i].rfind(', n')+len(', n'):linesobf[i].rfind(';')])
                if(nTemp > nMaxWire):
                    nMaxWire = nTemp
                    strMaxWire = 'n'+str(nMaxWire)

        listReplace = []
        listReplaceStandard = []
        if(len(dictDFFobf) != len(dictDFFStandard)):
            print("Top and top_obf have different number of DFFs!")
        else:
            for inst in dictDFFStandard.keys():
                listTemp = []
                if(dictDFFStandard[inst]['D'] != dictDFFobf[inst]['D']):
                    nMaxWire = nMaxWire + 1
                    strMaxWire = 'n'+str(nMaxWire)
                    listTemp = [dictDFFobf[inst]['D'], strMaxWire]
                    listReplace.append(listTemp)
                    listTemp = [dictDFFStandard[inst]['D'], strMaxWire]
                    listReplaceStandard.append(listTemp)


        for i in range(len(lines)):
            for item in listReplaceStandard:
                strSource = item[0]
                strDest = item[1]
                if(' '+strSource+',' in lines[i]):
                    lines[i] = lines[i].replace(' '+strSource+',', ' '+strDest+',')
                if(' '+strSource+';' in lines[i]):
                    lines[i] = lines[i].replace(' '+strSource+';', ' '+strDest+';')
                if('('+strSource+')' in lines[i]):
                    lines[i] = lines[i].replace('('+strSource+')', '('+strDest+')')
                if(' '+strSource+')' in lines[i]):
                    lines[i] = lines[i].replace(' '+strSource+')', ' '+strDest+')')
        
        for i in range(len(linesobf)):
            for item in listReplace:
                strSource = item[0]
                strDest = item[1]
                if(' '+strSource+',' in linesobf[i]):
                    linesobf[i] = linesobf[i].replace(' '+strSource+',', ' '+strDest+',')
                if(' '+strSource+';' in linesobf[i]):
                    linesobf[i] = linesobf[i].replace(' '+strSource+';', ' '+strDest+';')
                if('('+strSource+')' in linesobf[i]):
                    linesobf[i] = linesobf[i].replace('('+strSource+')', '('+strDest+')')
                if(' '+strSource+')' in linesobf[i]):
                    linesobf[i] = linesobf[i].replace(' '+strSource+')', ' '+strDest+')')

        with open(strtop_v, 'w') as tvf:
            for line in lines:
                tvf.write(line)

        with open(strtop_obf_v, 'w') as tovf:
            for line in linesobf:
                tovf.write(line)







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
        strSource = "source /apps/settings"
        strCmd = strSource + "&&" + strCmd
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

    def convert_verilog_to_bench_by_abc(self, outputvpath, inputfilename=""):
        if("" != inputfilename):
            inputfilename = os.path.split(inputfilename)[1]
            if('_obf_' in inputfilename):
                strTOPORTOP_OBF = 'top_obf'
            else:
                strTOPORTOP_OBF = 'top'
        else:
            strTOPORTOP_OBF = 'top_obf'

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

        return strOutputFile, strOriginalVerilogFile
        
    def get_ports_info_from_v(self, v_file):
        with open(v_file,'r') as scv:
            parsed_f = (scv.read()).split(";")
        
        dictPorts = {}
        for i in range(len(parsed_f)):
            parsed_f[i] += ";"
            # if(re.search(r"module[\s]+[\w\d\S]*\([\w\d\s,]*\);", parsed_f[i])):
            if(re.search(r"([\n\s(\\n)]*)module\s+.+\(", parsed_f[i])):
                strTemp = parsed_f[i][parsed_f[i].find('module')+len('module'):]
                strTemp = strTemp.strip()
                strModuleName = strTemp[:strTemp.find('(')]
                strModuleName = strModuleName.strip()
                continue
            #####################################
            # Match Input
            #####################################
            # elif(re.match(r"^([\n\s(\\n)]*)input\s+([\[\]\/\\\w\d\s,]+);$", parsed_f[i])):
            elif(re.match(r"([\n\s(\\n)]*)input\s+([\[\]\/\\\$\w\d\s,]+);", parsed_f[i])):
                strLine = parsed_f[i]
                strLine = strLine[strLine.find('input')+len('input'):]
                # x = re.findall(r"[\w\d\[\]]+[,;]", strLine)
                # x = re.findall(r"[\w/\\]*[\w\d\[\]\s]+[,;]", strLine)
                x = re.findall(r"[\w/\\\$]*[\w\d\[\]\s]+[,;]", strLine)       
                for j in x:
                    tempListPortInfo = [] #[str_name, min_bit, max_bit, int_type] #type:0:input,1:output,2:reg,3:wire
                    j = re.sub(r",|;", "", j)
                    j = j.strip()
                    if(j in dictPorts.keys()):
                        dictPorts[j][0].append(0)
                    else:
                        dictPorts[j] = [[0]]

            #####################################
            # Match Output
            # Qeustion: Is it possible that some outputs are in the form of bus?
            #####################################
            # elif(re.match(r"^([\n\s(\\n)]*)output\s+([\[\]\/\\\w\d\s,]+);$", parsed_f[i])):
            elif(re.match(r"([\n\s(\\n)]*)output\s+([\[\]\/\\\$\w\d\s,]+);", parsed_f[i])):
                strLine = parsed_f[i]
                strLine = strLine[strLine.find('output')+len('output'):]
                # x = re.findall(r"[\w/\\]*[\w\d\[\]\s]+[,;]", strLine)
                x = re.findall(r"[\w/\\\$]*[\w\d\[\]\s]+[,;]", strLine)
                for j in x:
                    tempListPortInfo = [] #[str_name, min_bit, max_bit, int_type] #type:0:input,1:output,2:reg,3:wire
                    j = re.sub(r",|;", "", j)
                    j = j.strip()
                    if(j in dictPorts.keys()):
                        dictPorts[j][0].append(1)
                    else:
                        dictPorts[j] = [[1]]
        
        return strModuleName, dictPorts

    def optimize_bench_file(self, original_verilog_file, benchfile):
        strModuleName, dictPorts = self.get_ports_info_from_v(original_verilog_file)
        with open(benchfile, 'r') as bf:
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
                # if(strName in dictPorts.keys()):
                #     if(1 == dictPorts[strName][0][0]):
                #         listOutput.append(strName)
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

    def delete_illegal_gates(self, v_file, gatetype):
        with open(v_file,'r') as vf:
            lines = vf.readlines()

        if("AND2X1" == gatetype):
            for i in range(len(lines)):
                if("AND2X1 " in lines[i]): #   AND2X1 U251149 ( .A(n255502), .B(n255478) );
                    if(';' not in lines[i]):
                        continue
                    elif("), .Y(" not in lines[i]):
                        lines[i] = '//' + lines[i]

        

        with open(v_file,'w') as vf:
            for line in lines:
                vf.write(line)

        return v_file



    def detect_errors_by_abc(self, strtop_obf_v):
        nStatus = 0
        nParsingAndGateStatus = 1
        while(1 == nParsingAndGateStatus):
            if(1 == nStatus):
                break
            nStatus = 0
            nParsingAndGateStatus = 0
            strGatetype = ''
            strOutputVPath = os.path.split(strtop_obf_v)[0]
            self.convert_verilog_to_bench_by_abc(strOutputVPath) # original
            strlogfile = os.path.join(self.strIntermediatePath, 'abc_' + 'top_obf' + '_log.log')
            with open(strlogfile, 'r') as lf:
                lines = lf.readlines()
            
            for line in lines:
                if('contains combinational loop!' in line):
                    nStatus = 1
                    break
                if(('Parsing of gate ' in line) and (' has failed.' in line)): # Parsing of gate AND2X1 has failed.
                    nParsingAndGateStatus = 1
                    strGatetype = line[line.find('Parsing of gate ') + len('Parsing of gate '):line.find(' has failed.')]

            if("" == strGatetype):
                nParsingAndGateStatus = 0
            if(1 == nStatus):
                return nStatus
            elif(1 == nParsingAndGateStatus):
                self.delete_illegal_gates(strtop_obf_v, strGatetype)



        return nStatus


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
    
    def get_all_available_subckts(self, strIterNum):
        strIterInfoFile = os.path.join(self.strDataRoot, 'sub_circuit')
        strIterInfoFile = os.path.join(strIterInfoFile, 'iter'+strIterNum)
        strIterInfoFile = os.path.join(strIterInfoFile, '_iter'+strIterNum+'_info.txt')
        with open(strIterInfoFile, 'r') as iif:
            subcktinfo = iif.readlines()
        del(subcktinfo[0])
        del(subcktinfo[0])

        for i in range(len(subcktinfo)):
            subcktinfo[i] = subcktinfo[i][:subcktinfo[i].find('\t')]

        for subckt in self.listDeleteSubckt:
            if(subckt in subcktinfo):
                subcktinfo.remove(subckt)
        
        return subcktinfo



        
        
def run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, SATtimeout=0, nTotalCircuitNum=-1, listFinish=[], strDefaultArea="DefaultArea", nPerformSATAttack=False, bSeq=True):
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
            strIntermediatePath_Iter = os.path.split(uef.strRecordFile)[0]
            strIntermediatePath_Iter = os.path.join(strIntermediatePath_Iter, 'iter'+str(nIter))
            strOldPath = os.path.join(strIntermediatePath_Iter, 'replace_'+str(nActuralReplaceSubckt))
            listAlreadyRun = os.listdir(strIntermediatePath_Iter)
            strRenameSuffix = "_old_" + str(nCount)
            strNewName = 'replace_'+str(nActuralReplaceSubckt)+strRenameSuffix
            while(strNewName in listAlreadyRun):
                nCount = nCount + 1
                strRenameSuffix = "_old_" + str(nCount)
                strNewName = 'replace_'+str(nActuralReplaceSubckt)+strRenameSuffix
            strNewPath = os.path.join(strIntermediatePath_Iter, strNewName)

            os.rename(strOldPath, strNewPath)
            listFinish.append(strFinish+strRenameSuffix)

            # return nTimeout, nReplacement, listFinish
        else:
            listFinish.append(strFinish)

        nReplacement = nActuralReplaceSubckt
        listBenchFile = []
        strTempPath = uef.prepare_folders(str(nIter), nReplacement)
        uef.modify_iters_csh(str(nIter), nReplacement)
        inputtclfileOri = os.path.join(strTempPath, 'read_'+str(nIter)+'.tcl')
        outputvpath = strTempPath
        listStatus, strDC_top_log = uef.run_compile_dc(inputtclfileOri, outputvpath)
        if(1 == listStatus[0]):
            print(listStatus[1])
            return nTimeout, nReplacement, listFinish


        inputtclfile = os.path.join(strTempPath, 'read_obf_'+str(nIter)+'.tcl')
                
        flagbreak = 0
        dictTemp = {}
        while(1):
            nReplaceRegularSubckt = nReplacement - nReplacementConflictSubckts
            strKey, listReplaceConflictSubckt, listRegularSubcktRedact, nTotalGates = uef.modify_top_plx_by_conflict_order(str(nIter), nReplacement, uef.listDeleteSubckt, nReplaceRegularSubckt)
            listReplace = listReplaceConflictSubckt+listRegularSubcktRedact
            nActReplace = len(listReplace)
            dictTemp[strKey] = listReplace
            # if(strKey[:strKey.find('_replace')+len('_replace')]+str(nActReplace) in uef.dictSubCktRecordTotal.keys()):
            #     listTemp = uef.dictSubCktRecordTotal[strKey[:strKey.find('_replace')+len('_replace')]+str(nActReplace)]
            #     if(0 != len(listTemp)):
            #         if(('Good' == listTemp[-1]) or ('MatchError' == listTemp[-1])):
            #             del listTemp[-1]
            #     if(listTemp == listReplace):
            #         print("=====Cannot find more subckts to use!=====")
            #         return nTimeout, nActReplace, listFinish
            if(listReplace == listLastReplace):
                listAvailableSubckts = uef.get_all_available_subckts(str(nIter))
                if(len(listAvailableSubckts) < nOriginalRequiredReplacement):
                    print("=====Cannot replace anymore!=====")
                    return nTimeout, nActReplace, listFinish
                else:
                    nReplacement = nReplacement + 1
            else:
                nLastReplacement = nReplacement
                listLastReplace = copy.deepcopy(listReplace)
            listStatus, strDC_top_obf_log = uef.run_compile_dc(inputtclfile, outputvpath)
            if(0 != listStatus[0]):
                print(listStatus[1])
                return nTimeout, nActReplace, listFinish
            listTempDeleteSubckt = uef.find_dc_timing_warnings(strDC_top_obf_log)
            CombLoopStatus = 0
            if(True == bSeq):
                listTempDeleteSubckt = []
                strtop_v = os.path.join(outputvpath,'top.v')
                strtop_obf_v = os.path.join(outputvpath,'top_obf.v')
                uef.rename_signals_in_verilog(strtop_v, strtop_obf_v)
                CombLoopStatus = uef.detect_errors_by_abc(strtop_obf_v)
            if((0 == len(listTempDeleteSubckt)) and (0 == CombLoopStatus)):      
                dictTemp[strKey].append("Good")
                # needkickonesubckt = 0
                if(nReplacement == nActuralReplaceSubckt):
                    flagbreak = 1
                    break
                nMinError = nActuralReplaceSubckt+1
                strMinErrorKey = "iter"+str(nIter)+"_replace"+str(nActuralReplaceSubckt+1)
                for key in dictTemp.keys():
                    if("Error" == dictTemp[key][-1]):
                        nLength = int(key[key.find('replace')+len('replace'):])
                        if(nLength < nReplacement):
                            continue
                        elif(nLength < nMinError):
                            nMinError = nLength
                            strMinErrorKey = key
                nReplacement = nMinError
                continue
                
            else:
                needkickonesubckt = 1
                dictTemp[strKey].append("Error")
                nMaxGood = 0
                strMaxGoodKey = ""
                for key in uef.dictSubCktRecordTotal.keys():
                    if('Good' == uef.dictSubCktRecordTotal[key][-1]):
                        nLength = int(key[key.find('replace')+len('replace'):])
                        if(nLength > nMaxGood):
                            nMaxGood = nLength
                            strMaxGoodKey = key
                for deleteitem in listTempDeleteSubckt:
                    if((deleteitem in listReplace) and (deleteitem not in uef.listDeleteSubckt)):
                        if('' != strMaxGoodKey):
                            if(deleteitem not in uef.dictSubCktRecordTotal[strMaxGoodKey]):
                                needkickonesubckt = 0
                                uef.listDeleteSubckt.append(deleteitem)
                        else:
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
                if("" == strMaxGoodKey):
                    for key in uef.dictSubCktRecordTotal.keys():
                        if('Good' == uef.dictSubCktRecordTotal[key][-1]):
                            nLength = int(key[key.find('replace')+len('replace'):])
                            if(nLength > nMaxGood):
                                nMaxGood = nLength
                                strMaxGoodKey = key


                if(0 != len(listTempDeleteSubckt)):
                    if("" == strMaxGoodKey):
                        if(1 == nReplacement):
                            if(dictTemp[strMinErrorKey][-2] not in uef.listDeleteSubckt):
                                uef.listDeleteSubckt.append(dictTemp[strMinErrorKey][-2])
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
                        if("" != strMaxGoodKey):
                            if(dictTemp[strMinErrorKey][-2] not in dictTemp[strMaxGoodKey]):
                                uef.listDeleteSubckt.append(dictTemp[strMinErrorKey][-2])
                        elif(1 == nMinError):
                            uef.listDeleteSubckt.append(dictTemp[strMinErrorKey][-2])
                    
        if(0 != listStatus[0]):
            print(listStatus[1])
            return nTimeout, nActReplace, listFinish
        
        benchfileOri, strOriginalVerilogFile = uef.convert_verilog_to_bench_by_abc(outputvpath, inputtclfileOri) # original
        benchfileOri = uef.optimize_bench_file(strOriginalVerilogFile, benchfileOri)
        listBenchFile.append(benchfileOri)

        benchfile, strOriginalVerilogFile = uef.convert_verilog_to_bench_by_abc(outputvpath, inputtclfile) # obf
        benchfile = uef.optimize_bench_file(strOriginalVerilogFile, benchfile)
        listBenchFile.append(benchfile)

        uef.dictSubCktRecordTotal[strKey] = uef.dictConflictSubCktRecord[strKey] + listRegularSubcktRedact
        if(True == nPerformSATAttack):
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
        

    return nTimeout, nActReplace, listFinish
    
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
        if(', DFF: ' in line):
            nTotalCircuitNum = int(line[line.find(', Sub ckt: ')+len(', Sub ckt: '):line.find(', DFF: ')]) # Iteration: 0, Sub ckt: 91, DFF: 0
        else:
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
    strDataRoot = '/home/UFAD/guor/experiment_data/UFM/Circuit_Partition_Tool_data/arbiter_20230104040630_ms0_af_5804'
    strRTL_LUTRoot = '/home/UFAD/guor/CouldBeRemove/MyDemo/UFM/rtl'
    strOutputDir = '/home/UFAD/guor/intermediate_data_files/UFM'
    nPerformSATAttack = True
    bSeq = True
    if(False == os.path.exists(strRTL_LUTRoot)):
        os.makedirs(strRTL_LUTRoot)
    strtime = time.strftime("%Y%m%d%H%M%S", time.localtime())
    

    nRunMode = 0 #0, 1, 2
    nIter = 0
    nMaxReplacement = 100
    nMinReplacement = 1
    nReplacement = 5
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
    parser.add_argument("-l", action="store", required=False, type=str, help="list of replace, use '-' to separate, e.g. 5-10-15")
    parser.add_argument("-maxr", action="store", required=False, type=str, help="nMaxReplacement, default 100")
    args = parser.parse_args()
    
    listReplacement = [5,10,15,20,25,30]

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
    if(None != args.a):
        strDefaultArea = args.a
    if(None != args.l):
        strTemp = args.l
        listReplacement = strTemp.split("-")
        for i in range(len(listReplacement)):
            listReplacement[i] = int(listReplacement[i])
    if(None != args.maxr):
        nMaxReplacement = int(args.maxr)

    
    strBenchName = os.path.split(strDataRoot)[1]
    strBenchName = strBenchName[:strBenchName.find('_')]

    
    
    strRecordFile = os.path.join(strOutputDir,'intermediate_files_'+strBenchName+'_'+strtime)
    strRecordFile = os.path.join(strRecordFile, 'record_'+strtime+'.txt')
    # strRecordFile = '/home/UFAD/guor/Codes_old/MyDemo/Circuit_Partition_Tool_data/intermediate_files_'+strBenchName+'_'+strtime+'/record_'+strtime+'.txt'
    print(strRecordFile)
    strDataRoot = os.path.abspath(os.path.expanduser(strDataRoot))
    strItersRoot = os.path.join(strDataRoot, 'sub_circuit')
    file_name_list = os.listdir(strItersRoot)
    nTimeoutLimit = 86400 # s, 24hr

    
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
    #==============================run one time======================
    strIterFolder = os.path.join(strItersRoot, 'iter'+str(nIter))
    nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(strIterFolder, nIter)
    if(0 == nRunMode):
        uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
        # nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(os.path.join(strItersRoot, iter+str(nIter)), nIter)
        nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack, bSeq)
    #==============================run one time======================
    
    # #==============================run cycles======================
    elif(1 == nRunMode):      
        if(None == args.i):
            for nIter in range(len(file_name_list)):
                strIterFolder = os.path.join(strItersRoot, 'iter'+str(nIter))
                nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(strIterFolder, nIter)
                print("Iter"+str(nIter)+":"+str(nTotalCircuitNum)+" subckts, "+str(nConflictCircuitNum)+" conflict sub-circuits.")
                uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
                for nReplacement in listReplacement:
                    # nSATtimeoutStatus, nActReplace, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack)
                    nSATtimeoutStatus, nActReplace, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack, bSeq)
                    if(nActReplace < nReplacement):
                        print("Cannot replace more subckts! Only %d subckt(s) could be used in iter%d!" % (nActReplace,nIter))
                        break

        else:
            for nReplacement in listReplacement:
                uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
                # nSATtimeoutStatus, nActReplace, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack)
                nSATtimeoutStatus, nActReplace, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack, bSeq)
                if(nActReplace < nReplacement):
                    print("Cannot replace more subckts! Only %d subckt(s) could be used in iter%d!" % (nActReplace,nIter))
                    break

    #==============================find closer to 24hrs======================
    elif(2 == nRunMode):
        dictFinish = {}
        listFinish = []
        nReplacement = nMaxReplacement
        uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
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
            # nSATtimeoutStatus, nReplacement = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack)
            nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack, bSeq)
            dictFinish[nReplacement] = nSATtimeoutStatus
            if(1 == nSATtimeoutStatus):
                nMaxReplacement = nReplacement
            else:
                nMinReplacement = nReplacement
                if(nMinReplacement == nMaxReplacement):
                    nMaxReplacement = 2*nMaxReplacement

    # #==============================run cycles======================
    elif(3 == nRunMode):       # start from iter i ,replace j
        if(None == args.i):
            print("Need to set from which iter!")
        else:
            for nIter in range(int(args.i), len(file_name_list)):
                strIterFolder = os.path.join(strItersRoot, 'iter'+str(nIter))
                nTotalCircuitNum, nConflictCircuitNum = get_total_circuit_in_iter(strIterFolder, nIter)
                print("Iter"+str(nIter)+":"+str(nTotalCircuitNum)+" subckts, "+str(nConflictCircuitNum)+" conflict sub-circuits.")
                uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
                for nReplacement in listReplacement:
                    if(nIter == int(args.i)):
                        if((None != args.r) and (nReplacement < int(args.r))):
                            continue
                    nSATtimeoutStatus, nReplacement, listFinish = run_one_test(nIter, nReplacement, uef, strDataRoot, strItersRoot, nTimeoutLimit, nTotalCircuitNum, listFinish, strDefaultArea, nPerformSATAttack)