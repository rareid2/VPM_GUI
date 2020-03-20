import tkinter as tk # Python 3.x
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib.cm import get_cmap
import datetime
import logging
from data_handlers import decode_burst_command, decode_status
from parula_colormap import parula


import pickle
import matplotlib.gridspec as GS
import matplotlib.dates as mdates
import scipy.signal
import os
import math

try:
    from mpl_toolkits.basemap import Basemap
except:
    import os
    import conda

    conda_file_dir = conda.__file__
    conda_dir = conda_file_dir.split('lib')[0]
    proj_lib = os.path.join(os.path.join(conda_dir, 'share'), 'proj')
    os.environ["PROJ_LIB"] = proj_lib
    from mpl_toolkits.basemap import Basemap
# from mpl_toolkits.basemap import Basemap
from scipy.interpolate import interp1d, interp2d


def packet_inspector(parent, packets):
    logger = logging.getLogger(__name__)
    

    figure_window = tk.Toplevel(parent)
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
    fig = Figure()
    ax = fig.add_subplot(111)

    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    taxis = np.arange(len(packets))    
    tstamps = np.array([p['header_timestamp'] for p in packets])
    dtypes  = np.array([p['dtype'] for p in packets])

    ax.plot(taxis[dtypes=='E'], tstamps[dtypes=='E'],'.', label='E',      picker=5)
    ax.plot(taxis[dtypes=='B'], tstamps[dtypes=='B'],'.', label='B',      picker=5)
    ax.plot(taxis[dtypes=='G'], tstamps[dtypes=='G'],'.', label='GPS',    picker=5)
    ax.plot(taxis[dtypes=='I'], tstamps[dtypes=='I'],'o', label='Status', picker=5)
    ax.plot(taxis[dtypes=='S'], tstamps[dtypes=='S'],'.', label='Survey', picker=5)

    ax.hlines([p['header_timestamp'] for p in I_packets], 0, len(packets))
    ax.legend()
    ax.set_xlabel('arrival index')
    ax.set_ylabel('timestamp')

    fig.canvas.mpl_connect('pick_event', lambda event: onpick(event, packets))
    fig.suptitle('VPM Packet Inspector Tool')
    def onpick(event, packets):
        ''' Click handler '''
        thisline = event.artist
        xdata = thisline.get_xdata()
        ydata = thisline.get_ydata()
        ind = event.ind
        x_inds = xdata[ind]
        logger.info(x_inds)

        logger.info(f"Clicked on {len(x_inds)} events")
        if x_inds:
            x = xdata[ind[0]]
            # for x in x_inds:
            logger.info(f'packet {x}:')
            logger.info(f"\tdtype: {packets[x]['dtype']}")
            logger.info(f"\theader timestamp: {packets[x]['header_timestamp']}" +\
            f" ({datetime.datetime.utcfromtimestamp(packets[x]['header_timestamp'])})")
            logger.info(f"\tExp num: {packets[x]['exp_num']}")
            logger.info(f"\tData indexes: [{packets[x]['start_ind']}:" +\
                f"{packets[x]['start_ind'] + packets[x]['bytecount']}]")

            if packets[x]['dtype']=='I':
                stat = decode_status([packets[x]])
                logger.info(stat[0])
                # Get burst configuration parameters:
                cmd = np.flip(packets[x]['data'][12:15])
                burst_config = decode_burst_command(cmd)
                logger.info(burst_config)

            if (packets[x]['dtype']=='G') and (packets[x]['start_ind']==0):
                # First GPS packet -- burst command is echoed here
                cmd = np.flip(packets[x]['data'][0:3])
                burst_config = decode_burst_command(cmd)
                logger.info(burst_config)


    return True

def plot_survey_data(parent, S_data, cal_file=None, E_gain=False, B_gain=False, bus_timestamps=False):
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

    # Start the logger
    logger = logging.getLogger(__name__)
    # Ideally would look this up. This sets the maximum time 
    # where we'll insert a column of NaNs, to mark off missing data
    per_sec = 26 

    figure_window = tk.Toplevel(parent)

    # colormap -- parula is Matlab; also try plt.cm.jet or plt.cm.viridis
    cm = parula();

    logger.info(f'Cal file: {cal_file}, E_gain {E_gain}, B_gain {B_gain}')
    # Abandon if we don't have any data to plot
    if S_data is None:
        logger.info('No survey data present!')
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

    # fig = plt.figure()

    fig = Figure()
    # ax = fig.add_subplot(111)

    gs = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05)
    ax1 = fig.add_subplot(gs[0,0])
    ax2 = fig.add_subplot(gs[1,0])
    e_cbax = fig.add_subplot(gs[0,1])
    b_cbax = fig.add_subplot(gs[1,1])

    e_clims = [50, 255]
    b_clims = [150, 255]

    if cal_file:
        try:
            with open(cal_file,'rb') as file:
                logger.debug(f'loading calibration file {cal_file}')
                cal_data = pickle.load(file)
        except:
            logger.warning(f'Failed to load calibration file {cal_file}')
            cal_file = None
    
    if cal_file:

        # Map the log-scaled survey outputs to physical units
        # This block accounts for the log-scaling and averaging modules,
        # and delivers dB-full-scale values at each frequency bin.
        # survey_fullscale = 20*np.log10(pow(2,32))   # 32 bits representing 0 - 1.
        SF = 256./32. # Equation 5.5 in Austin's thesis. 2^(bits out)/(bits in)

        # # (This is also where we might bring in a real-world calibration factor)
        # # E = 20*np.log10(pow(2,E/SF)) - survey_fullscale
        # # B = 20*np.log10(pow(2,B/SF)) - survey_fullscale

        # Normalize to full scale at output of averager; take the square root (e.g., divide by 2)
        # This should range from 0 to 16, with 16 representing a full-scale value - 65535.
        E = E/SF/2
        B = B/SF/2


        # # Linear scale -- square root of the (squared) average value
        E = pow(2,E)
        B = pow(2,B)
        # convert to base 10 dB:
        E = E/math.log(10,2)
        B = B/math.log(10,2)
        # Realistically, we're not going to have any zeroes in the survey data,
        # due to the noise floor of the uBBR. But let's mask off any infs anyway.
        E[np.isinf(E)] = -100
        B[np.isinf(B)] = -100

    # ---------- Calibration coefficients ------
        ADC_max_value = 32768. # 16 bits, twos comp
        ADC_max_volts = 1.0    # ADC saturates at +- 1 volt

        E_coef = ADC_max_volts/ADC_max_value  # [Volts at ADC / ADC bin]
        B_coef = ADC_max_volts/ADC_max_value

        
        td_lims = [-1, 1]
        E_cal_curve = cal_data[('E',False, E_gain)] # Hey! The filter changes the gain too, add that as an input
        B_cal_curve = cal_data[('B',False, B_gain)]
        E_coef *= 1000.0/max(E_cal_curve) # [(mV/m) / Vadc]
        B_coef *= 1.0/max(B_cal_curve) # [(nT) / Vadc]
        E_unit_string = 'mV/m @ Antenna'
        B_unit_string = 'nT'

        logger.debug(f'E calibration coefficient is {E_coef} mV/m per bit')
        logger.debug(f'B calibration coefficient is {B_coef} nT per bit')
    else:
        E_unit_string = 'V @ ADC'
        B_unit_string = 'V @ ADC'

        E_coef = 1
        B_coef = 1
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

    E_gapped*=E_coef
    B_gapped*=B_coef

    # Plot E data
    # p1 = ax1.pcolorfast(E.T, vmin=clims[0], vmax=clims[1])
    p1 = ax1.pcolormesh(d_gapped,F,E_gapped.T, vmin=e_clims[0], vmax=e_clims[1], shading='flat', cmap = cm);
    # p2 = ax2.pcolorfast(B.T, vmin=clims[0], vmax=clims[1])
    p2 = ax2.pcolormesh(d_gapped,F,B_gapped.T, vmin=b_clims[0], vmax=b_clims[1], shading='flat', cmap = cm);
    cb1 = fig.colorbar(p1, cax = e_cbax)
    cb2 = fig.colorbar(p2, cax = b_cbax)
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
    
    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

def plot_survey_data_and_metadata(parent, S_data, 
    line_plots = ['Lshell','altitude','velocity','lat','lon','used_sats','solution_status','solution_type'],
    cal_file=None, E_gain=False, B_gain=False, bus_timestamps=False, plot_map = True):
    # Only import Basemap for this function -- not sure if AFRL can install it yet


    logger = logging.getLogger(__name__)

    figure_window = tk.Toplevel(parent)

    fig = Figure(figsize=(12,8))

    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    if plot_map or (len(line_plots) > 0):
        # The full plot: 
        gs_root = GS.GridSpec(2, 2, height_ratios=[1,2.5], width_ratios=[1,1.5],  wspace = 0.2, hspace = 0.1, figure=fig)
        gs_data = GS.GridSpecFromSubplotSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, subplot_spec=gs_root[:,1])
        m_ax = fig.add_subplot(gs_root[0,0])
    else:
        gs_data = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, figure = fig)



    # colormap -- parula is a clone of the Matlab colormap; also try plt.cm.jet or plt.cm.viridis
    cm = parula(); #plt.cm.viridis;


    # Subset of data with GPS stamps included.
    # We need these for the line plots, regardless if we're using payload or bus timestamps.
    S_with_GPS = list(filter(lambda x: 'timestamp' in x['GPS'][0], S_data))
    T_gps = np.array([x['GPS'][0]['timestamp'] for x in S_with_GPS])
    dts_gps = np.array([datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc) for x in T_gps])


    # Build arrays
    E = []
    B = []
    F = np.arange(512)*40/512;
    
    # # Only plot survey data if we have GPS data to match
    # S_filt = list(filter(lambda x: 'timestamp' in x['GPS'][0], S_data))
    if bus_timestamps:
        logger.info('Using bus timestamps')
        # Sort using bus timestamp (finer resolution, but includes transmission error
        # from payload to bus)
        T = np.array([x['header_timestamp'] for x in S_data])
        dts = np.array([datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc) for x in T])
        for S in sorted(S_data, key = lambda f: f['header_timestamp']):
            E.append(S['E_data'])
            B.append(S['B_data'])
    else:
        logger.info('using payload timestamps')
        # Sort using payload GPS timestamp (rounded to nearest second)
        T = T_gps
        dts = dts_gps
        for S in sorted(S_with_GPS, key = lambda f: f['GPS'][0]['timestamp']):
            E.append(S['E_data'])
            B.append(S['B_data'])



    # -----------------------------------
    # Spectrograms
    # -----------------------------------
    E = np.array(E); B = np.array(B); T = np.array(T);
    logger.debug(f'E has shape {np.shape(E)}, B has shape {np.shape(B)}')

    # # Sort by time vector:
    # # (This may cause issues if the GPS card is off, since everything restarts at 1/6/1980 without a lock.
    # # The spacecraft timestamp will be accurate enough when bursts are NOT being taken, but things will get
    # # weird during a burst, since the data will have sat in the payload SRAM for a bit before receipt.)
    # sort_inds = np.argsort(T)
    # E = E[sort_inds, :]; B = B[sort_inds, :]; T = T[sort_inds];

    # gs_data = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, subplot_spec=gs_root[1])
    ax1 = fig.add_subplot(gs_data[0,0])
    ax2 = fig.add_subplot(gs_data[1,0], sharex=ax1, sharey=ax1)
    e_cbax = fig.add_subplot(gs_data[0,1])
    b_cbax = fig.add_subplot(gs_data[1,1])

    e_clims = [50,255] #[0,255] #[-80,-40]
    b_clims = [150,255] #[0,255] #[-80,-40]

    t_edges = np.insert(T, 0, T[0] - 26)
    dates = np.array([datetime.datetime.utcfromtimestamp(t) for t in t_edges])

    # Insert columns of NaNs wherever we have gaps in data (dt > 27 sec)
    per_sec = 26 # Might want to look this up for the shorter survey modes
    gaps = np.where(np.diff(dates) > datetime.timedelta(seconds=(per_sec+2)))[0]
    d_gapped = np.insert(dates, gaps + 1, dates[gaps] + datetime.timedelta(seconds=per_sec))
    E_gapped = np.insert(E.astype('float'), gaps + 1, np.nan*np.ones([1,512]), axis=0)
    B_gapped = np.insert(B.astype('float'), gaps + 1, np.nan*np.ones([1,512]), axis=0)


    # Plot E data
    p1 = ax1.pcolormesh(d_gapped,F,E_gapped.T, vmin=e_clims[0], vmax=e_clims[1], shading='flat', cmap = cm);
    p2 = ax2.pcolormesh(d_gapped,F,B_gapped.T, vmin=b_clims[0], vmax=b_clims[1], shading='flat', cmap = cm);
    cb1 = fig.colorbar(p1, cax = e_cbax)
    cb2 = fig.colorbar(p2, cax = b_cbax)
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

    # -----------------------------------
    # Ground track Map
    # -----------------------------------

    lats = [x['GPS'][0]['lat'] for x in S_with_GPS]
    lons = [x['GPS'][0]['lon'] for x in S_with_GPS]
    alts = np.array([x['GPS'][0]['alt'] for x in S_with_GPS])/1000.
    v_horiz = np.array([x['GPS'][0]['horiz_speed'] for x in S_with_GPS])
    v_vert = np.array([x['GPS'][0]['vert_speed'] for x in S_with_GPS])
    vel = np.sqrt(v_horiz*v_horiz + v_vert*v_vert)/1000.

    if plot_map:
        m = Basemap(projection='mill',lon_0=0,ax=m_ax, llcrnrlon=-180,llcrnrlat=-70,urcrnrlon=180,urcrnrlat=70)

        sx,sy = m(lons, lats)


        m.drawcoastlines(color='k',linewidth=1,ax=m_ax);
        m.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0]);
        m.drawmeridians(np.arange(m.lonmin,m.lonmax+30,60),labels=[0,0,1,0]);
        m.drawmapboundary(fill_color='cyan');
        m.fillcontinents(color='white',lake_color='cyan');
        s = m.scatter(sx,sy,c=T_gps, marker='.', s=10, cmap = get_cmap('plasma'), zorder=100, picker=5)

        # cb = m.colorbar(s, location='bottom', label='Time')

        # ticks = [T[0], T[-1]]
        # cb.set_ticks(ticks)
        # tl = [datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc).strftime('%D\n%H:%m:%S') for x in cb.get_ticks()]
        # cb.set_ticklabels(tl)

        # Enable click events on the map:
        def onpick(event):
            ''' Event handler for a point click '''
            ind = event.ind
            t_center = dts[ind[0]]
            logger.info(f't = {t_center}')
            ax_lines[-1].set_xlim(t_center - datetime.timedelta(minutes=15), t_center + datetime.timedelta(minutes=15))
            fig.canvas.draw()

        # tx, ty = m(-175,-60)
        # m_ax.text(tx, ty, 'Click to zoom')

        cid= fig.canvas.mpl_connect('pick_event', lambda event: onpick(event))
    # -----------------------------------
    # Line plots
    # -----------------------------------
    if len(line_plots) > 0:
        gs_lineplots = GS.GridSpecFromSubplotSpec(len(line_plots), 1, hspace=0.5, subplot_spec=gs_root[1,0])

        ax_lines = []

        # print(S_data[0]['GPS'][0].keys())
        for ind, a in enumerate(line_plots):
            ax_lines.append(fig.add_subplot(gs_lineplots[ind]))

        markersize = 4
        markerface = '.'
        markeralpha= 0.6
        for ind, a in enumerate(line_plots):
            
            if a in S_with_GPS[0]['GPS'][0]:
                yvals = np.array([x['GPS'][0][a] for x in S_with_GPS])
                ax_lines[ind].plot(dts_gps, yvals,markerface, markersize=markersize, label=a, alpha=markeralpha)
                ax_lines[ind].set_ylabel(a, rotation=0, labelpad=30)
            elif a in 'altitude':
                yvals = np.array([x['GPS'][0]['alt'] for x in S_with_GPS])/1000.
                ax_lines[ind].plot(dts_gps, yvals,markerface, markersize=markersize, label=a, alpha=markeralpha)
                ax_lines[ind].set_ylabel('Altitude\n[km]', rotation=0, labelpad=30)
                ax_lines[ind].set_ylim([450,500])
            elif a in 'dt':
                ax_lines[ind].plot(dts_gps, T - T_gps,markerface, markersize=markersize, label=a, alpha=markeralpha)
                ax_lines[ind].set_ylabel(r't$_{header}$ - t$_{GPS}$',  rotation=0, labelpad=30)
            elif a in 'velocity':
                ax_lines[ind].plot(dts_gps, vel,markerface, markersize=markersize, alpha=markeralpha, label='Velocity')
                ax_lines[ind].set_ylabel('Velocity\n[km/sec]', rotation=0, labelpad=30)
                ax_lines[ind].set_ylim([5,10])
            elif a in 'Lshell':
                # This way using a precomputed lookup table:
                with open('Lshell_dict.pkl','rb') as file:
                    Ldict = pickle.load(file)
                L_interp = interp2d(Ldict['glon'], Ldict['glat'], Ldict['L'], kind='cubic')
                Lshell = np.array([L_interp(x,y) for x,y in zip(lons, lats)])
                
                ax_lines[ind].plot(dts_gps, Lshell,markerface, markersize=markersize,  alpha=markeralpha, label='L shell')
                ax_lines[ind].set_ylabel('L shell', rotation=0, labelpad=30)
                ax_lines[ind].set_ylim([1,8])

        fig.autofmt_xdate()


        for a in ax_lines[:-1]:
            a.set_xticklabels([])
            
        # Link line plot x axes:
        for a in ax_lines:
            ax_lines[0].get_shared_x_axes().join(ax_lines[0], a)

        # Link data x axes:
        ax_lines[0].get_shared_x_axes().join(ax_lines[0], ax1)
        ax_lines[0].get_shared_x_axes().join(ax_lines[0], ax2)

        ax_lines[-1].set_xticklabels(ax_lines[-1].get_xticklabels(), rotation=30)
        ax_lines[-1].xaxis.set_major_formatter(formatter)
        ax_lines[-1].set_xlabel("Time (H:M:S) on \n%s"%datetime.datetime.utcfromtimestamp(T[0]).strftime("%Y-%m-%d"))


        ax_lines[-1].set_xlim([np.min(dts), np.max(dts)])


    fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.12)
    fig.suptitle(f"VPM Survey Data\n {dts[0].strftime('%D%, %H:%m:%S')} -- {dts[-1].strftime('%D%, %H:%m:%S')}")

    



def plot_burst_data(parent, burst, cal_file=None):

    logger = logging.getLogger(__name__)
    
    figure_window = tk.Toplevel(parent)

    fig = Figure(figsize=(12,8))

    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)


    if cal_file:    
        try:
            with open(cal_file,'rb') as file:
                logger.debug(f'loading calibration file {cal_file}')
                cal_data = pickle.load(file)
        except:
            logger.warning(f'Failed to load calibration file {cal_file}')
            cal_file = None

    # A list of bursts!
    # for ind, burst in enumerate(B_data):
    # for burst in [B_data[1]]:
    logger.debug(burst['config'])
    cfg = burst['config']

    logger.info(f'plotting burst...')
    logger.info(f'burst configuration: {cfg}')

    system_delay_samps_TD = 73;    
    system_delay_samps_FD = 200;
    fs = 80000;
    # cm = plt.cm.jet
    cm = parula();  # This is a mockup of the current Matlab colormap (which is proprietary)


    # Check if we have any status packets included -- we'll get
    # the uBBR configuration from these.
    if 'bbr_config' in burst:
        bbr_config =burst['bbr_config']
    elif 'I' in burst:
        logger.debug(f"Found {len(burst['I'])} status packets")
            # Get uBBR config command:
        if 'prev_bbr_command' in burst['I'][0]:
            bbr_config = decode_uBBR_command(burst['I'][0]['prev_bbr_command'])
        else:
            ps = decode_status([burst['I'][0]])
            bbr_config = decode_uBBR_command(ps[0]['prev_bbr_command'])
        logger.debug(f'bbr config is: {bbr_config}')
    else:
        logger.warning(f'No bbr configuration found')
        bbr_config = None

    # ---------- Calibration coefficients ------
    ADC_max_value = 32768. # 16 bits, twos comp
    ADC_max_volts = 1.0    # ADC saturates at +- 1 volt

    E_coef = ADC_max_volts/ADC_max_value  # [Volts at ADC / ADC bin]
    B_coef = ADC_max_volts/ADC_max_value

    if cal_file and bbr_config:
        td_lims = [-1, 1]
        E_cal_curve = cal_data[('E',bool(bbr_config['E_FILT']), bool(bbr_config['E_GAIN']))]
        B_cal_curve = cal_data[('B',bool(bbr_config['B_FILT']), bool(bbr_config['B_GAIN']))]
        E_coef *= 1000.0/max(E_cal_curve) # [(mV/m) / Vadc]
        B_coef *= 1.0/max(B_cal_curve) # [(nT) / Vadc]
        E_unit_string = 'mV/m @ Antenna'
        B_unit_string = 'nT'

        logger.debug(f'E calibration coefficient is {E_coef} mV/m per bit')
        logger.debug(f'B calibration coefficient is {B_coef} nT per bit')
    else:
        E_unit_string = 'V @ ADC'
        B_unit_string = 'V @ ADC'

    # Scale the spectrograms -- A perfect sine wave will have ~-3dB amplitude.
    # Scaling covers 14 bits of dynamic range, with a maximum at each channel's theoretical peak
    clims = np.array([-6*14, -3]) #[-96, -20]
    e_clims = clims + 20*np.log10(E_coef*ADC_max_value/ADC_max_volts)
    b_clims = clims + 20*np.log10(B_coef*ADC_max_value/ADC_max_volts)

    # Generate time axis


    if cfg['TD_FD_SELECT'] == 1:
    # --------- Time domain plots  -----------

        gs = GS.GridSpec(2, 3, width_ratios=[20, 20, 1],  wspace = 0.2, hspace = 0.1)
        E_TD = fig.add_subplot(gs[0,0])
        B_TD = fig.add_subplot(gs[1,0], sharex=E_TD)
        E_FD = fig.add_subplot(gs[0,1], sharex=E_TD)
        B_FD = fig.add_subplot(gs[1,1], sharex=E_FD)
        cb1  = fig.add_subplot(gs[0,2])
        cb2  = fig.add_subplot(gs[1,2])



        # Construct the appropriate time and frequency axes
        # Get the equivalent sample rate, if decimated
        if cfg['DECIMATE_ON']==1:
            fs_equiv = 80000./cfg['DECIMATION_FACTOR']
        else:
            fs_equiv = 80000.

        if cfg['SAMPLES_OFF'] == 0:
            max_ind = max(len(burst['E']), len(burst['B']))
            t_axis = np.arange(max_ind)/fs_equiv
        else:

            # Seconds from the start of the burst
            t_axis = np.array([(np.arange(cfg['SAMPLES_ON']))/fs_equiv +\
                          (k*(cfg['SAMPLES_ON'] + cfg['SAMPLES_OFF']))/fs_equiv for k in range(cfg['burst_pulses'])]).ravel()

        # Add in system delay 
        t_axis += system_delay_samps_TD/fs_equiv 

        # Get the timestamp at the beginning of the burst.
        # GPS timestamps are taken at the end of each contiguous recording.
        # (I think "samples on" is still undecimated, regardless if decimation is being used...)
        start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=float(cfg['SAMPLES_ON']/fs))

        # the "samples on" and "samples off" values are counting at the full rate, not the decimated rate.
        sec_on  = cfg['SAMPLES_ON']/fs
        sec_off = cfg['SAMPLES_OFF']/fs
        

        E_TD.plot(t_axis[0:len(burst['E'])], E_coef*burst['E'])
        B_TD.plot(t_axis[0:len(burst['B'])], B_coef*burst['B'])


        # E_TD.set_ylim(td_lims)
        # B_TD.set_ylim(td_lims)

        nfft=1024;
        overlap = 0.5
        window = 'hanning'

        
        if cfg['SAMPLES_OFF'] == 0:
            E_td_spaced = E_coef*burst['E']
            B_td_spaced = B_coef*burst['B']
        else:
            # Insert nans into vector to account for "off" time sections
            E_td_spaced = []
            B_td_spaced = []
            
            for k in np.arange(cfg['burst_pulses']):
                E_td_spaced.append(E_coef*burst['E'][k*cfg['SAMPLES_ON']:(k+1)*cfg['SAMPLES_ON']])
                E_td_spaced.append(np.ones(cfg['SAMPLES_OFF'])*np.nan)
                B_td_spaced.append(B_coef*burst['B'][k*cfg['SAMPLES_ON']:(k+1)*cfg['SAMPLES_ON']])
                B_td_spaced.append(np.ones(cfg['SAMPLES_OFF'])*np.nan)


            E_td_spaced = np.concatenate(E_td_spaced).ravel()
            B_td_spaced = np.concatenate(B_td_spaced).ravel()


        # E spectrogram -- "spectrum" scaling -> V^2; "density" scaling -> V^2/Hz
        ff,tt, FE = scipy.signal.spectrogram(E_td_spaced, fs=fs_equiv, window=window,
                    nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='spectrum')
        E_S_mag = 20*np.log10(np.sqrt(FE))
        E_S_mag[np.isinf(E_S_mag)] = -100
        logger.debug(f'E data min/max: {np.min(E_S_mag)}, {np.max(E_S_mag)}')
        pe = E_FD.pcolorfast(tt,ff/1000,E_S_mag, cmap = cm,  vmin=e_clims[0], vmax=e_clims[1])
        ce = fig.colorbar(pe, cax=cb1)

        # B spectrogram
        ff,tt, FB = scipy.signal.spectrogram(B_td_spaced, fs=fs_equiv, window=window,
                    nperseg=nfft, noverlap=nfft*overlap,mode='psd',scaling='spectrum')
        B_S_mag = 20*np.log10(np.sqrt(FB))
        B_S_mag[np.isinf(B_S_mag)] = -100
        logger.debug(f'B data min/max: {np.min(B_S_mag)}, {np.max(B_S_mag)}')
        pb = B_FD.pcolorfast(tt,ff/1000, B_S_mag, cmap = cm, vmin=b_clims[0], vmax=b_clims[1])
        cb = fig.colorbar(pb, cax=cb2)

        E_TD.set_ylabel(f'E Amplitude\n[{E_unit_string}]')
        B_TD.set_ylabel(f'B Amplitude\n[{B_unit_string}]')
        E_FD.set_ylabel('Frequency [kHz]')
        B_FD.set_ylabel('Frequency [kHz]')
        B_TD.set_xlabel('Time [sec from start]')
        B_FD.set_xlabel('Time [sec from start]')

        ce.set_label(f'dB[{E_unit_string}]')
        cb.set_label(f'dB[{B_unit_string}]')

        if bbr_config:
            fig.suptitle('Time-Domain Burst\n%s - n = %d, %d on / %d off\nE gain = %s, E filter = %s, B gain = %s, B filter = %s'
                %(start_timestamp, cfg['burst_pulses'], sec_on, sec_off, bbr_config['E_GAIN'], bbr_config['E_FILT'], bbr_config['B_GAIN'], bbr_config['B_FILT']))
        else:
            fig.suptitle('Time-Domain Burst\n%s - n = %d, %d on / %d off'
                %(start_timestamp, cfg['burst_pulses'], sec_on, sec_off))


    elif cfg['TD_FD_SELECT'] == 0:
    # --------- Frequency domain plots  -----------
        gs = GS.GridSpec(2, 2, width_ratios=[20, 1],  wspace = 0.05, hspace = 0.05)
        E_FD = fig.add_subplot(gs[0,0])
        B_FD = fig.add_subplot(gs[1,0], sharex=E_FD, sharey=E_FD)
        cb1 = fig.add_subplot(gs[0,1])
        cb2 = fig.add_subplot(gs[1,1])

        nfft = 1024

        # Frequency axis
        f_axis = []
        seg_length = nfft/2/16

        for i, v in enumerate(cfg['BINS'][::-1]):
            if v=='1':
                f_axis.append([np.arange(seg_length)+seg_length*i])
        freq_inds = np.array(f_axis).ravel().astype('int') # stash the row indices here
        f_axis = (40000/(nfft/2))*np.array(f_axis).ravel()
        f_axis_full = np.arange(512)*40000/512;

        logger.debug(f"f axis: {len(f_axis)}")
        
        # E and B are flattened vectors; we need to reshape them into 2d arrays (spectrograms)
        max_E = len(burst['E']) - np.mod(len(burst['E']), len(f_axis))
        E = burst['E'][0:max_E].reshape(int(max_E/len(f_axis)), len(f_axis))*E_coef
        E = E.T
        max_B = len(burst['B']) - np.mod(len(burst['B']), len(f_axis))
        B = burst['B'][0:max_B].reshape(int(max_B/len(f_axis)), len(f_axis))*B_coef
        B = B.T
        
        logger.debug(f"E dims: {np.shape(E)}, B dims: {np.shape(B)}")

        # Generate time axis
        scale_factor = nfft/2./80000.

        sec_on  = np.round(cfg['FFTS_ON']*scale_factor)
        sec_off = np.round(cfg['FFTS_OFF']*scale_factor)

        if cfg['FFTS_OFF'] == 0:
            # GPS packets are taken when stopping data capture -- e.g., at the end of the burst,
            # or transitioning to a "samples off" section. If we're doing back-to-back bursts
            # with no windowing, we'll only have one GPS timestamp instead of burst_pulses.
            max_t_ind = np.shape(E)[1]
            t_inds = np.arange(max_t_ind)
            t_axis_seconds = t_inds*scale_factor
            start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=np.round(t_axis_seconds[-1]))
            t_axis_full_seconds = np.arange(max_t_ind)*scale_factor + system_delay_samps_FD/fs
            t_axis_full_timestamps = burst['G'][0]['timestamp'] - max_t_ind*scale_factor + t_axis_full_seconds

        else:
            t_inds = np.array([(np.arange(cfg['FFTS_ON'])) + (k*(cfg['FFTS_ON'] + cfg['FFTS_OFF'])) for k in range(cfg['burst_pulses'])]).ravel()
            max_t_ind = (cfg['FFTS_ON'] + cfg['FFTS_OFF'])*cfg['burst_pulses']
            start_timestamp = datetime.datetime.utcfromtimestamp(burst['G'][0]['timestamp']) - datetime.timedelta(seconds=np.round(cfg['FFTS_ON']*scale_factor))
            t_axis_full_seconds = np.arange(max_t_ind)*scale_factor + system_delay_samps_FD/fs
            t_axis_full_timestamps = burst['G'][0]['timestamp'] - cfg['FFTS_ON']*scale_factor + t_axis_full_seconds

        # Spectrogram color limits    
        clims = [-96, 0];

        # Log-scaled magnitudes
        Emag = 20*np.log10(np.abs(E))
        Emag[np.isinf(Emag)] = -100
        Bmag = 20*np.log10(np.abs(B))
        Bmag[np.isinf(Bmag)] = -100
        print(np.max(Emag), np.max(Bmag))
        # Spaced spectrogram -- insert nans (or -120 for a blue background) in the empty spaces
        E_spec_full = -120*np.ones([max_t_ind, 512])
        B_spec_full = -120*np.ones([max_t_ind, 512])

        a,b = np.meshgrid(t_inds, freq_inds)

        E_spec_full[a,b] = Emag
        B_spec_full[a,b] = Bmag
        E_spec_full = E_spec_full.T
        B_spec_full = B_spec_full.T          
        
        # Plots!
        pe = E_FD.pcolormesh(t_axis_full_timestamps, f_axis_full/1000, E_spec_full, cmap = cm, vmin=e_clims[0], vmax=e_clims[1])
        pb = B_FD.pcolormesh(t_axis_full_timestamps, f_axis_full/1000, B_spec_full, cmap = cm, vmin=b_clims[0], vmax=b_clims[1])

        # Axis labels and ticks. Label the burst start time, and the GPS timestamps.
        xtix = [t_axis_full_timestamps[0]]
        xtix.extend([x['timestamp'] for x in burst['G']])
        minorticks = np.arange(np.ceil(t_axis_full_timestamps[0]), t_axis_full_timestamps[-1], 5)  # minor tick marks -- 5 seconds
        E_FD.set_xticks(xtix)
        E_FD.set_xticks(minorticks, minor=True)
        B_FD.set_xticks(xtix)
        B_FD.set_xticks(minorticks, minor=True)
        E_FD.set_xticklabels([])
        B_FD.set_xticklabels([datetime.datetime.utcfromtimestamp(x).strftime("%H:%M:%S") for x in xtix])

        fig.autofmt_xdate()

        ce = fig.colorbar(pe, cax=cb1)
        cb = fig.colorbar(pb, cax=cb2)

        E_FD.set_ylim([0, 40])
        B_FD.set_ylim([0, 40])

        E_FD.set_ylabel('E\n Frequency [kHz]')
        B_FD.set_ylabel('B\n Frequency [kHz]')

        # ce.set_label('dBFS')
        # cb.set_label('dBFS')
        ce.set_label(f'dB[{E_unit_string}]')
        cb.set_label(f'dB[{B_unit_string}]')

        # B_FD.set_xlabel('Time [sec from start]')
        B_FD.set_xlabel("Time (H:M:S) on \n%s"%start_timestamp.strftime("%Y-%m-%d"))

        # fig.suptitle(f'Burst {ind}\n{start_timestamp}')    
        if bbr_config:
            fig.suptitle('Frequency-Domain Burst\n%s - n = %d, %d on / %d off\nE gain = %s, E filter = %s, B gain = %s, B filter = %s'
                %(start_timestamp, cfg['burst_pulses'], sec_on, sec_off, bbr_config['E_GAIN'], bbr_config['E_FILT'], bbr_config['B_GAIN'], bbr_config['B_FILT']))
        else:
            fig.suptitle('Frequency-Domain Burst\n%s - n = %d, %d on / %d off'
                %(start_timestamp, cfg['burst_pulses'], sec_on, sec_off))


