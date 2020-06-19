import numpy as np
import datetime
import os
import pickle
from data_handlers import decode_status
from data_handlers import decode_burst_command
import logging

def packet_inspector(fig, packets):
    logger = logging.getLogger(__name__)
    

    # figure_window = tk.Toplevel(parent)
    ''' A nice tool to analyze packets in a list. Click'em to see info about them! '''

    # Select burst packets
    E_packets = list(filter(lambda packet: packet['dtype'] == 'E', packets))
    B_packets = list(filter(lambda packet: packet['dtype'] == 'B', packets))
    G_packets = list(filter(lambda packet: packet['dtype'] == 'G', packets))
    I_packets = list(filter(lambda packet: packet['dtype'] == 'I', packets))
    S_packets = list(filter(lambda packet: packet['dtype'] == 'S', packets))
    
    logger.info(f'E: {len(E_packets)} B: {len(B_packets)} G: {len(G_packets)} Status: {len(I_packets)} Survey: {len(S_packets)}')  
    logger.info(f"Exp nums: {np.unique([p['exp_num'] for p in packets])}")
    logger.info(f"Burst exp nums: {np.unique([p['exp_num'] for p in E_packets + B_packets + G_packets])}")
    logger.info(f"Survey exp nums: {np.unique([p['exp_num'] for p in S_packets])}")



    # -------- arrival time debugging plot -------
    # fig, ax = plt.subplots(1,1)
    # fig = Figure(figsize=(12,6))

    ax = fig.add_subplot(111)

    # canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    # canvas.draw()
    # canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # toolbar = NavigationToolbar2Tk(canvas, figure_window)
    # toolbar.update()
    # canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # taxis = np.arange(len(packets))    
    # tstamps = np.array([p['header_timestamp'] for p in packets])
    # dtypes  = np.array([p['dtype'] for p in packets])

    # ax.plot(taxis[dtypes=='E'], tstamps[dtypes=='E'],'.', label='E',      picker=5)
    # ax.plot(taxis[dtypes=='B'], tstamps[dtypes=='B'],'.', label='B',      picker=5)
    # ax.plot(taxis[dtypes=='G'], tstamps[dtypes=='G'],'.', label='GPS',    picker=5)
    # ax.plot(taxis[dtypes=='I'], tstamps[dtypes=='I'],'o', label='Status', picker=5)
    # ax.plot(taxis[dtypes=='S'], tstamps[dtypes=='S'],'.', label='Survey', picker=5)

    taxis = np.arange(len(packets))    
    tstamps = np.array([p['header_timestamp'] for p in packets])
    dts = np.array([datetime.datetime.utcfromtimestamp(p['header_timestamp']) for p in packets])
    dtypes  = np.array([p['dtype'] for p in packets])

    ax.plot(dts[dtypes=='E'], 1*np.ones_like(tstamps[dtypes=='E']),'.', label='E',      picker=5)
    ax.plot(dts[dtypes=='B'], 2*np.ones_like(tstamps[dtypes=='B']),'.', label='B',      picker=5)
    ax.plot(dts[dtypes=='G'], 3*np.ones_like(tstamps[dtypes=='G']),'.', label='GPS',    picker=5)
    ax.plot(dts[dtypes=='I'], 4*np.ones_like(tstamps[dtypes=='I']),'o', label='Status', picker=5)
    ax.plot(dts[dtypes=='S'], 5*np.ones_like(tstamps[dtypes=='S']),'.', label='Survey', picker=5)




    # ax.hlines([p['header_timestamp'] for p in I_packets], 0, len(packets))
    ax.vlines([datetime.datetime.utcfromtimestamp(p['header_timestamp']) for p in I_packets], 0, 6, alpha=0.7)
    ax.legend()
    # ax.set_xlabel('arrival index')
    ax.set_xlabel('Header Timestamp')
    ax.set_yticks([1,2,3,4,5])
    ax.set_yticklabels(['E','B','GPS','Status','Survey'])

    ax.set_ylim([0,6])
    # ax.set_xlim([min(tstamps), max(tstamps)])

    ax.grid(which='major', alpha=0.5)
    ax.grid(which='minor', alpha=0.2)
    fig.canvas.mpl_connect('pick_event', lambda event: onpick(event, packets))
    fig.suptitle('VPM Packet Inspector Tool')

    fig.autofmt_xdate()

    def onpick(event, packets):
        ''' Click handler '''
        thisline = event.artist
        xdata = thisline.get_xdata()
        ydata = thisline.get_ydata()
        ind = event.ind
        x_inds = xdata[ind]
        logger.info(x_inds)

        logger.info(f"Clicked on {len(x_inds)} events")
        if len(x_inds) > 0:
            x = np.where(dts == xdata[ind[0]])[0][0]

            # for x in x_inds:
            logger.info(f'packet at {x}:')

            if packets[x]['dtype']=='I':
                logger.info(f'Status packet:')
                stat = decode_status([packets[x]])
                logger.info(stat[0])
                # Get burst configuration parameters:
                cmd = np.flip(packets[x]['data'][12:15])
                burst_config = decode_burst_command(cmd)
                logger.info(burst_config)

            if (packets[x]['dtype']=='G') and (packets[x]['start_ind']==0):
                logger.info(f'GPS packet with echoed command')
                # First GPS packet -- burst command is echoed here
                cmd = np.flip(packets[x]['data'][0:3])
                burst_config = decode_burst_command(cmd)
                logger.info(burst_config)

            logger.info(f"\tdtype: {packets[x]['dtype']}")
            logger.info(f"\theader timestamp: {packets[x]['header_timestamp']}" +\
            f" ({datetime.datetime.utcfromtimestamp(packets[x]['header_timestamp'])})")
            logger.info(f"\tExp num: {packets[x]['exp_num']}")
            logger.info(f"\tData indexes: [{packets[x]['start_ind']}:" +\
                f"{packets[x]['start_ind'] + packets[x]['bytecount']}]")


    return True

if __name__ == '__main__':

    import matplotlib.pyplot as plt
    with open('output/packets.pkl','rb') as f:
        packets = pickle.load(f)

        fig = plt.figure()
    packet_inspector(fig, packets)
