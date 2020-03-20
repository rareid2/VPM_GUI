# import netCDF4
import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
import numpy as np
import datetime
import os
import logging


def write_status_XML(in_data, filename="status_messages.xml"):
    '''write status messages to an xml file'''

    in_data = sorted(in_data, key=lambda k: k['header_timestamp'])
    d = ET.Element('status_messages')
    d.set('file_creation_date', datetime.datetime.now(datetime.timezone.utc).isoformat())

    for entry_data in in_data:
        entry = ET.SubElement(d,'status')
        entry.set('header_timestamp',datetime.datetime.utcfromtimestamp(entry_data['header_timestamp']).isoformat())

        for k, v in entry_data.items():
            # (This is a prime place for some recursion, if you wanted to show off)
            if isinstance(v,dict):
                sub_entry = ET.SubElement(entry,k)
                for kk, vv in v.items():
                    cur_item = ET.SubElement(sub_entry,kk)
                    cur_item.text = str(vv)
            else:                
                cur_item = ET.SubElement(entry,k)
                cur_item.text = str(v)        

    rough_string = ET.tostring(d, 'utf-8')
    reparsed = MD.parseString(rough_string).toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(reparsed)

def write_survey_XML(in_data, filename='survey_data.xml'):
    ''' Write a list of survey elements to an xml file. '''
    
    # Sort by internal timestamp    
    # in_data = sorted(in_data, key=lambda k: k['GPS'][0]['timestamp'])
    # Sort by receipt timestamp
    in_data = sorted(in_data, key=lambda k: k['header_timestamp'])

    d = ET.Element('survey_data')
    # d.set('creation_date', str(datetime.datetime.now(datetime.timezone.utc).timestamp()))
    d.set('file_creation_date', datetime.datetime.now(datetime.timezone.utc).isoformat())

    for entry_data in in_data:

        entry = ET.SubElement(d, 'survey')
        entry.set('header_timestamp',datetime.datetime.utcfromtimestamp(entry_data['header_timestamp']).isoformat())
        E_elem = ET.SubElement(entry, 'E_data')
        B_elem = ET.SubElement(entry, 'B_data')
        GPS_elem= ET.SubElement(entry,'GPS')
        E_elem.text = np.array2string(entry_data['E_data'], max_line_width=1000000000000, separator=',')[1:-2]
        B_elem.text = np.array2string(entry_data['B_data'], max_line_width=1000000000000, separator=',')[1:-2]

        if 'GPS' in entry_data:
            for k, v in entry_data['GPS'][0].items():

                cur_item = ET.SubElement(GPS_elem,k)
                cur_item.text = str(v)
        # header_entry = ET.SubElement(GPS_elem,'header_timestamp')
        # header_entry.text = '{0:f}'.format(entry_data['header_timestamp'])

    rough_string = ET.tostring(d, 'utf-8')
    reparsed = MD.parseString(rough_string).toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(reparsed)

def read_survey_XML(filename):   
    ''' Reads survey elements from an xml file. '''

    # Open it
    with open(filename,'r') as f:
        tree = ET.parse(f)
    
    outs = []
    
    # Process all "survey" elements
    for S in tree.findall('survey'):
        d = dict()
        d['E_data'] = np.fromstring(S.find('E_data').text, dtype='uint8', sep=',')
        d['B_data'] = np.fromstring(S.find('B_data').text, dtype='uint8', sep=',')
        d['GPS'] = []
        d['GPS'].append(dict())
        G = S.find('GPS')
        for el in G:
            try:
                d['GPS'][0][el.tag] = int(el.text)
            except:
                d['GPS'][0][el.tag] = float(el.text)
        outs.append(d)

        header_timestamp_isoformat = S.attrib['header_timestamp']
        d['header_timestamp'] = datetime.datetime.fromisoformat(header_timestamp_isoformat).replace(tzinfo=datetime.timezone.utc).timestamp()

    # if d:
    #     logging.info(f'survey keys: {d.keys()}')
    # else:
    #     logging.info(f'No survey entries found')

    # Return a list of dicts
    return outs

def write_burst_XML(in_data, filename='burst_data.xml'):
    ''' write a list of burst elements to an xml file. '''

    logger = logging.getLogger(__name__)
    logger.info(f'writing data to {filename}')
    in_data = sorted(in_data, key=lambda k: k['header_timestamp'])

    d = ET.Element('burst_data')
    d.set('file_creation_date', datetime.datetime.now(datetime.timezone.utc).isoformat())

    # Process each burst in the input list:
    for entry_data in in_data:
        logger.debug(f'entry_data contains {entry_data.keys()}')
        entry = ET.SubElement(d, 'burst')
        entry.set('header_timestamp',datetime.datetime.utcfromtimestamp(entry_data['header_timestamp']).isoformat())
        
        if 'config' in entry_data:
            # Configuration entries
            cfg = ET.SubElement(entry, 'burst_config')
            for k, v in entry_data['config'].items():
                cur_item = ET.SubElement(cfg,k)
                cur_item.text = str(v)

        if 'bbr_config' in entry_data:
            # uBBR configuration entries
            bbr = ET.SubElement(entry,'bbr_config')
            for k, v in entry_data['bbr_config'].items():
                cur_item = ET.SubElement(bbr,k)
                cur_item.text = str(v)
        
        if 'G' in entry_data: 
            # GPS entries
            gps = ET.SubElement(entry, 'GPS')
            for g in entry_data['G']:
                gps_el = ET.SubElement(gps,'gps_entry')
                for k, v in g.items():
                    cur_item = ET.SubElement(gps_el,k)
                    cur_item.text = str(v)


        # # Status entries
        # stat = ET.SubElement(entry,'status')
        # for status in entry_data['I']:
        #     stat_el = ET.SubElement(stat,'status_entry')
        #     for k, v in status.items():
        #         # (This is a prime place for some recursion, if you wanted to show off)
        #         if isinstance(v,dict):
        #             sub_entry = ET.SubElement(stat_el,k)
        #             for kk, vv in v.items():
        #                 cur_item = ET.SubElement(sub_entry,kk)
        #                 cur_item.text = str(vv)
        #         else:                
        #             cur_item = ET.SubElement(stat_el,k)
        #             cur_item.text = str(v)        

        # E and B data fields        
        if entry_data['config']['TD_FD_SELECT']==1:
            # Time domain
            E_data_elem = ET.SubElement(entry,'E_data')
            E_data_elem.set('mode','time domain')
            E_str = ''.join(['{0:g},'.format(x) for x in entry_data['E']])[0:-1]
            E_data_elem.text = E_str
            B_data_elem = ET.SubElement(entry,'B_data')
            B_data_elem.set('mode','time domain')
            B_str = ''.join(['{0:g},'.format(x) for x in entry_data['B']])[0:-1]
            B_data_elem.text = B_str

        if entry_data['config']['TD_FD_SELECT']==0:
            # Frequency domain
            E_data_elem = ET.SubElement(entry,'E_data')
            E_data_elem.set('mode','frequency domain')
            E_real = ET.SubElement(E_data_elem,'real')
            E_imag = ET.SubElement(E_data_elem,'imag')

            E_str = ''.join(['{0:g},'.format(np.real(x)) for x in entry_data['E']])[0:-1]
            E_real.text = E_str
            E_str = ''.join(['{0:g},'.format(np.imag(x)) for x in entry_data['E']])[0:-1]
            E_imag.text = E_str

            B_data_elem = ET.SubElement(entry,'B_data')
            B_data_elem.set('mode','frequency domain')
            B_real = ET.SubElement(B_data_elem,'real')
            B_imag = ET.SubElement(B_data_elem,'imag')

            B_str = ''.join(['{0:g},'.format(np.real(x)) for x in entry_data['B']])[0:-1]
            B_real.text = B_str
            B_str = ''.join(['{0:g},'.format(np.imag(x)) for x in entry_data['B']])[0:-1]
            B_imag.text = B_str



    rough_string = ET.tostring(d, 'utf-8')
    reparsed = MD.parseString(rough_string).toprettyxml(indent="\t")

    with open(filename, "w") as f:
        f.write(reparsed)

def read_burst_XML(filename):   
    ''' Reads burst elements from an xml file. '''

    logger = logging.getLogger(__name__)

    # Open it
    with open(filename,'r') as f:
        tree = ET.parse(f)
    outs = []
    
    # Process all "burst" elements
    for S in tree.findall('burst'):
        d = dict()

        # Load the iso-formatted UTC string, and cast it to a Unix timestamp
        # (This is consistent with how we're storing times internally)
        header_timestamp_isoformat = S.attrib['header_timestamp']
        d['header_timestamp'] = datetime.datetime.fromisoformat(header_timestamp_isoformat).replace(tzinfo=datetime.timezone.utc).timestamp()
        
        # Load burst configuration
        d['config'] = dict()
        for el in S.find('burst_config'):
            # print(cfg)
            # print(el.tag, el.text)
            # # for el in cfg:
                # print(el.name, el.text)
            if el.tag in ['str', 'BINS']:
                d['config'][el.tag] = el.text
            else:
                d['config'][el.tag] = int(el.text)

        if S.find('bbr_config') is not None:
            # Load bbr configuration
            d['bbr_config'] = dict()
            for el in S.find('bbr_config'):
                d['bbr_config'][el.tag] = int(el.text)

        TD_FD_SELECT = d['config']['TD_FD_SELECT']

        # Load data fields
        if TD_FD_SELECT == 1:
            # Time domain
            logger.debug('Selected time domain')
            d['E'] = np.fromstring(S.find('E_data').text, dtype='int16', sep=',')
            d['B'] = np.fromstring(S.find('B_data').text, dtype='int16', sep=',')

        elif TD_FD_SELECT == 0:
            # Frequency domain
            logger.debug('Selected frequency domain')
            ER = np.fromstring(S.find('E_data').find('real').text, dtype='int16', sep=',')
            EI = np.fromstring(S.find('E_data').find('imag').text, dtype='int16', sep=',')
            logger.debug(f'ER: {np.shape(ER)}, EI: {np.shape(EI)}')
            d['E'] = ER + 1j*EI
            
            BR = np.fromstring(S.find('B_data').find('real').text, dtype='int16', sep=',')
            BI = np.fromstring(S.find('B_data').find('imag').text, dtype='int16', sep=',')
            d['B'] = BR + 1j*BI

        logger.info(f"loaded E data of size {len(d['E'])}")
        logger.info(f"loaded B data of size {len(d['B'])}")

        # Load GPS data
        d['G'] = []
        for g in S.find('GPS'):
            tmp_dict = dict()
            for el in g:
                try:
                    tmp_dict[el.tag] = int(el.text)
                except:
                    tmp_dict[el.tag] = float(el.text)
            d['G'].append(tmp_dict)
        outs.append(d)
        logger.info(f"loaded {len(d['G'])} GPS elements")

    # Return a list of dicts
    return outs


def xml_read_kernel(el):
    '''
        A recursive kernel for reading XML elements
        (don't call this directly)
    '''
    # Parse these fields as strings
    str_fields = ['str','source','BINS']
    
    # Parse these fields as integer arrays
    arr_uint8_fields = ['prev_bbr_command','prev_burst_command','prev_command']
    
    if len(list(el)) > 0:
        d = dict()
        for sub in el:
            d[sub.tag] = xml_read_kernel(sub);
        return d
    else:
        # base case!
        if el.tag in str_fields:
            return el.text
        elif el.tag in arr_uint8_fields:
            return np.fromstring(el.text[1:-1], dtype='uint8',sep=' ')
        
        else:
            try:
                return int(el.text)
            except:
                return float(el.text)
            
def read_XML(filename, field):   
    ''' Reads status elements from an xml file. ''' 

    # Open it
    with open(filename,'r') as f:
        tree = ET.parse(f)
    outs = []
    
    # Process all elements
    for S in tree.findall(field):
        outs.append(xml_read_kernel(S));
    return outs

def read_status_XML(filename):
    ''' A convenience wrapper '''
    return read_XML(filename, 'status')
    
if __name__ == '__main__':

    import os
    import pickle

    logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')


    with open("output/decoded_data.pkl",'rb') as f:
        outs = pickle.load(f)


    # os.remove('survey_data.nc')
    # print("writing survey data")
    # write_survey_netCDF(outs['survey'])
    # write_survey_XML(outs['survey'])

    print("writing burst data")
    write_burst_XML(outs['burst'],filename="burst_debug.xml")

    xml_data = read_burst_XML("burst_debug.xml")
    print("original data:")
    print(outs['burst'][0].keys())
    print("xml data:")
    print(xml_data[0].keys())
    