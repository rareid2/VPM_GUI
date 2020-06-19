import sqlite3
from sqlite3 import Error

import numpy as np
import os, sys
import logging
import datetime




def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    logger = logging.getLogger('create_connection')

    if not os.path.exists(db_file):
        logger.info('no db exists! creating')
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        logger.error(e)

    return conn


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    logger = logging.getLogger('create_table')

    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        logger.error(e)

def packet_hash(el):
    # A hash of a single packet. This is a little sloppy, since
    # it casts the whole dict to a string, sorted by keys.
    # It will fail on nested dictionaries if the nested
    # dicts are in different orders, since we're only sorting the
    # top level.
    return hash(str(sorted(el.items())))
    
def add_metadata(in_list):
    # Add metadata to each entry -- a hash value, and the time added.
    for el in in_list:
        el['hash'] = packet_hash(el)
        el['added'] = datetime.datetime.now().timestamp()

def connect_packet_db(db_name):
    # Connect to a database, and create the packets table,
    # if it doesn't already exist

    logger = logging.getLogger('connect_packet_db')

    sql_create_packets_table = """ CREATE TABLE IF NOT EXISTS packets (
                                        data BLOB,
                                        start_ind INTEGER,
                                        dtype TEXT,
                                        exp_num INTEGER,
                                        bytecount INTEGER,
                                        checksum_verify INTEGER,
                                        packet_length INTEGER,
                                        fname TEXT,
                                        header_timestamp REAL,
                                        file_index INTEGER,
                                        hash INTEGER,
                                        header_ns INTEGER,
                                        header_epoch_sec INTEGER,
                                        header_reboots INTEGER,
                                        added REAL
                                    ); """

    # create a database connection
    conn = create_connection(db_name)

    # create tables
    if conn is not None:
        logger.info('connected to db')
        # create projects table
        create_table(conn, sql_create_packets_table)
    else:
        logger.error("Error! cannot create the database connection.")

    return conn

def write_to_db(conn, packets, db_field = 'packets'):
    logger = logging.getLogger('write_to_db')

    for p in packets:

        # add metadata
        p['hash'] = packet_hash(p)
        p['added'] = datetime.datetime.now().timestamp()

        sql = f'INSERT INTO {db_field}('
        vals = []


        for k, v in p.items():
            sql+=k + ','
            if type(v) == list:
                # Here we're assuming the list is of uint8s. Can
                # we abstract this better? We could do the array conversion
                # before this call, and just read the dtype...
                # vals.append(str(v))
                # vals.append(sqlite3.Binary(np.array(v,dtype=np.uint8)))
                vals.append(sqlite3.Binary(np.array(v, dtype=np.uint8)).tobytes())
                # To reconstruct on the other end, do:
                # y = np.frombuffer(x, dtype=np.uint8)  
            elif type(v) == np.uint8:
                vals.append(int(v))
            else:
                vals.append(v)

        sql = sql[:-1] + ') VALUES(' + ''.join(['?,' for x in p])
        sql = sql[:-1] + ')'                                           
        
        cur = conn.cursor()
        cur.execute(sql, vals)
    return cur.lastrowid

def get_packets_within_range(database, dtype=None, date_added=None, t1=None, t2=None):
    '''
    Load packets from the database, with header_timestamps between datetimes t1 and t2,
    and added after date_added, for data type specified by dtype (S, E, B, G, I)
    '''
    logger = logging.getLogger('get_packets_within_range')

    if date_added is None:
        date_added = datetime.datetime.utcfromtimestamp(0)
    if t1 is None:
        t1 = datetime.datetime.utcfromtimestamp(0)
    if t2 is None:
        t2 = datetime.datetime.now()

    conn = create_connection(database)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if dtype:
        sql = '''SELECT DISTINCT * FROM packets 
                WHERE header_timestamp > ? 
                AND header_timestamp < ? 
                AND dtype=?
                AND added > ?
                ORDER BY header_timestamp'''

        cur.execute(sql, (t1.timestamp(), t2.timestamp(), dtype, date_added.timestamp()))
    else:
        sql = '''SELECT DISTINCT * FROM packets 
                WHERE header_timestamp > ? 
                AND header_timestamp < ? 
                AND added > ?
                ORDER BY header_timestamp'''

        cur.execute(sql, (t1.timestamp(), t2.timestamp(), date_added.timestamp()))

    rows = cur.fetchall()

    logger.debug(f'Retrieved {np.shape(rows)[0]} packets from db')
    packets = []
    for row in rows:
        p = dict(row)
        p['data'] = np.frombuffer(p['data'],dtype=np.uint8).tolist()
        packets.append(p)
        
    return packets


def get_files_in_db(db_name, db_field):
    try:
        # Get filenames already in the database, so we don't reprocess them:
        sql = '''SELECT DISTINCT fname FROM ''' + db_field
        conn = create_connection(db_name)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        return [x[0] for x in rows]
    except:
        return []

def get_last_access_time(db_name, source_str):
    '''
     Get the time of the last access entry for source_str.
    '''
    sql = f'SELECT * FROM log WHERE source="{source_str}"'
    conn = create_connection(db_name)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    if rows:
        return max([r[0] for r in rows])
    else:
        return 0

def get_time_range_for_updated_packets(db_name, ts):
    # 1. find the last log entry timestamp for source_str
    # Get header timestamps corresponding to newly-added packets:
    
    sql = f'SELECT header_timestamp FROM packets WHERE added > {ts}'
    conn = create_connection(db_name)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    if len(rows) < 1:
        # print(f'No packets added after {datetime.datetime.utcfromtimestamp(ts)}')
        return None, None

    # Get minimum timestamp:
    tmin = min(rows)[0]    
    tmax = max(rows)[0]

    return tmin, tmax   
    # logger.info(f'packets added after {datetime.datetime.utcfromtimestamp(ts)}')
    # logger.info(f'Header timestamps range from {datetime.datetime.utcfromtimestamp(tmin)} to {datetime.datetime.utcfromtimestamp(tmax)}')
    
    
def log_access_time(db_name, source_str, desc_str=None):
    '''
     records the current time in the "log" db, tagged to source_str.
     You can add a description string if it's useful!
    '''

    sql_create_log_table = """ CREATE TABLE IF NOT EXISTS log (
                                    timestamp real,
                                    time_str TEXT,
                                    source TEXT,
                                    description TEXT
                                ); """

    conn = create_connection(db_name)
    cur = conn.cursor()
    cur.execute(sql_create_log_table)

    sql = f'INSERT INTO log (timestamp, time_str, source, description) VALUES(?, ?, ?, ?)'
    cur = conn.cursor()
    t = datetime.datetime.now()
    cur.execute(sql,(t.timestamp(), t.isoformat(), source_str, desc_str))
    conn.commit()
    conn.close()
    
