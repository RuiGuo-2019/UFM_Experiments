# from ufm_exp_flow_ntk import *
from ufm_experiment_flow import *
import Ntk_Parser
import os
import subprocess

if __name__ == "__main__":
    # strDataRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/sin_20220927111930_ms0_af_7492'
    # strRecordFile = os.path.join('/home/UFAD/guor/Codes/MyDemo', 'record_123456.txt')
    # strRTL_LUTRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/rtl'
    # uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
    # bench_file = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_CG_b05_20221223035515/1/top_abc_dc_abc.bench'
    # uef.resort_input_and_output_ports_in_bench(bench_file)
    # bench_file = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_CG_b05_20221223035515/1/top_obf_abc_dc_abc.bench'
    # uef.resort_input_and_output_ports_in_bench(bench_file)

    # inputbench = '/home/UFAD/guor/experiment_data/UFM/Circuit_Partition_Tool_data/b02_20230107182858_ms0_af_909/b02.bench'
    # outputbench = '/home/UFAD/guor/experiment_data/UFM/Circuit_Partition_Tool_data/b02_20230107182858_ms0_af_909/b02_comb.bench'
    # Ntk_Parser.seq_to_comb(inputbench, outputbench)

    # strLogFile = '/home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230116083916/iter0/replace_10/dc_top_log.log'
    # strCmd = 'source /apps/settings&&dc_shell -f /home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230116083916/iter0/replace_10/run_compile_dc_top.tcl > /home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230116083916/iter0/replace_10/dc_top_log.log'
    # status = os.system(strCmd)
    # if(0 == status):
    #     with open(strLogFile, 'r') as dclf:
    #         while(True):
    #             strLine = dclf.readline()
    #             if(not strLine):
    #                 break
    #             if('Error:' in strLsubprocessine):
    #                 status = 1
    #                 ErrInfo = strLine
    #                 break
    #     if(0 == status):
    #         print("Generate .v finish.")
    #     else:
    #         print("===ERROR: Cannot generate .v!===")
    # else:
    #     print("===ERROR: Cannot generate .v!===")


    # listCmd = ['dc_shell', '-f', '/home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230116083916/iter0/replace_10/run_compile_dc_top.tcl']
    # cmd = 'source /apps/settings\ndc_shell -f /home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230116083916/iter0/replace_10/run_compile_dc_top.tcl'
    # with open('/home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230116083916/iter0/replace_10/dc_top_log_subprocess.log', 'w') as lf:
    #     subprocess.call(cmd, shell=True, executable='/bin/bash', stdout=lf)


    strDataRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/sin_20220927111930_ms0_af_7492'
    strRecordFile = os.path.join('/home/UFAD/guor/Codes/MyDemo', 'record_123456.txt')
    strRTL_LUTRoot = '/home/UFAD/guor/CouldBeRemove/MyDemo/UFM/rtl'
    uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
    ori_v = '/home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230223162120/iter0/replace_2/top.v'
    obf_v = '/home/UFAD/guor/intermediate_data_files/UFM/intermediate_files_b02_20230223162120/iter0/replace_2/top_obf.v'
    uef.rename_verilog_for_RANE_attack(ori_v, obf_v, 0, 2)