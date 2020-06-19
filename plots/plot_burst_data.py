import numpy as np
# import matplotlib.pyplot as plt
import pickle
import datetime
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
import scipy.signal
import os
from plots.parula_colormap import parula
import logging
import argparse
from file_handlers import read_burst_XML
from data_handlers import decode_status
from data_handlers import decode_uBBR_command
import pickle

def plot_burst_TD(fig, burst, cal_data = None):
    
    logger = logging.getLogger("plot_burst_TD")

    # # --------------- Latex Plot Beautification --------------------------
    # fig_width = 10 
    # fig_height = 8
    # fig_size =  [fig_width+1,fig_height+1]
    # params = {'backend': 'ps',
    #           'axes.labelsize': 12,
    #           'font.size': 12,
    #           'legend.fontsize': 10,
    #           'xtick.labelsize': 10,
    #           'ytick.labelsize': 10,
    #           'text.usetex': False,
    #           'figure.figsize': fig_size}
    # plt.rcParams.update(params)
    # # --------------- Latex Plot Beautification --------------------------

    # if cal_file:    
    #     try:
    #         with open(cal_file,'rb') as file:
    #             logger.debug(f'loading calibration file {cal_file}')
    #             cal_data = pickle.load(file)
    #     except:
    #         logger.warning(f'Failed to load calibration file {cal_file}')
    #         cal_file = None

    # A list of bursts!
    # for ind, burst in enumerate(B_data):
    # for burst in [B_data[1]]:
    cfg = burst['config']

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

    if cal_data and bbr_config:
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
        # fig = plt.figure()
        gs = GridSpec(2, 3, width_ratios=[20, 20, 1],  wspace = 0.2, hspace = 0.1)
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

    # # Save it!
    # if ind == 0:
    #     fname = filename
    # else:
    #     components = os.path.splitext(filename)
    #     fname = components[0] + f"_{ind}" + components[1]

    # fig.savefig(fname, bbox_inches='tight')


def plot_burst_FD(fig, burst, cal_data = None):
    logger = logging.getLogger('plot_burst_FD')

    logger.debug(burst['config'])
    cfg = burst['config']

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



    if cfg['TD_FD_SELECT'] == 0:
# --------- Frequency domain plots  -----------
        # fig = plt.figure()
        gs = GridSpec(2, 2, width_ratios=[20, 1],  wspace = 0.05, hspace = 0.05)
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
        # print(np.max(Emag), np.max(Bmag))
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

if __name__ == '__main__':


    parser = argparse.ArgumentParser(description="VPM Ground Support Software\nBurst Plotter")
    
    parser.add_argument("--inp","--input","-i",  required=False, type=str, default = "decoded_data.pkl", help="input file (pickle, xml, or netCDF)")
    parser.add_argument("--out","--output","-o",  required=False, type=str, default = "burst.png", help="output filename. Suffix defines the file type (png, jpg)")
    parser.add_argument("--logfile", required=False, type=str, default=None, help="log filename. If not provided, output is logged to console")
    parser.add_argument("--calfile","--cal_file","--cal", required=False, type=str, default="calibration_data.pkl",
                         help="Path to calibration data (a .pkl file). If no data provided, plots will reference volts at the ADCs")

    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--interactive_plots", dest='int_plots', action='store_true', help ="Show plots interactively")
    g.set_defaults(int_plots=False)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, filename = args.logfile, format='[%(name)s]\t%(levelname)s\t%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    logging.info("plotting burst data...")

    infile = args.inp
    outfile = args.out

    infile_parts = os.path.splitext(infile)

    logging.info(f'Loading {infile}')

    if infile_parts[-1] =='.pkl':
        with open(infile,"rb") as f:
            d = pickle.load(f)
            B_data = d['burst']
    elif infile_parts[-1] == '.xml':
        B_data = read_burst_XML(infile)
    elif infile_parts[-1] == '.nc':
        logging.warning("reading netCDFs not yet implemented!")

    plot_burst_data(B_data, outfile, show_plots = args.int_plots)
