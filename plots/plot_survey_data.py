import numpy as np
import matplotlib.pyplot as plt
import pickle
import datetime
import matplotlib.gridspec as GS
# from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal
from parula_colormap import parula
import logging
import argparse
import os
import math
from file_handlers import read_survey_XML
# from mpl_toolkits.basemap import Basemap
# from scipy.interpolate import interp1d, interp2d





def plot_survey_data(S_data, filename="survey_data.pdf", show_plots=False):
    '''
    Author:     Austin Sousa
                austin.sousa@colorado.edu
    Version:    1.0
        Date:   10.14.2019
    Description:
        Plots survey data as PDFs

    inputs: 
        S_data: a list of dictionaries, as returned from decode_survey_data.py
                Each dictionary represents a single column of the survey product.
                A time axis will be constructed using the timestamps within each
                dictionary.
        filename: The filename to save
    outputs:
        saved images; format is defined by the suffix of filename
    '''
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

    # Start the logger
    logger = logging.getLogger(__name__)
    # Ideally would look this up. This sets the maximum time 
    # where we'll insert a column of NaNs, to mark off missing data
    per_sec = 26 

    # colormap -- parula is Matlab; also try plt.cm.jet or plt.cm.viridis
    cm = parula();


    # Abandon if we don't have any data to plot
    if S_data is None:
        return
    
    # Assemble into grids:
    E = []
    B = []
    T = []
    F = np.arange(512)*40/512;
    for S in sorted(S_data, key = lambda f: f['GPS'][0]['timestamp']):
        if S['GPS'] is not None:
            # if S['GPS'][0]['time_status'] != 20:  # Ignore any 
            T.append(S['GPS'][0]['timestamp'])
            # T.append(S['header_timestamp'])
            # print(datetime.datetime.utcfromtimestamp(S['GPS'][0]['timestamp']), S['exp_num'], datetime.datetime.utcfromtimestamp(S['header_timestamp']))
        else:
            T.append(np.nan)

        E.append(S['E_data'])
        B.append(S['B_data'])


    E = np.array(E); B = np.array(B); T = np.array(T);

    # Sort by time vector:
    # (This may cause issues if the GPS card is off, since everything restarts at 1/6/1980 without a lock.
    # The spacecraft timestamp will be accurate enough when bursts are NOT being taken, but things will get
    # weird during a burst, since the data will have sat in the payload SRAM for a bit before receipt.)
    sort_inds = np.argsort(T)
    E = E[sort_inds, :]; B = B[sort_inds, :]; T = T[sort_inds];

    fig = plt.figure()
    gs = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05)
    ax1 = fig.add_subplot(gs[0,0])
    ax2 = fig.add_subplot(gs[1,0])
    e_cbax = fig.add_subplot(gs[0,1])
    b_cbax = fig.add_subplot(gs[1,1])


    # # Map the log-scaled survey outputs to physical units
    # # This block accounts for the log-scaling and averaging modules,
    # # and delivers dB-full-scale values at each frequency bin.
    # # survey_fullscale = 20*np.log10(pow(2,32))   # 32 bits representing 0 - 1.
    # SF = 256./32. # Equation 5.5 in Austin's thesis. 2^(bits out)/(bits in)

    # # # (This is also where we might bring in a real-world calibration factor)
    # # # E = 20*np.log10(pow(2,E/SF)) - survey_fullscale
    # # # B = 20*np.log10(pow(2,B/SF)) - survey_fullscale

    # # Normalize to full scale at output of averager; take the square root (e.g., divide by 2)
    # # This should range from 0 to 16, with 16 representing a full-scale value - 65535.
    # E = E/SF/2
    # B = B/SF/2


    # # # Linear scale -- square root of the (squared) average value
    # E = pow(2,E)
    # B = pow(2,B)
    # # convert to base 10 dB:
    # E = E/math.log(10,2)
    # B = B/math.log(10,2)
    # # Realistically, we're not going to have any zeroes in the survey data,
    # # due to the noise floor of the uBBR. But let's mask off any infs anyway.
    # E[np.isinf(E)] = -100
    # B[np.isinf(B)] = -100

    logger.info(f'emin: {np.min(E)}, emax: {np.max(E)}')
    logger.info(f'bmin: {np.min(B)}, bmax: {np.max(B)}')

    # clims = [0,255] #[-80,-40]
    # clims = [-40, 0]
    # clims = [0, 16]
    e_clims = [50, 255]
    b_clims = [150, 255]
    t_edges = np.insert(T, 0, T[0] - 26)
    dates = np.array([datetime.datetime.utcfromtimestamp(t) for t in t_edges])
    
    gaps = np.where(np.diff(dates) > datetime.timedelta(seconds=(per_sec+2)))[0]
    d_gapped = np.insert(dates, gaps + 1, dates[gaps] + datetime.timedelta(seconds=per_sec))
    E_gapped = np.insert(E.astype('float'), gaps + 1, np.nan*np.ones([1,512]), axis=0)
    B_gapped = np.insert(B.astype('float'), gaps + 1, np.nan*np.ones([1,512]), axis=0)




    # Plot E data
    # p1 = ax1.pcolorfast(E.T, vmin=clims[0], vmax=clims[1])
    p1 = ax1.pcolormesh(d_gapped,F,E_gapped.T, vmin=e_clims[0], vmax=e_clims[1], shading='flat', cmap = cm);
    # p2 = ax2.pcolorfast(B.T, vmin=clims[0], vmax=clims[1])
    p2 = ax2.pcolormesh(d_gapped,F,B_gapped.T, vmin=b_clims[0], vmax=b_clims[1], shading='flat', cmap = cm);
    cb1 = plt.colorbar(p1, cax = e_cbax)
    cb2 = plt.colorbar(p2, cax = b_cbax)
    cb1.set_label(f'Raw value [{e_clims[0]}-{e_clims[1]}]')
    cb2.set_label(f'Raw value [{b_clims[0]}-{b_clims[1]}]')
    # vertical lines at each edge (kinda nice, but messy for big plots)
    # g1 = ax1.vlines(dates, 0, 40, linewidth=0.2, alpha=0.5, color='w')
    # g2 = ax2.vlines(dates, 0, 40, linewidth=0.2, alpha=0.5, color='w')

    ax1.set_xticklabels([])
    ax1.set_ylim([0,40])
    ax2.set_ylim([0,40])

    formatter = mdates.DateFormatter('%H:%M:%S')
    ax2.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()
    ax2.set_xlabel("Time (H:M:S) on \n%s"%datetime.datetime.utcfromtimestamp(T[0]).strftime("%Y-%m-%d"))

    ax1.set_ylabel('E channel\nFrequency [kHz]')
    ax2.set_ylabel('B channel\nFrequency [kHz]')
    
    
    fig.suptitle(f'VPM Survey Data\n {datetime.datetime.utcfromtimestamp(T[0])} -- {datetime.datetime.utcfromtimestamp(T[-1])}')
    # gs.tight_layout(fig)
    
    if show_plots:
        plt.show()
    fig.savefig(filename, bbox_inches='tight')







    # print(f"Clicked on {len(x_inds)} events")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="VPM Ground Support Software -- Survey data plotter")

    parser.add_argument("--input","--in",  required=True, type=str, default = 'input', help="path to an input XML file")
    parser.add_argument("--output","--out", required=False, type=str, default='survey_data.png', help="output filename. Suffix defines file type (pdf, png)")

    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--debug", dest='debug', action='store_true', help ="Debug mode (extra chatty)")
    g.set_defaults(debug=False)

    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--interactive_plots", dest='show_plots', action='store_true', help ="Plot interactively")
    g.set_defaults(interactive_plots=False)

    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--show_metadata", dest='show_metadata', action='store_true', help ="Plot GPS metadata along with E and B spectrograms")
    g.set_defaults(show_metadata=False)

    args = parser.parse_args()



    from tkinter import filedialog
    from tkinter import *

    root = Tk()
    root.filename =  filedialog.askopenfilename(title = "Select file",filetypes = (("jpeg files","*.jpg"),("all files","*.*")))
    print (root.filename)


    #  ----------- Start the logger -------------
    # log_filename = os.path.join(out_root, 'log.txt')
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
    else:
        logging.basicConfig(level=logging.INFO,  format='[%(name)s]\t%(levelname)s\t%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    

    if os.path.exists(args.input):  
        # Load it
        logging.info(f'Loading file {args.input}')
        dd = read_survey_XML(args.input)

        # Plot it
        # plot_survey_data(dd,args.output, args.show_plots)
        if args.show_metadata:
            logging.info(f'Plotting data and metadata')
            plot_survey_data_and_metadata(dd, filename=args.output, show_plots = args.show_plots)
        else:
            logging.info(f'Plotting data only')
            plot_survey_data(dd, filename = args.output, show_plots = args.show_plots)
    else:
        logging.warning(f'Cannot find file {args.input}')


