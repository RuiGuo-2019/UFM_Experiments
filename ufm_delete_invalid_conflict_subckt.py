import os
import time
def delete_invalid_conflict_subckts(strConflictFileRoot, strInvalidConflictRecordFileRoot):
    strConflictFile = os.path.join(strConflictFileRoot, "_conflict_subckt.txt")
    if(False == os.path.exists(strConflictFile)):
        print(strConflictFile,'not exist!')
        return
    strInvalidConflictRecordFile = os.path.join(strInvalidConflictRecordFileRoot, "InvalidConflictSubckt.txt")
    if(False == os.path.exists(strInvalidConflictRecordFile)):
        print(strInvalidConflictRecordFile,'not exist!')
        return
    
    # back up old version
    strTime = time.strftime("%Y%m%d%H%M%S", time.localtime())
    strBackupFile = os.path.join(strConflictFileRoot, "backup_"+strTime+"_conflict_subckt.txt")
    with open(strConflictFile, 'r') as cf:
        strConflictSubckt = cf.readline()
    with open(strBackupFile, 'w') as bauf:
            bauf.write(strConflictSubckt)
    strConflictSubckt = strConflictSubckt.replace('[','')
    strConflictSubckt = strConflictSubckt.replace(']','')
    listConflictSubckt = strConflictSubckt.split(',')
    for i in range(len(listConflictSubckt)):
        listConflictSubckt[i] = listConflictSubckt[i].strip()

    listDelete = []
    with open(strInvalidConflictRecordFile, 'r') as icrf:
        linesInvConfSubckt = icrf.readlines()
    for line in linesInvConfSubckt:
        listDeleteTemp = []
        line = line.replace('\n','')
        line = line.replace('[','')
        line = line.replace(']','')
        line = line.replace('"','')
        line = line.replace("'",'')
        listDeleteTemp = line.split(',')
        for cktname in listDeleteTemp:
            cktname = cktname.strip()
            if(cktname not in listDelete):
                listDelete.append(cktname)
    
    for cktname in listDelete:
        if(cktname in listConflictSubckt):
            listConflictSubckt.remove(cktname)
    strWrite = "["
    for i in listConflictSubckt:
        strWrite = strWrite + i + ', '
    strWrite = strWrite[:-2]+ ']'
    with open(strConflictFile, 'w') as cf:
        cf.write(strWrite)

    print("Generate new conflict file finish!")




if __name__ == '__main__':

    strConflictFileRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/div_20220918235039_ms0_af_4586/sub_circuit/iter0'
    strInvalidSubckRecordRoot = '/home/UFAD/guor/Codes/MyDemo/Circuit_Partition_Tool_data/intermediate_files_div_20220922004310'

    delete_invalid_conflict_subckts(strConflictFileRoot, strInvalidSubckRecordRoot)