import numpy as np
import pickle
import datetime
import logging
from scipy.io import loadmat
import os
import struct
import csv
import scipy.stats
import itertools

global console_log

def decode_status(packets):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Locates any "status" packets, and prints a nicely-formatted string.

    inputs: 
        packets: A list of "packet" dictionaries, as returned from decode_packets.py
    outputs:
        A list of dictionaries, containing all the keys + values from the status message.
        Use "print_status(list)" to print a nice string
    '''

    logger = logging.getLogger(__name__ +'.decode_status')


    out_data = []

    # get status packets    
    for p in filter(lambda packet: packet['dtype'] == 'I', packets):
        try:
            data = p['data'][:p['bytecount']]

            source = chr(data[3])
            prev_command = np.array(np.flip(data[0:3]), dtype=np.uint8)
            prev_bbr_command = np.array(np.flip(data[4:7]), dtype=np.uint8)
            prev_burst_command = np.array(np.flip(data[12:15]), dtype=np.uint8)
            total_commands = data[16] + 256*data[17]
            
            system_config = np.flip(data[20:24])

            # Cast it to a binary string
            system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')

            gps_resets = int(system_config[29:32],base=2)
            e_deployer_counter = int(system_config[0:4],base=2)
            b_deployer_counter = int(system_config[4:8],base=2)
            arm_e = int(system_config[13])
            arm_b = int(system_config[14])
            gps_enable = int(system_config[15])
            e_enable = int(system_config[26])
            b_enable = int(system_config[27])
            lcs_enable=int(system_config[28])


            if system_config[24]=='1':
                survey_period = 4096;
            elif system_config[25]=='1':
                survey_period = 2048;
            else:
                survey_period = 1024;

            burst_pulses = int(system_config[16:24],base=2)

            # print(gps_resets)
            survey_total = data[24] + pow(2,8)*data[25] + pow(2,16)*data[26] + pow(2,24)*data[27];
            E_total = data[28] + pow(2,8)*data[29] + pow(2,16)*data[30] + pow(2,24)*data[31];
            B_total = data[32] + pow(2,8)*data[33] + pow(2,16)*data[34] + pow(2,24)*data[35];
            LCS_total = data[36] + pow(2,8)*data[37] + pow(2,16)*data[38] + pow(2,24)*data[39];
            GPS_total = data[40] + pow(2,8)*data[41] + pow(2,16)*data[42] + pow(2,24)*data[43];
            status_total = data[44] + pow(2,8)*data[45] + pow(2,16)*data[46] + pow(2,24)*data[47];
            E_exp_num = data[51];
            B_exp_num = data[50];
            LCS_exp_num = data[49];
            GPS_exp_num = data[48];
            survey_exp_num = data[55];
            uptime = data[56]+ pow(2,8)*data[57] + pow(2,16)*data[58] + pow(2,24)*data[59]
            total_bytes_out = data[60] + pow(2,8)*data[61] + pow(2,16)*data[62] + pow(2,24)*data[63];
            bytes_in_memory = 4*(data[64] + pow(2,8)*data[65] + pow(2,16)*data[66] + pow(2,24)*data[67]);
            GPS_errors = data[68] + pow(2,8)*data[69];

            mem_percent_full = 100.*(bytes_in_memory)/(128.*1024*1024);

            # # Decode the burst command:
            # cfg = decode_burst_command(prev_burst_command)

            out_dict = dict()
            out_dict['header_timestamp'] = p['header_timestamp']
            out_dict['source'] = source
            out_dict['prev_command'] = prev_command
            out_dict['prev_bbr_command'] = prev_bbr_command
            out_dict['prev_burst_command'] = prev_burst_command
            out_dict['total_commands'] = total_commands
            out_dict['gps_resets'] = gps_resets
            out_dict['e_deployer_counter'] = e_deployer_counter
            out_dict['b_deployer_counter'] = b_deployer_counter
            out_dict['arm_e'] = arm_e
            out_dict['arm_b'] = arm_b
            out_dict['gps_enable'] = gps_enable
            out_dict['e_enable'] = e_enable
            out_dict['b_enable'] = b_enable
            out_dict['lcs_enable'] = lcs_enable
            out_dict['survey_period'] = survey_period
            out_dict['burst_pulses'] = burst_pulses
            out_dict['survey_total'] = survey_total
            out_dict['E_total'] = E_total
            out_dict['B_total'] = B_total
            out_dict['LCS_total'] = LCS_total
            out_dict['GPS_total'] = GPS_total
            out_dict['status_total'] = status_total
            out_dict['E_exp_num'] = E_exp_num
            out_dict['B_exp_num'] = B_exp_num
            out_dict['LCS_exp_num'] = LCS_exp_num
            out_dict['GPS_exp_num'] = GPS_exp_num
            out_dict['survey_exp_num'] = survey_exp_num
            out_dict['uptime'] = uptime
            out_dict['total_bytes_out'] = total_bytes_out
            out_dict['bytes_in_memory'] = bytes_in_memory
            out_dict['GPS_errors'] = GPS_errors
            out_dict['mem_percent_full'] = mem_percent_full

            out_dict['burst_config'] = decode_burst_command(prev_burst_command)
            out_dict['bbr_config'] = decode_uBBR_command(prev_bbr_command)

            # out_data.append(nice_str)
            out_data.append(out_dict)

        except:
            logger.warning(f'Failed to decode a status packet')
    return out_data

def print_status(data_list):
    ''' Prints a nicely-formatted status message, from a list of status dictionaries '''

    for d in data_list:
        
                    # Decode the burst command:
        cfg = decode_burst_command(d['prev_burst_command'])
        cmd_str = ""
        for k, v in cfg.items():
            if not "str" in k:
                cmd_str+= f"{k}={v}, "
        cmd_str = cmd_str[:-2]

        bbr = decode_uBBR_command(d['prev_bbr_command'])
        bbr_str = ""
        for k, v in bbr.items():
            bbr_str += f"{k}={v}, "
        bbr_str = bbr_str[:-2]

        nice_str = '---- System Status:  ----\n' +\
        'Packet received at:\t%s\n'%(datetime.datetime.utcfromtimestamp(d['header_timestamp'])) +\
        f"Source:\t\t\t{d['source']}\n" + \
        f"Uptime:\t\t\t{d['uptime']} Secs\n" +\
        f"Last Command:\t\t%s "%(''.join('{:02X} '.format(a) for a in d['prev_command'])) +\
        f" \t(%s)\n"%(''.join(str(chr(x)) for x in d['prev_command'])) +\
        f"Burst Command:\t\t%s "%(''.join('{:02X} '.format(a) for a in d['prev_burst_command'])) +\
        f" \t[%s]\n"%(''.join("|{0:8b}|".format(x) for x in d['prev_burst_command']).replace(' ','0')) +\
        "\t\t\t" + cmd_str + "\n" +\
        f"uBBR Command:\t\t%s "%(''.join('{:02X} '.format(a) for a in d['prev_bbr_command'])) +\
        f" \t[%s]\n"%(''.join("|{0:8b}|".format(x) for x in d['prev_bbr_command']).replace(' ','0')) +\
        "\t\t\t" + bbr_str + "\n" +\
        f"Total Commands:\t\t{d['total_commands']}\n" +\
        f"E channel enabled:\t{d['e_enable']}\n" +\
        f"B channel enabled:\t{d['b_enable']}\n" +\
        f"LCS enabled:\t\t{d['lcs_enable']}\n" +\
        f"GPS card enabled:\t{d['gps_enable']}\n"+\
        f"E antenna deploys:\t{d['e_deployer_counter']}\n" +\
        f"B antenna deploys:\t{d['b_deployer_counter']}\n" +\
        f"E deployer armed:\t{d['arm_e']}\n" +\
        f"B deployer armed:\t{d['arm_b']}\n" +\
        f"Survey period:\t\t{d['survey_period']}\n" +\
        f"Burst pulses:\t\t{d['burst_pulses']}\n" +\
        f"\nTotal Packets:\n" +\
        f"\tSurvey:\t\t{d['E_total']}\n" +\
        f"\tE burst:\t{d['E_total']}\n" +\
        f"\tB burst:\t{d['B_total']}\n" +\
        f"\tGPS burst:\t{d['GPS_total']}\n" +\
        f"\tStatus:\t\t{d['status_total']}\n" +\
        f"\tLCS:\t\t{d['LCS_total']}\n" +\
        f"Total transmitted data:\t{d['total_bytes_out']/1000} kb\n" +\
        f"Bytes in memory:\t{d['bytes_in_memory']/1000} kb\n" +\
        "Memory usage:\t\t{0:2.2f}%\n".format(d['mem_percent_full']) +\
        "\nCurrent experiment numbers:\n" +\
        f"\tSurvey:\t\t{d['survey_exp_num']}\n" +\
        f"\tE:\t\t{d['E_exp_num']}\n" +\
        f"\tB:\t\t{d['B_exp_num']}\n" +\
        f"\tGPS:\t\t{d['GPS_exp_num']}\n" +\
        f"\tLCS:\t\t{d['LCS_exp_num']}\n" +\
        f"\nGPS errors:\t\t{d['GPS_errors']}\n" +\
        f"GPS restart:\t\t{d['gps_resets']}\n"

        return nice_str
        # print(nice_str)
        # print('\n')

        # decode_uBBR_command(d['prev_bbr_command'])

def decode_burst_command(cmd):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Parses a three-byte command sequence from VPM; returns a dictionary
        stocked with various configuration parameters describing the burst.

    outputs:
        A dictionary containing:
            TD_FD_SELECT: 1 for time domain, 0 for frequency domain
            
            If time domain is selected:
                WINDOWING: 1 for time-axis windowing; 0 for just taking straight data
                WINDOW_MODE: configuration parameter describing the on/off duty cycle
                DECIMATE_ON: 1 to decimate data, 0 to record full 80kHz
                DECIMATION_MODE: A setting describing the downsampling factor
                DECIMATION_FACTOR: The decimation factor, e.g., downsample by 2, 4, 8, or 16x.
                SAMPLES_ON, SAMPLES_OFF: The number of samples to collect and to wait
            
            If frequency domain is selected:
                FFTS_ON, FFTS_OFF: The number of FFT columns to collect and to wait
                BINS: A string of 16 ones or zeros, corresponding to 16, uniformly-divided
                      bins along the frequency axis (nominally 512 bins, spanning 0 to 40 kHz).
                      A '1' enables data collection for this bin.
    '''
    logger = logging.getLogger(__name__ +'.decode_burst_command')


    logger.debug(f'decoding command: {cmd}')
    cmd_str = ''.join("{0:8b}".format(x) for x in cmd).replace(' ','0')
    
    if not cmd_str[0:2]=='01':
        logger.warning(f'invalid DPU command: {cmd}')

    burst_cmd = dict()
    burst_cmd['str'] = cmd_str
    burst_cmd['TD_FD_SELECT'] = int(cmd_str[2])
    burst_cmd['WINDOWING'] = int(cmd_str[3])
    burst_cmd['WINDOW_MODE'] = int(cmd_str[4:8],2)
    burst_cmd['DECIMATE_ON'] = int(cmd_str[8])
    burst_cmd['DECIMATION_MODE'] = int(cmd_str[9:11],2)
    burst_cmd['BINS'] = cmd_str[8:24];


    # Generate derived parameters:
    # Table of samples on and off, for time and frequency domain
    td_samples_on_vec  = np.array([10, 10, 10, 10,  5,  5, 5, 5,  2,  2, 2, 2,  1,  1, 1, 1])*80000;
    td_samples_off_vec = np.array([30, 10,  5,  2, 30, 10, 5, 2, 30, 10, 5, 2, 30, 10, 5, 2])*80000;
    fd_samples_on_vec  = np.array([1563, 1563, 1563, 1563,  782,  782, 782, 782,  313,  313, 313, 313,  157,  157, 157, 157])
    fd_samples_off_vec = np.array([4688, 1563,  782,  313, 4688, 1563, 782, 313, 4688, 1563, 782, 313, 4688, 1563, 782, 313]) 
    decimation_factors = np.array([2, 4, 8, 16])

    if burst_cmd['TD_FD_SELECT']==1:
        # Time-domain burst
        if burst_cmd['WINDOWING'] == 1:
            burst_cmd['SAMPLES_ON']  = td_samples_on_vec[burst_cmd['WINDOW_MODE']]
            burst_cmd['SAMPLES_OFF'] = td_samples_off_vec[burst_cmd['WINDOW_MODE']]
        else:
            burst_cmd['SAMPLES_ON'] = 30*80000;
            burst_cmd['SAMPLES_OFF'] = 0;

        if burst_cmd['DECIMATE_ON'] ==1:
            burst_cmd['DECIMATION_FACTOR'] = decimation_factors[burst_cmd['DECIMATION_MODE']]

    if burst_cmd['TD_FD_SELECT'] ==0:
        # Frequency-domain burst
        if burst_cmd['WINDOWING'] == 1:
            burst_cmd['FFTS_ON']  = fd_samples_on_vec[burst_cmd['WINDOW_MODE']]
            burst_cmd['FFTS_OFF'] = fd_samples_off_vec[burst_cmd['WINDOW_MODE']]
        else:
            burst_cmd['FFTS_ON'] = 4688;
            burst_cmd['FFTS_OFF']= 0;

    return burst_cmd;

def generate_burst_command(burst_config):
    # The inverse. Pass in a burst configuration, get an appropriate command!
    cmd_str = np.zeros(24, dtype='uint8')

    cmd_str[0:2] = [0,1]
    cmd_str[2] = burst_config['TD_FD_SELECT']


    cmd_str[3]    = burst_config['WINDOWING']
    cmd_str[4:8]  = burst_config['WINDOW_MODE']
    cmd_str[8]    = burst_config['DECIMATE_ON']

    
    if burst_config['TD_FD_SELECT'] == 1:
        cmd_str[9:11] = burst_config['DECIMATION_MODE']
    else:
        cmd_str[8:24] = [int(x) for x in burst_config['BINS']]

    cmd_str = cmd_str.tobytes()

    return(cmd_str) 

def decode_uBBR_command(cmd):
    '''decode commands sent to the uBBR (passed as 3 uint8s)'''
    
    logger = logging.getLogger(__name__ +'.decode_uBBR_command')

    cmd_str = ''.join("{0:8b}".format(x) for x in cmd).replace(' ','0')[::-1]
    
    if len(cmd_str)!=24:
        logger.warning("invalid uBBR command length")
    if not (cmd_str[23]=='1' and cmd_str[22] == '0'):
        logger.warning("invalid uBBR header")

    out = dict()
    parms = ['E_FILT','B_FILT','E_CAL','B_CAL','E_PRE','B_PRE','E_RST','B_RST','E_GAIN','B_GAIN','CALTONE','SIG_GEN','TONETYPE']
    inds  = [21,      20,      19,     18,     17,      16,     15,    14,     13,       12,     11,       10,       9 ]

    out['TONESTEP'] = int(cmd_str[1:9],2)  # Pretty sure byte zero is unused...
    for parm, ind in zip(parms,inds):
        out[parm] = int(cmd_str[ind])    
    
    return out

def find_sequence(arr,seq):
    '''
    Find any instances of a sequence seq in 1d array arr.
    Returns an array of indexes corresponding to the first value in the sequence.
    '''
    # Store sizes of input array and sequence
    Na, Nseq = arr.size, seq.size
    # Range of sequence
    r_seq = np.arange(Nseq)
    # Create a 2D array of sliding indices across the entire length of input array.
    # Match up with the input sequence & get the matching starting indices.
    M = (arr[np.arange(Na-Nseq+1)[:,None] + r_seq] == seq).all(1)
    inds = np.where(M)[0]
    return(inds)

def decode_packets_TLM(data_root, fname):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.10.2019
    Description:
        Parses a raw byte string from VPM; locates packets and calculates
        checksums; unescapes 7E/7D characters; decodes various metadata.
    inputs: 
        data_root:          Root directory of the data file
        fname:              file name to load. Should end with .TLM
    outputs:
        a list of decoded packets:
        Each packet is a dictionary with the following fields:
        packet_data:        2d array of packet data (num_packets x data_segment_length)
        packet_start_index: Start index of the current data segment
        datatype:           Channel label. (Ascii 'S','E','B','L','G','I')
        experiment_number:  indicates the experiment to which packets belong to
        bytecounts:         length of actual data within packet_data
                            (i.e., when reassembling, place the current packet_data at
                            [packet_start_index(i):packet_start_index(i) + bytecounts(i)]
        packet_lengths:     length of each packet, including headers, but after escaping
        verify:             received checksum - calculated checksum.
                            Should be all zeros unless we have some corruption happening.
    '''
    logger = logging.getLogger(__name__ + '.decode_packets_TLM')

    logger.info(f'Loading file {fname}')
    fpath = os.path.join(data_root, fname)
    with open(fpath,'rb') as f:
        data = np.fromfile(f,dtype='uint8')

    # Packet indices and lengths (set in payload firmware)
    PACKET_SIZE = 512
    DATA_SEGMENT_LENGTH = PACKET_SIZE - 8
    PACKET_COUNT_INDEX = 1
    DATA_TYPE_INDEX = 5
    EXPERIMENT_INDEX = 6
    DATA_START_INDEX = 7
    DATA_END_INDEX = DATA_START_INDEX + DATA_SEGMENT_LENGTH
    CHECKSUM_INDEX = PACKET_SIZE - 2

    CCSDS_HEADER_LEN = 26

    leap_seconds = 18  # GPS time does not account for leap seconds; as of ~2019, GPS leads UTC by 18 seconds.
    reference_date = datetime.datetime(1980,1,6,0,0, tzinfo=datetime.timezone.utc) - datetime.timedelta(seconds=leap_seconds)


    # Find all packet start indices
    p_inds_pre_escape = np.array(sorted(np.where(data==0x7E)))
    p_length_pre_escape = np.diff(p_inds_pre_escape)

    # Select only the valid packet start indices
    p_start_inds = p_inds_pre_escape[np.where(p_length_pre_escape == (PACKET_SIZE - 1))]
    logger.info(f"found {len(p_start_inds)} valid packets")
    # Escape characters, and move packets into a list (since their length now varies)
    packets = [];
    checksum_failure_counter = 0

    # for k in np.arange(-6, 20):
    for x, pind in enumerate(p_start_inds):
        try:
            cur_packet = np.copy(data[pind:pind+PACKET_SIZE].astype('uint8'))
            # cur_packet   = data[pind:pind+PACKET_SIZE]
            ccsds_header = np.copy(data[pind-CCSDS_HEADER_LEN:pind]).astype('uint8')
            # print(['{0:X}'.format(x) for x in data[pind:pind + EXPERIMENT_INDEX + 3]])

            # grab data from the CTCSS header
            C_packet_length = struct.unpack('>I', ccsds_header[0:4].tobytes())[0] # 534
            C_component_ID  = struct.unpack('>B', ccsds_header[5:6].tobytes())[0] # 34
            C_interface_ID  = struct.unpack('>B', ccsds_header[6:7].tobytes())[0] # 1
            C_message_ID    = struct.unpack('>B', ccsds_header[7:8].tobytes())[0] # 2
            C_epoch_seconds = struct.unpack('>I', ccsds_header[8:12].tobytes())[0]
            C_nanoseconds   = struct.unpack('>I', ccsds_header[12:16].tobytes())[0]
            C_reboot_count  = struct.unpack('>H', ccsds_header[16:18].tobytes())[0]


            # Check if the bytecount or checksum fields were escaped
            check_escaped = (cur_packet[PACKET_SIZE - 2]!=0)*1
            count_escaped = (cur_packet[PACKET_SIZE - 4]!=0)*1

            # Calculate the checksum (on the unescaped data):
            checksum_calc = sum(cur_packet[2:CHECKSUM_INDEX - 1])%256

            # Un-escape the packet (Destructive)
            esc1_inds = find_sequence(cur_packet,np.array([0x7D, 0x5E])) # [7D, 5E] -> 7E
            cur_packet[esc1_inds] =  0x7E
            cur_packet = np.delete(cur_packet, esc1_inds + 1) 
            esc2_inds = find_sequence(cur_packet,np.array([0x7D, 0x5D])) # [7D, 5D] -> 7D
            cur_packet = np.delete(cur_packet, esc2_inds + 1)


            # Get the new indices of the checksum and bytecount fields
            packet_length_post_escape = len(cur_packet)
            checksum_index = packet_length_post_escape + check_escaped - 3
            bytecount_index= packet_length_post_escape + check_escaped + count_escaped - 6
     
            # Decode metadata fields
            packet_start_index = struct.unpack('>L',cur_packet[PACKET_COUNT_INDEX:(PACKET_COUNT_INDEX + 4)])[0]

            datatype = chr(cur_packet[DATA_TYPE_INDEX]) # works!
            experiment_number = cur_packet[EXPERIMENT_INDEX]
            # print(experiment_number)
            # bytecount = 256*cur_packet[bytecount_index] + cur_packet[bytecount_index + 1]
            bytecount = struct.unpack('>H', cur_packet[bytecount_index:(bytecount_index + 2)])[0]

            checksum = cur_packet[checksum_index]

            if (checksum - checksum_calc) != 0:
                checksum_failure_counter += 1
                logger.warning('invalid checksum at packet # %d -- skipping'%x)
                continue
            # Pack the decoded packet into a dictionary, and add it to the list
            # (maybe there's a nicer data structure for this - but this is probably the most general case)
            p = dict()
            p['data'] = np.array(cur_packet[DATA_START_INDEX:(bytecount + DATA_START_INDEX)], dtype='uint8').tolist()
            p['start_ind'] = packet_start_index
            p['dtype'] = datatype
            p['exp_num'] = experiment_number
            p['bytecount'] = bytecount
            p['checksum_verify'] = (checksum - checksum_calc)==0
            p['packet_length'] = packet_length_post_escape
            p['fname'] = fname
            p['header_ns'] = C_nanoseconds
            p['header_epoch_sec'] = C_epoch_seconds
            p['header_reboots'] = C_reboot_count
            p['header_timestamp'] = (reference_date + datetime.timedelta(seconds=C_epoch_seconds + C_nanoseconds*1e-9)).timestamp()
                
            packets.append(p)


        except:
            logger.warning('exception at packet # %d',x)
        
    if checksum_failure_counter > 0:
        logger.warning(f'--------------- {checksum_failure_counter} failed checksums ---------------')

    logger.info(f'decoded {len(packets)} packets')

    return packets

def decode_packets_CSV(data_root, filename):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.1
        Date    6.12.2020
        - Modified to detect delimiter and to be more robust against header row weirdness
    Version:    1.0
        Date:   2.25.2020
    Description:
        Parses data from VPM, stored in a .CSV file
        (e.g., the KSat file format)

    '''
    logger = logging.getLogger(__name__ + '.decode_packets_CSV')

    fpath = os.path.join(data_root, filename)
    
    with open(fpath) as csvfile:
        # cur = csvfile.read().split('\n')
        cur = csvfile.readlines()

    # Find the header row
    for header_index, line in enumerate(cur):
        if 'TARGET' in line:
            header_line = line
            break
    logger.debug(f'Header index: {header_index}')            

    # Detect the delimeter -- either comma or tab so far
    delimeters = [',',' ','\t']
    for delimeter in delimeters:

        counts = header_line.count(delimeter)
        logger.debug(f'Delimter: " {delimeter}" counts: {counts}')

        # header_string = str(header_line).split()
        
        if counts>3:
            logger.info(f'using delimeter "{delimeter}"')
            header_string = header_line.split(delimeter)
            break
    logger.debug(f'Header string: {header_string}')

    with open(fpath) as csvfile:
        # Skip up to the header row:
        for i in range(header_index):
            csvfile.readline()
        
        # Read the remaining entries into dicts
        reader = csv.DictReader(csvfile, delimiter=delimeter)
        
        # Parse the entry list, grab data and timestamp
        timestamps = []
        raw_data = []
        for row in reader:
            try:
                if ('VPM' in row['TARGET']) and row['PACKET'] == 'PAYLOAD_INTERFACE_RECEIVE_RAW_PAYLOAD_DATA':
                    timestamps.append(row['UTC_TIME'])
                    raw_data.append(bytes.fromhex(row['DYNAMIC_DATA']))
            except:
                logger.info(f'skipped CSV line: {row}')

    # Packet indices and lengths (set in payload firmware)
    PACKET_SIZE = 512
    DATA_SEGMENT_LENGTH = PACKET_SIZE - 8
    PACKET_COUNT_INDEX = 1
    DATA_TYPE_INDEX = 5
    EXPERIMENT_INDEX = 6
    DATA_START_INDEX = 7
    DATA_END_INDEX = DATA_START_INDEX + DATA_SEGMENT_LENGTH
    CHECKSUM_INDEX = PACKET_SIZE - 2

    # Escape characters, and move packets into a list (since their length now varies)
    packets = [];
    checksum_failure_counter = 0
    logger.info(f'Received {len(timestamps)} packets')
    for ind, (timestamp, p_data) in enumerate(zip(timestamps, raw_data)):
        try:
            cur_packet = np.array([int(x) for x in p_data], dtype='uint8')
            p_inds = np.array(sorted(np.where(cur_packet==0x7E)))
            cur_packet = np.copy(cur_packet[p_inds[0][0]:(p_inds[0][1] + 1)])

            # Check if the bytecount or checksum fields were escaped
            check_escaped = (cur_packet[PACKET_SIZE - 2]!=0)*1
            count_escaped = (cur_packet[PACKET_SIZE - 4]!=0)*1

            # Calculate the checksum (on the unescaped data):
            checksum_calc = sum(cur_packet[2:CHECKSUM_INDEX - 1])%256

            # Un-escape the packet (Destructive)
            esc1_inds = find_sequence(cur_packet,np.array([0x7D, 0x5E])) # [7D, 5E] -> 7E
            cur_packet[esc1_inds] =  0x7E
            cur_packet = np.delete(cur_packet, esc1_inds + 1) 
            esc2_inds = find_sequence(cur_packet,np.array([0x7D, 0x5D])) # [7D, 5D] -> 7D
            cur_packet = np.delete(cur_packet, esc2_inds + 1)


            # Get the new indices of the checksum and bytecount fields
            packet_length_post_escape = len(cur_packet)
            checksum_index = packet_length_post_escape + check_escaped - 3
            bytecount_index= packet_length_post_escape + check_escaped + count_escaped - 6

            # Decode metadata fields
            packet_start_index = struct.unpack('>L',cur_packet[PACKET_COUNT_INDEX:(PACKET_COUNT_INDEX + 4)])[0]

            datatype = chr(cur_packet[DATA_TYPE_INDEX]) # works!
            experiment_number = cur_packet[EXPERIMENT_INDEX]
            bytecount = struct.unpack('>H', cur_packet[bytecount_index:(bytecount_index + 2)])[0]
            checksum = cur_packet[checksum_index]

            if (checksum - checksum_calc) != 0:
                checksum_failure_counter += 1
                logger.warning('invalid checksum at packet # %d -- skipping'%ind)
                continue


            # Pack the decoded packet into a dictionary, and add it to the list
            # (maybe there's a nicer data structure for this - but this is probably the most general case)
            p = dict()
            p['data'] = np.array(cur_packet[DATA_START_INDEX:(bytecount + DATA_START_INDEX)], dtype='uint8').tolist()
            p['start_ind'] = packet_start_index
            p['dtype'] = datatype
            p['exp_num'] = experiment_number
            p['bytecount'] = bytecount
            p['checksum_verify'] = (checksum - checksum_calc)==0
            p['packet_length'] = packet_length_post_escape
            p['fname'] = filename
            p['header_timestamp'] = datetime.datetime.fromisoformat(timestamp[0:-1]).replace(tzinfo=datetime.timezone.utc).timestamp()
            p['file_index'] = ind # Order of arrival in file 
            packets.append(p)
        except:
            logger.warning('exception at packet # %d',ind)
        
    if checksum_failure_counter > 0:
        logger.warning(f'--------------- {checksum_failure_counter} failed checksums ---------------')

    logger.info(f'decoded {len(packets)} packets')

    return packets

def remove_trailing_nans(arr1d):
    ''' Trims off the trailing NaNs of a vector.'''
    notnans = np.flatnonzero(~np.isnan(arr1d))
    if notnans.size:
        # Trim leading and trailing:
        # trimmed = arr1d[notnans[0]: notnans[-1]+1]  # slice from first not-nan to the last one
        # Trim trailing only
        trimmed = arr1d[0:notnans[-1]+1]  # slice from first not-nan to the last one
    else:
        trimmed = np.zeros(0)

        
    return trimmed

def TD_reassemble(vec):
    ''' Rearranges a byte string into 16-bit values (packed as a double),
     following time-domain interleaving'''
    
    re = vec[:len(vec) - (len(vec)%4)].astype('uint8')
    re = np.reshape(re, [int(len(re)/4),4])
    re = np.stack([(re[:,0] + 256*re[:,1]).astype('int16'), (re[:,2] + 256*re[:,3]).astype('int16')],axis=1)
    re = re.ravel().astype('float')

    # Mark off any nans in the output vector
    out_nan_inds = np.unique(np.floor(np.where(np.isnan(vec))[0]/2).astype('int'))
    re[out_nan_inds] = np.nan

    # Returns floats, even though our data is 16-bit ints... but this keeps the 'nan' flags present.
    return re

def FD_reassemble(vec):
    ''' Rearranges a byte string into 16-bit values (packed as a complex double),
    following time-domain interleaving.
    Untested as of 10/11/2019, but follows the Matlab code! I need some FD data to try it with.

    Added nan mask 10/31/2019, also untested
    '''
    re = vec[:len(vec) - (len(vec)%4)].astype('uint8')
    re = np.reshape(re, [int(len(re)/4),4])
    re = np.stack([(re[:,0] + 256*re[:,1]).astype('int16'), (re[:,2] + 256*re[:,3]).astype('int16')],axis=1)

    re = re[:,0].astype('float') + 1j*re[:,1].astype('float')

    # Mark off any nans in the output vector.
    out_nan_inds = np.unique(np.floor(np.where(np.isnan(vec))[0]/4).astype('int'))
    re[out_nan_inds] = np.nan

    return re

def decode_burst_data_by_experiment_number(packets, burst_cmd = None, burst_pulses=None):
    ''' Decode bursts by grouping packets by experiment number.
        The burst command is echoed in each GPS packet; the number of repeats
        is decoded by counting GPS packets.

        This method is the way things should work ideally -- however, it will
        fail on bursts without GPS data, either from dropped packets or the GPS
        card being turned off, and may cause problems if the payload has been
        reset between two adjacent bursts, resulting in two bursts with experiment
        number 0.
    '''
    logger = logging.getLogger(__name__+'.decode_burst_data_by_experiment_number')

    # Select burst packets
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    
    # Get all unique experiment numbers for this set of packets 
    # (chances are real good that we'll only have 1 or 2 unique numbers)
    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])
    logger.info(f"available burst experiment numbers: {avail_exp_nums}")

    completed_bursts = []

    if (burst_cmd is not None) and (len(burst_cmd) > 0 ) and (burst_cmd is not "burst command"):
        logger.info(f'Using manually-provided burst command {burst_cmd}')
        # Use externally-provided burst command, if present
        burst_config = decode_burst_command(burst_cmd)
        burst_config['burst_pulses'] = burst_pulses
    else:
        burst_config = None

    for e_num in avail_exp_nums:
        logger.info(f"processing experiment number {e_num}")
        filt_inds = [p['exp_num']==e_num for p in burst_packets]
        current_packets = list(itertools.compress(burst_packets, filt_inds))
        cur_G_packets   = list(filter(lambda p: p['dtype']=='G', current_packets))
        header_timestamps = sorted([p['header_timestamp'] for p in current_packets])

        # # The burst command is echoed at the top of each GPS packet, if we have any
        # if (burst_config is None) and cur_G_packets:
        #     for gg in cur_G_packets:
        #         if gg['start_ind'] ==0:
        #             cmd_gps = np.flip(gg['data'][0:3])

        #     # Get burst configuration parameters:
        #     logger.info(f'Found burst command {cmd_gps} in GPS packet')
        #     burst_config = decode_burst_command(cmd_gps)
        #     burst_config['burst_pulses'] = burst_pulses

            
        processed = process_burst(current_packets, burst_config)
        processed['header_timestamp'] = header_timestamps[0]
        processed['experiment_number'] = e_num
        completed_bursts.append(processed)
        burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
        logger.info(f"{len(burst_packets)} packets remaining")
    unused_packets = burst_packets
    logger.info(f"returning {len(burst_packets)} unused burst packets")
    return completed_bursts, unused_packets

def decode_burst_data_in_range(packets, ta, tb, burst_cmd = None, burst_pulses = None):
    ''' decode burst data between a given time interval, with a given command.
        Use this in the event that we want to decode an incomplete burst.
    '''
    logger = logging.getLogger(__name__ +'.decode_burst_data_in_range')
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    header_timestamps = ([p['header_timestamp'] for p in burst_packets])


    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])
    logger.debug(f'Available burst experiment numbers: {avail_exp_nums}')

    completed_bursts = []

    min_timestamp = min(header_timestamps)
    max_timestamp = max(header_timestamps)
    logger.info(f'packet timestamps range betwen {datetime.datetime.utcfromtimestamp(min_timestamp)} and {datetime.datetime.utcfromtimestamp(max_timestamp)}')

    if burst_cmd is not None:
        # Use externally-provided burst command, if present
        burst_config = decode_burst_command(burst_cmd)
        burst_config['burst_pulses'] = burst_pulses
    else:
        burst_config = None

    for e_num in avail_exp_nums:
        logger.info(f"processing experiment number {e_num}")

        filt_inds = [p['header_timestamp'] >= ta and p['header_timestamp'] <= tb for p in burst_packets]
        current_packets = list(itertools.compress(burst_packets, filt_inds))
        header_timestamps = sorted([p['header_timestamp'] for p in current_packets])

        if len(current_packets) > 100:
            logger.info(f'------ exp num {e_num} ------')
            logger.info(f"processing burst betweeen times: {datetime.datetime.utcfromtimestamp(ta),datetime.datetime.utcfromtimestamp(tb)}")


            processed = process_burst(current_packets, burst_config)

            processed['ta'] = ta
            processed['tb'] = tb
            processed['header_timestamp'] = header_timestamps[0]
            processed['experiment_number'] = e_num

            completed_bursts.append(processed)
            burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
            logger.info(f"{len(burst_packets)} packets remaining")

    unused_packets = burst_packets    
    logger.info(f"returning {len(burst_packets)} unused burst packets")
    return completed_bursts, unused_packets

def decode_burst_data_between_status_packets(packets):
    ''' Decode burst data by sorting packets by arrival time, and binning bursts
        between two status packets. 
    '''

    logger = logging.getLogger(__name__ +'.decode_burst_data_between_status_packets')

    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    I_packets     = sorted(I_packets, key = lambda p: p['header_timestamp'])
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    # stats = decode_status(I_packets)


    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])
    logging.info(f"exp nums in dataset: {avail_exp_nums}")
    completed_bursts = []

    status_times = np.array(sorted([IP['header_timestamp'] for IP in I_packets]))

    # We should have a status message at the beginning and end of each burst.
    # Add 1 second padding on either side for good measure.
    logger.info(f'I_packets has length {len(I_packets)} pre-sift')
    for IA, IB in zip(I_packets[0:-1], I_packets[1:]):
        ta = IA['header_timestamp'] - 1.5
        tb = IB['header_timestamp'] + 1.5
        logger.info(f"{ta}, {tb}")
        
        # Confirm that the burst command is the same within each status packet:        
        IA_cmd = np.flip(IA['data'][12:15])
        IB_cmd = np.flip(IB['data'][12:15])

        # Skip any pairs with different burst commands
        if any(IA_cmd != IB_cmd):
            continue

        # (At this point, there will be only one available experiment number)
        for e_num in avail_exp_nums:
            filt_inds = [p['header_timestamp'] >= ta and p['header_timestamp'] <= tb for p in burst_packets]
            packets_in_time_range = list(itertools.compress(burst_packets, filt_inds))


            packets_with_matching_e_num = list(filter(lambda p: p['exp_num']==e_num, burst_packets))
            logger.info(f"packets in time range: {len(packets_in_time_range)}; packets with exp_num {e_num}: {len(packets_with_matching_e_num)}")

            if len(packets_in_time_range) > 100:
                logger.info(f'------ exp num {e_num} ------')
                logger.info(f"status packet times: {datetime.datetime.utcfromtimestamp(ta),datetime.datetime.utcfromtimestamp(tb)}")


                # Ok! Now we have a list of packets, all with a common experiment number, 
                # in between two status packets, each with have the same burst command.
                # Ideally, this should be a complete set of burst data. Let's try processing it!
                
                # The burst command is echoed at the top of each GPS packet; we're using the
                # command listed in the status packet, but let's confirm it matches.
                for gg in filter(lambda packet: packet['dtype'] == 'G', packets_in_time_range):
                    if gg['start_ind'] ==0:
                        cmd_gps = np.flip(gg['data'][0:3])
                        logger.debug(cmd_gps)
                        if (IA_cmd != cmd_gps).any():
                            logger.warning("GPS and status command echo mismatch")

                # Get burst configuration parameters:
                cmd = np.flip(IA['data'][12:15])
                burst_config = decode_burst_command(cmd)
                
                # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
                system_config = np.flip(IA['data'][20:24])
                system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
                burst_config['burst_pulses'] = int(system_config[16:24],base=2)

                logger.info(burst_config)

                processed = process_burst(packets_in_time_range, burst_config)
                # processed['I'] = [IA, IB]
                processed['status'] = decode_status([IA, IB])
                processed['bbr_config'] = decode_uBBR_command(processed['status'][0]['prev_bbr_command'])
                processed['header_timestamp'] = ta
                processed['experiment_number'] = e_num
                
                completed_bursts.append(processed)

                
                # Remove processed packets from data_dict
                burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
                I_packets.remove(IA)
                I_packets.remove(IB)

            logger.info(f"{len(burst_packets)} packets remaining")

    unused_packets = burst_packets + I_packets
    logger.info(f"returning {len(unused_packets)} unused burst packets")    
    return completed_bursts, unused_packets



def decode_burst_data_by_trailing_status_packet(packets):
    ''' Decode burst data by sorting packets by arrival time, and binning bursts
        within a time window preceeding a status packet
    '''

    logger = logging.getLogger(__name__)

    I_packets     = list(filter(lambda p: (p['dtype'] == 'I' and chr(p['data'][3])=='B'), packets))
    I_packets     = sorted(I_packets, key = lambda p: p['header_timestamp'])
    burst_packets = list(filter(lambda packet: packet['dtype'] in ['E','B','G'], packets))
    burst_packets = sorted(burst_packets, key = lambda p: p['header_timestamp'])
    # stats = decode_status(I_packets)


    avail_exp_nums = np.unique([x['exp_num'] for x in burst_packets])
    logging.info(f"exp nums in dataset: {avail_exp_nums}")
    completed_bursts = []

    status_times = np.array(sorted([IP['header_timestamp'] for IP in I_packets]))

    # We should have a status message at the beginning and end of each burst.
    # Add 1 second padding on either side for good measure.
    logger.info(f'I_packets has length {len(I_packets)} pre-sift')
    for IB in I_packets:
        ta = IB['header_timestamp'] - 2*3600
        tb = IB['header_timestamp'] + 1.5
        logger.info(f"{ta}, {tb}")
        
        # Confirm that the burst command is the same within each status packet:        
        IB_cmd = np.flip(IB['data'][12:15])


        # (At this point, there will be only one available experiment number)
        for e_num in avail_exp_nums:
            filt_inds = [p['header_timestamp'] >= ta and p['header_timestamp'] <= tb for p in burst_packets]
            packets_in_time_range = list(itertools.compress(burst_packets, filt_inds))


            packets_with_matching_e_num = list(filter(lambda p: p['exp_num']==e_num, burst_packets))
            logger.info(f"packets in time range: {len(packets_in_time_range)}; packets with exp_num {e_num}: {len(packets_with_matching_e_num)}")

            if len(packets_in_time_range) > 100:
                logger.info(f'------ exp num {e_num} ------')
                logger.info(f"status packet times: {datetime.datetime.fromtimestamp(ta),datetime.datetime.fromtimestamp(tb)}")


                # Ok! Now we have a list of packets, all with a common experiment number, 
                # in between two status packets, each with have the same burst command.
                # Ideally, this should be a complete set of burst data. Let's try processing it!
                
                # The burst command is echoed at the top of each GPS packet; we're using the
                # command listed in the status packet, but let's confirm it matches.
                for gg in filter(lambda packet: packet['dtype'] == 'G', packets_in_time_range):
                    if gg['start_ind'] ==0:
                        cmd_gps = np.flip(gg['data'][0:3])
                        logger.debug(cmd_gps)
                        if (IB_cmd != cmd_gps).any():
                            logger.warning("GPS and status command echo mismatch")

                # Get burst configuration parameters:
                burst_config = decode_burst_command(IB_cmd)
                
                # Get burst nPulses -- this is the one key parameter that isn't defined by the burst command...
                system_config = np.flip(IB['data'][20:24])
                system_config = ''.join("{0:8b}".format(a) for a in system_config).replace(' ','0')
                burst_config['burst_pulses'] = int(system_config[16:24],base=2)

                logger.info(burst_config)

                processed = process_burst(packets_in_time_range, burst_config)
                # processed['I'] = [IA, IB]
                processed['status'] = decode_status([IB])
                processed['bbr_config'] = decode_uBBR_command(processed['status'][0]['prev_bbr_command'])
                processed['header_timestamp'] = ta
                processed['experiment_number'] = e_num
                
                completed_bursts.append(processed)

                
                # Remove processed packets from data_dict
                burst_packets = list(itertools.compress(burst_packets, np.logical_not(filt_inds)))
                I_packets.remove(IB)

            logger.info(f"{len(burst_packets)} packets remaining")

    unused_packets = burst_packets + I_packets
    logger.info(f"returning {len(unused_packets)} unused burst packets")    
    return completed_bursts, unused_packets

def process_burst(packets, burst_config=None):
    ''' Reassemble burst data, according to info in burst_config.
        This assumes the set of packets is complete, and belongs to the
        same burst.

        This is the internal helper function called by the other "Decode burst" methods.
    '''

    logger = logging.getLogger(__name__ +'.process_burst')

    # Sort the packets by data stream:
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))



    # Loop through all packets to get the maximum data index:    
    if E_packets:
        max_E_ind = max([p['start_ind'] + p['bytecount'] for p in E_packets])
    else: max_E_ind = 0
    if B_packets:
        max_B_ind = max([p['start_ind'] + p['bytecount'] for p in B_packets])
    else: max_B_ind = 0
    if G_packets:
        max_G_ind = max([p['start_ind'] + p['bytecount'] for p in G_packets])
    else: max_G_ind = 0

    E_data = np.zeros(max_E_ind)*np.nan
    B_data = np.zeros(max_B_ind)*np.nan
    G_data = np.zeros(max_G_ind)*np.nan

    logger.debug(f'Max E ind: {max_E_ind}  Max B ind: {max_B_ind}, Max G ind: {max_G_ind}')
    logger.info("reassembling E")
    for p in E_packets:
        E_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    logger.info("reassembling B")
    for p in B_packets:
        B_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']

    logger.info("reassembling GPS")
    for p in G_packets:
        G_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']


    # Decode any GPS data we might have
    G = decode_GPS_data(G_data)

    if burst_config is None:
        # If no burst configuration has been passed, find it in the data
        # Burst command is echo'ed at the top of each GPS packet:
        gps_echoed_cmds = []

        for g in G_packets:
            if g['start_ind'] == 0:
                cmd = np.flip(g['data'][0:3])
                gps_echoed_cmds.append(cmd)
        if gps_echoed_cmds:
            # Check that they're all the same, if we have more entries...
            cmd = gps_echoed_cmds[0]
            logger.info(f'Recovered command {cmd} from GPS packets')
            burst_config = decode_burst_command(cmd)
        else:
            logger.warning("no GPS packets found; cannot determine burst command")                
            return dict()

        # One GPS entry per pulse
        burst_config['burst_pulses'] = len(G)
        logger.info(burst_config)

    # ------- Calculate n_samples -------
    # This isn't really used here anymore! All we need to know in here is time domain or frequency domain...
    if burst_config['TD_FD_SELECT']==1:
        SAMPLES_TO_IGNORE = 105;
        # Initialize for time domain
        n_samples = burst_config['SAMPLES_ON']*burst_config['burst_pulses'] # how many 8-bit values should we get?
        if burst_config['DECIMATE_ON']==1:
            # (Not sure about this)
            n_samples = n_samples/burst_config['DECIMATION_FACTOR']
            n_samples -= np.floor(SAMPLES_TO_IGNORE/burst_config['DECIMATION_FACTOR']) + burst_config['DECIMATION_FACTOR'] - 1
            
    elif burst_config['TD_FD_SELECT']==0:
        # Initialize for frequency domain
        seg_length = 32 # number of FFTs within each bin
        logger.info(f"seg length: {seg_length}")
        n_samples = int(2*(burst_config['FFTS_ON'])*2*seg_length*burst_config['BINS'].count('1'))

    # Juggle the 8-bit values around
    if burst_config['TD_FD_SELECT']==1:
        logger.info("Selected time domain")
        E = TD_reassemble(E_data)
        B = TD_reassemble(B_data)

    if burst_config['TD_FD_SELECT']==0:
        logger.info("seleced frequency domain")
        E = FD_reassemble(E_data)
        B = FD_reassemble(B_data)

    logger.debug(f'Reassembled E has length {len(E)}, with {np.sum(np.isnan(E)):,d} nans. Raw E missing {np.sum(np.isnan(E_data)):,d} values.')
    logger.debug(f'Reassembled B has length {len(B)}, with {np.sum(np.isnan(B)):,d} nans. Raw B missing {np.sum(np.isnan(B_data)):,d} values.')
    logger.debug(f'expected {int(n_samples)} samples')

    if len(E)!=int(n_samples):
        logger.warning("E data size is an unexpected size -- possible missing packets or mismatched data")
        logger.warning(f'Reassembled E has length {len(E)}, with {np.sum(np.isnan(E))} nans. Raw E missing {np.sum(np.isnan(E_data))} values. Expected {int(n_samples)} samples')

    if len(B)!=int(n_samples):
        logger.warning("B data size is an unexpected size -- possible missing packets or mismatched data")
        logger.warning(f'Reassembled B has length {len(B)}, with {np.sum(np.isnan(B))} nans. Raw B missing {np.sum(np.isnan(B_data))} values. Expected {int(n_samples)} samples')

    outs = dict()
    outs['E'] = E
    outs['B'] = B
    outs['G'] = G
    outs['config'] = burst_config

    return outs

def decode_GPS_data(data):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.15.2019
    Description:
        Decodes GPS data from the Novatel OEM6/7 cards, and returns a dictionary of parameters

    inputs: 
        data: A numpy array with type 'uint8'; the reassembled 
    outputs:
        A Python dictionary
        Each dictionary is a single survey column, and contains the following fields:
            E_data: The electric field data, corresponding to averaged, log-scaled
                    magnitudes of the onboard FFT
            B_data: The magnetic field data, corresponding to averaged, log-scaled
                    magnitudes of the onboard FFT
            GPS:    A dictionary of decoded GPS data, corresponding to the end of
                    the current survey product
    '''

    logger = logging.getLogger(__name__ +'.decode_GPS_data')

    # GPS time is delivered as: weeks from reference date, plus seconds into the week.
    leap_seconds = 18  # GPS time does not account for leap seconds; as of ~2019, GPS leads UTC by 18 seconds.
    reference_date = datetime.datetime(1980,1,6,0,0, tzinfo=datetime.timezone.utc) - datetime.timedelta(seconds=leap_seconds)
    pos_inds = find_sequence(data,np.array([0xAA, 0x44, 0x12, 0x1C, 0x2A]))
    vel_inds = find_sequence(data,np.array([0xAA, 0x44, 0x12, 0x1C, 0x63]))

    if len(pos_inds)==0 and len(vel_inds)==0:
        logger.debug("No GPS logs found")
        return []
    # else:
        # logger.debug(f'found {len(pos_inds)} position logs and {len(vel_inds)} velocity logs')
        # In survey mode, there should never be more than 1 position and 1 velocity entry
        
    # See page 47 of the OEM7 Firmware Reference Manual for the header reference indices,
    # and page 443 for the BESTPOS / BESTVEL indices
    header_len = 28;

    data = data.astype('uint8')
    
    
    if len(pos_inds)!=len(vel_inds):
        logger.warning("position / velocity mismatch!")

    outs = []
    for i in range(max(len(pos_inds), len(vel_inds))):
        out = dict()

        # Position entries:
        # if len(pos_inds) > 0:
        if i <= len(pos_inds):
        	try:
	            x = pos_inds[i]
	            H = x + header_len # matches the "H" in the datasheets
	            
	            # Parameters common to both position and velocity messages:
	            time_status = int(data[x + 13])
	            receiver_status = struct.unpack('I',data[x + 20: x + 24].tobytes())[0]
	            weeknum_pos = 1.0*(data[x + 14] + (data[x + 15] <<8));
	            sec_offset_pos =(struct.unpack('I',data[x + 16:x +20].tobytes()))[0]/1000.

	            # Parameters in BESTPOS:
	            # Number of satellites in view; number of satellites used in solution
	            tracked_sats = int(data[H + 64])
	            used_sats = int(data[H + 65])

	            # Solution status + position type flags:
	            sol_stat = struct.unpack('I',data[H:H+4].tobytes())[0]
	            pos_type = struct.unpack('I',data[H+4:H+8].tobytes())[0]

	            # Lat and Lon are 8-byte doubles; unpack 'em
	            lat = struct.unpack('d', data[H+8:H+16].tobytes())[0]
	            lon = struct.unpack('d', data[H+16:H+24].tobytes())[0]
	            alt = struct.unpack('d', data[H+24:H+32].tobytes())[0]
	            
	            # out['pos'] = [lat, lon, alt]
	            out['lat'] = lat; out['lon'] = lon; out['alt'] = alt
	            out['tracked_sats'] = tracked_sats
	            out['used_sats'] = used_sats
	            
	            # All these fields are in the 'velocity' message as well, and *should* be the same...
	            out['time_status'] = time_status
	            out['receiver_status'] = receiver_status
	            out['weeknum'] = weeknum_pos
	            out['sec_offset'] = sec_offset_pos
	            out['solution_status'] = sol_stat
	            out['solution_type'] = pos_type
	        except:
	        	logger.warning(f'exception decoding position message {i}')
        # Velocity entries:
        # if len(vel_inds) > 0:
        if i <= len(vel_inds):
        	try:
	            x = vel_inds[i]
	            H = x + header_len # matches the "H" in the datasheets
	            
	            # Repeat for the velocity messages:
	            time_status = int(data[x + 13])
	            receiver_status = struct.unpack('I',data[x + 20: x + 24].tobytes())[0]
	            weeknum_vel = 1.0*(data[x + 14] + (data[x + 15] <<8));
	            sec_offset_vel =(struct.unpack('I',data[x + 16:x + 20].tobytes()))[0]/1000.

	            # Parameters in BESTVEL:
	            H = x + header_len

	            # Solution status + position type flags:
	            sol_stat = struct.unpack('I',data[H:H+4].tobytes())[0]
	            vel_type = struct.unpack('I',data[H+4:H+8].tobytes())[0]

	            # Latency of velocity measurement, in seconds
	            latency = struct.unpack('f',data[H+8:H+12].tobytes())[0]

	            # Horizontal and vertical speeds, in meters per second:
	            horiz_speed = struct.unpack('d',data[H+16:H+24].tobytes())[0]
	            vert_speed  = struct.unpack('d',data[H+32:H+40].tobytes())[0]

	            # Direction of motion over the ground WRT True North, in degrees:
	            ground_track= struct.unpack('d',data[H+24:H+32].tobytes())[0]

	            out['horiz_speed'] = horiz_speed
	            out['vert_speed'] = vert_speed
	            out['ground_track'] = ground_track
	            out['latency'] = latency
	            
	            if 'weeknum' in out.keys():
	                # If we had both a position and velocity message, confirm that the timestamps agree:
	                if out['weeknum'] != weeknum_vel:
	                    logger.warning("position / velocity timestamp mismatch")
	            else:
	                # If we didn't get a position message, use this data
	                out['time_status'] = time_status
	                out['receiver_status'] = receiver_status
	                out['weeknum'] = weeknum_vel
	                out['sec_offset'] = sec_offset_vel
	                out['solution_status'] = sol_stat
	                out['solution_type'] = vel_type
        	except:
        		logger.warning(f'exception decoding velocity message {i}')
        # timestamp
        out['timestamp'] = (reference_date + datetime.timedelta(weeks=out['weeknum']) + \
                      datetime.timedelta(seconds=out['sec_offset'])).timestamp()
        outs.append(out)

    return outs

def decode_survey_data(packets, separation_time = 4.5):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.1
        Date:   2.25.2020
    Description:
        - Modified sorting lines to use the 'header_timestamp' field rather
          than computing it from header_epoch_sec and header_ns. 
    Version:    1.0
        Date:   10.14.2019
    Description:
        Gathers and reassembles any "survey" data contained within a set of packets.

    inputs: 
        packets: A list of "packet" dictionaries, as returned from decode_packets.py
        separation_time: The maximum time, in seconds, between packet arrivals
                for which we'll group by experiment number.
    outputs:
        A list of dictionaries:
        Each dictionary is a single survey column, and contains the following fields:
            E_data: The electric field data, corresponding to averaged, log-scaled
                    magnitudes of the onboard FFT
            B_data: The magnetic field data, corresponding to averaged, log-scaled
                    magnitudes of the onboard FFT
            GPS:    A dictionary of decoded GPS data, corresponding to the end of
                    the current survey product
    '''

    # leap_seconds = 18  # GPS time does not account for leap seconds; as of ~2019, GPS leads UTC by 18 seconds.
    # reference_date = datetime.datetime(1980,1,6,0,0, tzinfo=datetime.timezone.utc) - datetime.timedelta(seconds=leap_seconds)
    # logger = logging.getLogger(__name__ +'.decode_survey_data')
    logger = logging.getLogger(__name__ +'.decode_survey_data')
    S_packets = list(filter(lambda packet: packet['dtype'] == 'S', packets))
    # Sort by arrival time
    # S_packets = sorted(S_packets, key=lambda p: p['header_epoch_sec'] + p['header_ns']*1e-9)
    S_packets = sorted(S_packets, key=lambda p: p['header_timestamp'])

    if len(S_packets) == 0:
        logger.info("no survey data present!")
        return [], []

    # These will roll over every 256 survey columns... need to deal with that
    # in this search. For now, just assume they're unique

    
    # ax.plot(np.diff([x['exp_num'] for x in S_packets]),'.')
    # plt.show()
    e_nums = np.unique([x['exp_num'] for x in S_packets])

    logging.debug(f'available survey experiment numbers: {e_nums}')

    survey_packet_length = 1212

    gps_length = 180
    survey_header = np.array([205, 171, 33, 67])
    # survey_footerooter = np.array([137, 103, 33, 67])

    # Index kernels
    gps_index = np.arange(len(survey_header),len(survey_header) + gps_length).astype('int')
    # The indices of the BBR data -- four-byte interleaved (1,2,3,4),(9,10,11,12),(17,18,19,20)...
    bbr_index_noLCS = np.array([np.arange(4) + 4 + k*8 for k in range(128)]).ravel().astype('int')
    gps_index += bbr_index_noLCS[-1] + 1

    # Gather and reassemble the 3-ish survey (system) packets into a single survey (product) packet
    S_data = []
    complete_surveys = []
    unused = []
    # separation_time = 4.5 # 0.5  # seconds
    for e_num in e_nums:

        # Reassemble into a single survey data packet
        cur_packets   = list(filter(lambda packet: packet['exp_num'] == e_num, S_packets))

        # Divide this list up into segments with nearby arrival times:
        # arrival_times = [p['header_epoch_sec'] + p['header_ns']*1e-9 for p in cur_packets]
        arrival_times = [p['header_timestamp'] for p in cur_packets]

        # Find any significant time differences
        splits = np.where(np.diff(arrival_times) > separation_time)[0] + 1  
        # append the first and last indexes to the list, to give us pairs of indexes to slice around
        splits = np.insert(np.append(splits,[len(cur_packets)]),0,0) 

        # Iterate over sub-lists of packets, as divided by splits:
        for s1,s2 in zip(splits[0:-1],splits[1:]):
            try:
                # Start with all nans
                cur_data = np.zeros(survey_packet_length)*np.nan
                # Insert each packets' payload
                for p in cur_packets[s1:s2]:
                    cur_data[p['start_ind']:(p['start_ind'] + p['bytecount'])] = p['data']
                # Did we get a full packet? 
                if np.sum(np.isnan(cur_data)) == 0:
                    # Complete packet!
                    
                    E_data = cur_data[bbr_index_noLCS]
                    B_data = cur_data[bbr_index_noLCS + 4]
                    G_data = cur_data[gps_index].astype('uint8')

                    d = dict()
                    try:
                        G = decode_GPS_data(G_data)
                        d['GPS'] = G
                    except:
                        logger.warning('Failed to decode survey GPS data')

                    d['E_data'] = E_data.astype('uint8')
                    d['B_data'] = B_data.astype('uint8')
                    # d['header_epoch_sec'] = cur_packets[s1]['header_epoch_sec']
                    d['header_timestamp'] = cur_packets[s1]['header_timestamp']
                    d['exp_num'] = e_num
                    S_data.append(d)

                else:
                    # If not, put the unused packets aside, so we can possibly
                    # combine with packets from other files
                    unused.extend(cur_packets[s1:s2])
            except:
                logging.warning(f'bad survey packet between {s1} and {s2}')
    # Send it
    logger.info(f'Recovered {len(S_data)} survey products, leaving {len(unused)} unused packets')
    return S_data, unused


def unique_entries(in_list):
    # Python doesn't like to compare complex entries (dicts containing dicts, numpy arrays)
    # So we're explicitly generating a hash of the entry, by casting the whole thing to a string.
    # It's slow but probably works!
    
    # 1. compute hash
    for el in in_list:
        # Here's a quick and dirty hash function. Might fail on nested dictionaries,
        # since we're only sorting the top-level dictionary (e.g., the GPS entries might
        # come up in a different order)
        el['id'] = hash(str(sorted(el.items())))
    
    # 2. build a temporary dictionary of values, with hash as key
    temp = list({v['id']: v for v in in_list}.values())
    
    # 3. ditch the hash, for cleanliness:
    #    - Pop from in_list, not temp, since the elements themselves
    #      are identified by reference. If we pop from temp, we'll leave
    #      'id' elements in the duplicate entries.
    for el in in_list:
        el.pop('id')
    
    return temp


def deep_compare(d1, d2):
    ''' Implements a recursive deep compare of two objects
        (lists, dictionaries, arrays, or otherwise comparable)
        and any structure comprised of these types. '''
    
    # Check types
    if not isinstance(d1, type(d2)):
        print(f'Type mismatch: {type(d1)}, {type(d2)}')
        return False
    
    # Root nodes are dictionaries -- process each element
    if isinstance(d1, dict):
        k1 = sorted(d1.keys())
        k2 = sorted(d2.keys())
        if k1 != k2:
            print(f'Key mismatch')
            print(k1)
            print(k2)
            return False

        for k in k1:
            if not deep_compare(d1[k], d2[k]):
                print(f'{k} does not match')
                return False
        return True

    # Root nodes are lists or arrays -- process each element
    if (isinstance(d1, list) or isinstance(d1, np.ndarray)):
        if len(d1) != len(d2):
            return False
        for a, b in zip(d1, d2):
            if not deep_compare(a, b):
                return False
            return True

    # Base case -- do simple comparisons
    if isinstance(d1, np.float):
        # Numpy compares nans as false
        if np.isnan(d1) and np.isnan(d2):
            return True

    # Strings, ints, numbers, whatever
    return d1==d2