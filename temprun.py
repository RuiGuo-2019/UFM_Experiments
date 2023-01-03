from ufm_exp_flow_ntk import *

strDataRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/sin_20220927111930_ms0_af_7492'
strRecordFile = os.path.join('/home/UFAD/guor/Codes/MyDemo', 'record_123456.txt')
strRTL_LUTRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/rtl'
uef = ufm_experiment_flow(strDataRoot, strRecordFile, strRTL_LUTRoot)
bench_file = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_CG_b05_20221223035515/1/top_abc_dc_abc.bench'
uef.resort_input_and_output_ports_in_bench(bench_file)
bench_file = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_CG_b05_20221223035515/1/top_obf_abc_dc_abc.bench'
uef.resort_input_and_output_ports_in_bench(bench_file)
