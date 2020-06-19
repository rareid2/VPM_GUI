import xml.etree.ElementTree as ET
import xml.dom.minidom as MD
import numpy as np
import datetime
import os
import logging
import pickle
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.gridspec as GS
import argparse


def plot_ubbr_configuration(data,filename='bbr_config.png', show_plots=False):
    '''Plot the uBBR configuration from a set of status messages'''

    # --------------- Latex Plot Beautification --------------------------
    fig_width = 10 
    fig_height = 8
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------

    bbr_data = dict()
    bbr_data['T'] = []
    burst_times = []

    # These fields get a fixed y-axis of 0-1
    binary_lims = ['E_GAIN','B_GAIN','E_FILT','B_FILT','E_CAL','B_CAL',
                   'E_PRE','B_PRE','E_RST','B_RST','CALTONE','SIG_GEN']

    for S in sorted(dd, key = lambda f: f['header_timestamp']):
        if S['bbr_config'] is not None:    
            bbr_data['T'].append(datetime.datetime.utcfromtimestamp(S['header_timestamp']))
            for k, v in S['bbr_config'].items():
                if k in bbr_data:
                    bbr_data[k].append(v)
                else:
                    bbr_data[k] = [v]
                    

    # We probably don't care about the ADC resets and presets, etc
    fields_to_plot = ['E_GAIN','B_GAIN','E_FILT','B_FILT','E_CAL','B_CAL','CALTONE','SIG_GEN']

    fig, ax = plt.subplots(len(fields_to_plot), 1, sharex=True)

    for i, k in enumerate(fields_to_plot):
        if k=='CALTONE':
            # Add the "off" instances one minute after each "on"
            t_tmp = []
            c_tmp = []
            for t, c in zip(bbr_data['T'], bbr_data['CALTONE']):
                t_tmp.append(t)
                c_tmp.append(c)
                if c==1:
                    t_tmp.append(t + datetime.timedelta(minutes=1))
                    c_tmp.append(0)
                    
            ax[i].plot(t_tmp, c_tmp,'o-', color=plt.cm.tab20(i), drawstyle='steps-post')
        else:
            # Plot the rest regularly
            ax[i].plot(bbr_data['T'],bbr_data[k],'o-', color=plt.cm.tab20(i), drawstyle='steps-post')
        
        if k in binary_lims:
            ax[i].set_ylim([-0.2, 1.2])
            
        ax[i].set_ylabel(k, rotation=0, labelpad=30)    
        ax[i].yaxis.grid('on')    
        ax[i].spines["top"].set_visible(False)
        ax[i].spines["right"].set_visible(False)

    formatter = mdates.DateFormatter('%d/%m/%Y %H:%M:%S')
    ax[-1].xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()
    ax[0].set_title('µBBR Configuration from Status')

    if show_plots:
        plt.show()

    fig.savefig(filename, bbox_inches='tight')
    



def plot_system_status(data, filename ='system_status.pdf', show_plots=False):
    ''' Plot a big grid of system parameters from the status files '''
    sys_data = dict()
    sys_data['T'] = []

    bbr_data = dict()
    bbr_data['T'] = []

    for S in sorted(dd, key = lambda f: f['header_timestamp']):
        if S['bbr_config'] is not None:    
            bbr_data['T'].append(datetime.datetime.utcfromtimestamp(S['header_timestamp']))
            for k, v in S['bbr_config'].items():
                if k in bbr_data:
                    bbr_data[k].append(v)
                else:
                    bbr_data[k] = [v]


    for S in sorted(dd, key = lambda f: f['header_timestamp']):
        sys_data['T'].append(datetime.datetime.utcfromtimestamp(S['header_timestamp']))
        for k, v in S.items():
            if k in ['bbr_config','burst_config']:
                continue
            else:
                if k in sys_data:
                    sys_data[k].append(v)
                else:
                    sys_data[k] = [v]


    # --------------- Latex Plot Beautification --------------------------
    fig_width = 12
    fig_height = 8
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 10,
              'font.size': 10,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------

    fig = plt.figure()
    gs_root = GS.GridSpec(2, 2,  wspace = 0.2, hspace = 0.3, figure=fig)

    # --------- Upper left ------------
    gs00 = GS.GridSpecFromSubplotSpec(5, 1, hspace=0.2, wspace=0.2, subplot_spec=gs_root[0,0])

    # Uptime:
    ax1 = fig.add_subplot(gs00[0])
    ax1.plot(sys_data['T'],sys_data['uptime'],'o-',  label='uptime', alpha=0.8)
    ax1.set_ylabel('Uptime\n[sec]')
    ax1.set_title('System Health')

    # Received commands:
    ax2 = fig.add_subplot(gs00[1])
    ax2.plot(sys_data['T'], sys_data['total_commands'],'o-', drawstyle='steps-post', label='total_commands', alpha=0.8)
    ax2.set_ylabel('Total\nCommands')

    # Memory usage:
    ax3 = fig.add_subplot(gs00[2])

    ax3.plot(sys_data['T'], np.array(sys_data['total_bytes_out'])/1024/1024, 'o-',
             drawstyle='steps-post', label='Total MB transmitted')
    ax3.set_ylabel('Total MB\nOut')

    ax3b = fig.add_subplot(gs00[3])
    ax3b.plot(sys_data['T'], sys_data['mem_percent_full'], 'o-',
              drawstyle='steps-post', label='Memory percent full', alpha=0.8)
    ax3b.set_ylim([0,100])
    ax3b.set_yticks([0,25,50,75,100])
    ax3b.set_ylabel('SRAM\n % full')

    # GPS Errors and automatic resets:
    ax4 = fig.add_subplot(gs00[4])
    ax4.plot(sys_data['T'], sys_data['GPS_errors'], 'o-', alpha=0.8, drawstyle='steps-post', label='GPS errors')
    ax4.plot(sys_data['T'], sys_data['gps_resets'], 'x-', alpha=0.8, drawstyle='steps-post', label='GPS resets')
    ax4.set_ylabel('GPS\nErrors')
    ax4.legend(ncol=1)





    # --------- Lower left -----------
    gs10 = GS.GridSpecFromSubplotSpec(5, 1, hspace=0.2, wspace=0.2, subplot_spec=gs_root[1,0])

    # Total transmitted packets:
    ax8 = fig.add_subplot(gs10[0])
    ax8.set_title('Misc')
    ax8.plot(sys_data['T'], np.array(sys_data['E_total']),   'o-', drawstyle='steps-post', alpha=0.8, label='E')
    ax8.plot(sys_data['T'], np.array(sys_data['B_total']),   'o-', drawstyle='steps-post', alpha=0.8, label='B')
    ax8.legend(ncol=2)
    ax8.set_ylabel('Total\nPackets')

    ax9 = fig.add_subplot(gs10[1])
    ax9.plot(sys_data['T'], np.array(sys_data['GPS_total']), 'o-', drawstyle='steps-post', alpha=0.8, label='GPS')
    ax9.plot(sys_data['T'], np.array(sys_data['survey_total']) ,'o-', drawstyle='steps-post', alpha=0.8, label='Survey')
    ax9.plot(sys_data['T'], np.array(sys_data['status_total']) , 'o-', drawstyle='steps-post', alpha=0.8, label='Status')
    ax9.set_ylabel('Total\nPackets')
    ax9.legend(ncol=3)


    # Experiment numbers:
    ax10 = fig.add_subplot(gs10[2])
    ax10.plot(sys_data['T'], np.array(sys_data['E_exp_num']), 'o-', drawstyle='steps-post', alpha=0.8, label='E')
    ax10.plot(sys_data['T'], np.array(sys_data['B_exp_num']) ,'o-', drawstyle='steps-post', alpha=0.8, label='B')
    ax10.plot(sys_data['T'], np.array(sys_data['GPS_exp_num']) , 'o-', drawstyle='steps-post', alpha=0.8, label='GPS')
    ax10.plot(sys_data['T'], np.array(sys_data['survey_exp_num']) , 'o-', drawstyle='steps-post', alpha=0.8, label='Survey')
    ax10.legend(ncol=4)
    ax10.set_ylabel('Exp\nNumber')

    # Antenna deployers:
    ax11 = fig.add_subplot(gs10[3])
    ax11.plot(sys_data['T'], np.array(sys_data['arm_e']), 'o-', drawstyle='steps-post', alpha=0.8, label='E')
    ax11.plot(sys_data['T'], np.array(sys_data['arm_b']) ,'o-', drawstyle='steps-post', alpha=0.8, label='B')
    ax11.legend(ncol=2)
    ax11.set_ylabel('Ant\nArm')
    ax11.set_ylim([-0.2, 1.2])
    ax12 = fig.add_subplot(gs10[4])
    ax12.plot(sys_data['T'], np.array(sys_data['e_deployer_counter']) , 'o-', drawstyle='steps-post', alpha=0.8, label='E')
    ax12.plot(sys_data['T'], np.array(sys_data['b_deployer_counter']) , 'o-', drawstyle='steps-post', alpha=0.8, label='B')
    ax12.set_ylabel('Ant\nDeploys')
    ax12.legend(ncol=2)

    formatter = mdates.DateFormatter('%d/%m/%Y %H:%M:%S')
    ax12.xaxis.set_major_formatter(formatter)

    # # --------------- uBBR configuration ----------


    # These fields get a fixed y-axis of 0-1
    binary_lims = ['E_GAIN','B_GAIN','E_FILT','B_FILT','E_CAL','B_CAL',
                   'E_PRE','B_PRE','E_RST','B_RST','CALTONE','SIG_GEN']

    # We probably don't care about the ADC resets and presets, etc
    fields_to_plot = ['E_GAIN','B_GAIN','E_FILT','B_FILT','E_CAL','B_CAL','CALTONE','SIG_GEN']

    gs01 = GS.GridSpecFromSubplotSpec(len(fields_to_plot), 1, hspace=0.2, wspace=0.2, subplot_spec=gs_root[1,1])

    ax_bbr = []

    for i, a in enumerate(fields_to_plot):
        ax_bbr.append(fig.add_subplot(gs01[i]))

    for i, k in enumerate(fields_to_plot):
        if k=='CALTONE':
            # Add the "off" instances one minute after each "on"
            t_tmp = []
            c_tmp = []
            for t, c in zip(bbr_data['T'], bbr_data['CALTONE']):
                t_tmp.append(t)
                c_tmp.append(c)
                if c==1:
                    t_tmp.append(t + datetime.timedelta(minutes=1))
                    c_tmp.append(0)
                    
            ax_bbr[i].plot(t_tmp, c_tmp,'o-', color=plt.cm.tab20(i), drawstyle='steps-post')
        else:
            # Plot the rest regularly
            ax_bbr[i].plot(bbr_data['T'],bbr_data[k],'o-', color=plt.cm.tab20(i), drawstyle='steps-post')
        
        if k in binary_lims:
            ax_bbr[i].set_ylim([-0.2, 1.2])

        ax_bbr[i].set_ylabel(k, rotation=0, labelpad=30)    
        ax_bbr[i].yaxis.grid('on')    


    # formatter = mdates.DateFormatter('%d/%m/%Y %H:%M:%S')
    # ax_bbr[-1].xaxis.set_major_formatter(formatter)
    # fig.autofmt_xdate()
    ax_bbr[0].set_title('µBBR Configuration')



    # ---------- Config -------------
    gs11 = GS.GridSpecFromSubplotSpec(3, 1, hspace=0.2, wspace=0.2, subplot_spec=gs_root[0,1])

    ax5 = fig.add_subplot(gs11[0])
    ax5.set_title('Configuration')

    # Channel enables:
    ax5.plot(sys_data['T'], sys_data['e_enable'],    'o-', drawstyle='steps-post', alpha=0.5, label='E')
    ax5.plot(sys_data['T'], sys_data['b_enable'],    'x-', drawstyle='steps-post', alpha=0.5, label='B')
    ax5.plot(sys_data['T'], sys_data['gps_enable'],  '.-', drawstyle='steps-post', alpha=0.5, label='GPS')
    # ax5.plot(sys_data['T'], sys_data['lcs_enable'],  '.-', drawstyle='steps-post', alpha=0.5, label='LCS')
    ax5.set_ylim([-0.2, 1.2])
    ax5.set_yticks([0,1])
    ax5.set_yticklabels(['off','on'])
    ax5.set_ylabel('Channel\nenable')
    ax5.legend(ncol=3)

    # Burst pulses:
    ax6 = fig.add_subplot(gs11[1])
    ax6.plot(sys_data['T'], sys_data['burst_pulses'],   'o-', drawstyle='steps-post', alpha=0.8, label='burst_pulses')
    ax6.set_ylim(bottom=0)
    ax6.set_ylabel('Burst\nPulses')
    ax6.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Survey period:
    ax7 = fig.add_subplot(gs11[2])
    tmp = np.zeros_like(sys_data['survey_period'])
    tmp[np.array(sys_data['survey_period'])==1024]=1
    tmp[np.array(sys_data['survey_period'])==2048]=2
    tmp[np.array(sys_data['survey_period'])==4096]=3
    ax7.plot(sys_data['T'], tmp,   'o-', drawstyle='steps-post', alpha=0.8, label='survey_period')
    ax7.set_ylim(bottom=0)
    ax7.set_ylabel('Survey\nPeriod')
    ax7.set_ylim([0.5,3.5])
    ax7.set_yticks([1,2,3])
    ax7.set_yticklabels(['short','med', 'long'])

    formatter = mdates.DateFormatter('%d/%m/%Y %H:%M:%S')
    ax_bbr[-1].xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()
    gs_root.tight_layout(fig)


    if show_plots:
        plt.show()

    fig.savefig(filename, bbox_inches='tight')
if __name__ == '__main__':
    from file_handlers import read_status_XML
    
    parser = argparse.ArgumentParser(description="VPM Ground Support Software -- Status plotter")

    parser.add_argument("--input","--in",  required=True, type=str, default = 'input', help="path to an input XML file")
    parser.add_argument("--output","--out", required=False, type=str, default='status.pdf', help="output filename. Suffix defines file type (pdf, png)")

    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--debug", dest='debug', action='store_true', help ="Debug mode (extra chatty)")
    g.set_defaults(debug=False)


    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--interactive_plots", dest='show_plots', action='store_true', help ="Plot interactively")
    g.set_defaults(debug=False)

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
    else:
        logging.basicConfig(level=logging.INFO,  format='[%(name)s]\t%(levelname)s\t%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    if os.path.exists(args.input):  
        # Load it
        dd = read_status_XML(args.input)

        # Plot it
        plot_system_status(dd,args.output, args.show_plots)
    else:
        logging.warning(f'Cannot find file {args.input}')

