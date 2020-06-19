import numpy as np
# import matplotlib.pyplot as plt

import datetime
import matplotlib.gridspec as GS
import matplotlib.dates as mdates
from plots.parula_colormap import parula
import logging
import os
import pickle

try:
    from mpl_toolkits.basemap import Basemap
except:
    # Basemap has trouble finding proj_lib correctly - here's an automated fix
    import os
    import conda

    conda_file_dir = conda.__file__
    conda_dir = conda_file_dir.split('lib')[0]
    proj_lib = os.path.join(os.path.join(conda_dir, 'share'), 'proj')
    os.environ["PROJ_LIB"] = proj_lib
    from mpl_toolkits.basemap import Basemap


from scipy.interpolate import interp1d, interp2d
from matplotlib.cm import get_cmap
from mpl_toolkits.basemap.solar import daynight_terminator


def is_day(t, lats, lons):
    # Determine whether or not the satellite is on the dayside.
    # We're using the day-nite terminator function from Basemap.

    tlons, tlats, tau, dec = daynight_terminator(t, 1.1, -180, 180)

    # Lon to lat interpolator
    interpy = interp1d(tlons, tlats,'linear', fill_value='extrapolate')
    thresh_lats = interpy(lons)
    
    if dec > 0: 
        dayvec = lats > thresh_lats
    else:
        dayvec = lats < thresh_lats
        
    return dayvec

def plot_survey_data_and_metadata(fig, S_data,
                plot_map=True, bus_timestamps=False, t1=None, t2=None,
                line_plots = ['Lshell','altitude','velocity','lat','lon','used_sats','solution_status','solution_type'],
                show_plots=False, lshell_file = 'resources/Lshell_dict.pkl', cal_file = None, E_gain=False, B_gain=False):

    logger = logging.getLogger()

    if plot_map:
        from mpl_toolkits.basemap import Basemap
        from scipy.interpolate import interp1d, interp2d

    if plot_map or (len(line_plots) > 0):
        # The full plot: 
        gs_root = GS.GridSpec(2, 2, height_ratios=[1,2.5], width_ratios=[1,1.5],  wspace = 0.2, hspace = 0.1, figure=fig)
        gs_data = GS.GridSpecFromSubplotSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, subplot_spec=gs_root[:,1])
        m_ax = fig.add_subplot(gs_root[0,0])
    else:
        gs_data = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, figure = fig)

    # colormap -- parula is a clone of the Matlab colormap; also try plt.cm.jet or plt.cm.viridis
    cm = parula(); #plt.cm.viridis;

    # Sort by header timestamps
    S_data = sorted(S_data, key = lambda f: f['header_timestamp'])

    # Subset of data with GPS stamps included.
    # We need these for the line plots, regardless if we're using payload or bus timestamps.
    # Also confirm that we have at least one field from BESTPOS and BESTVEL messages,
    # since on rare occasions we miss one or the other.
    S_with_GPS = list(filter(lambda x: (('GPS' in x) and 
                                        ('timestamp' in x['GPS'][0]) and
                                        ('lat' in x['GPS'][0]) and
                                        ('horiz_speed' in x['GPS'][0])), S_data))
    S_with_GPS = sorted(S_with_GPS, key = lambda f: f['GPS'][0]['timestamp'])

    logger.info(f'{len(S_with_GPS)} GPS packets')
    T_gps = np.array([x['GPS'][0]['timestamp'] for x in S_with_GPS])
    dts_gps = np.array([datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc) for x in T_gps])

    # Build arrays
    E = []
    B = []
    T = []
    F = np.arange(512)*40/512;
    
    # # Only plot survey data if we have GPS data to match
    if bus_timestamps:
        logger.info('Using bus timestamps')
        # Sort using bus timestamp (finer resolution, but 
        # includes transmission error from payload to bus)
        for S in S_data:
            T.append(S['header_timestamp'])
            E.append(S['E_data'])
            B.append(S['B_data'])
    else:
        logger.info('using payload timestamps')
        # Sort using payload GPS timestamp (rounded to nearest second.
        # Ugh, why didn't we just save a local microsecond counter... do that on CANVAS please)
        for S in S_with_GPS:
            T.append(S['GPS'][0]['timestamp'])
            E.append(S['E_data'])
            B.append(S['B_data'])
    T = np.array(T)

    dates = np.array([datetime.datetime.utcfromtimestamp(t) for t in T])

    if t1 is None:
        t1 = dates[0]
    if t2 is None:
        t2 = dates[-1]
    # -----------------------------------
    # Spectrograms
    # -----------------------------------
    E = np.array(E); B = np.array(B); T = np.array(T);
    logger.debug(f'E has shape {np.shape(E)}, B has shape {np.shape(B)}')

    # gs_data = GS.GridSpec(2, 2, width_ratios=[20, 1], wspace = 0.05, hspace = 0.05, subplot_spec=gs_root[1])
    ax1 = fig.add_subplot(gs_data[0,0])
    ax2 = fig.add_subplot(gs_data[1,0], sharex=ax1, sharey=ax1)
    e_cbax = fig.add_subplot(gs_data[0,1])
    b_cbax = fig.add_subplot(gs_data[1,1])

    e_clims = [50,255] #[0,255] #[-80,-40]
    b_clims = [150,255] #[0,255] #[-80,-40]

    date_edges = np.insert(dates, 0, dates[0] - datetime.timedelta(seconds=26))

    # Insert columns of NaNs wherever we have gaps in data (dt > 27 sec)
    per_sec = 26 # Might want to look this up for the shorter survey modes
    gaps = np.where(np.diff(date_edges) > datetime.timedelta(seconds=(per_sec+2)))[0]

    d_gapped = np.insert(dates, gaps, dates[gaps] - datetime.timedelta(seconds=per_sec + 3))
    E_gapped = np.insert(E.astype('float'), gaps - 1, np.nan*np.ones([1,512]), axis=0)
    B_gapped = np.insert(B.astype('float'), gaps - 1, np.nan*np.ones([1,512]), axis=0)

    # Plot E data
    p1 = ax1.pcolormesh(d_gapped,F,E_gapped.T, vmin=e_clims[0], vmax=e_clims[1], shading='flat', cmap = cm);
    p2 = ax2.pcolormesh(d_gapped,F,B_gapped.T, vmin=b_clims[0], vmax=b_clims[1], shading='flat', cmap = cm);
    cb1 = fig.colorbar(p1, cax = e_cbax)
    cb2 = fig.colorbar(p2, cax = b_cbax)
    cb1.set_label(f'Raw value [{e_clims[0]}-{e_clims[1]}]')
    cb2.set_label(f'Raw value [{b_clims[0]}-{b_clims[1]}]')

    # # vertical lines at each edge (kinda nice, but messy for big plots)
    # g1 = ax1.vlines(dates, 0, 40, linewidth=0.2, alpha=0.5, color='w')
    # g2 = ax2.vlines(dates, 0, 40, linewidth=0.2, alpha=0.5, color='w')

    ax1.set_xticklabels([])
    ax1.set_ylim([0,40])
    ax2.set_ylim([0,40])

    formatter = mdates.DateFormatter('%H:%M:%S')
    ax2.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()
    ax2.set_xlabel("Time (H:M:S) on \n%s"%datetime.datetime.utcfromtimestamp(T[0]).strftime("%Y-%m-%d"))
    # ax2.set_xlabel("Time (H:M:S)")

    ax1.set_ylabel('E channel\nFrequency [kHz]')
    ax2.set_ylabel('B channel\nFrequency [kHz]')

    # -----------------------------------
    # Ground track Map
    # -----------------------------------

    if plot_map:
        m = Basemap(projection='mill',lon_0=0,ax=m_ax, llcrnrlon=-180,llcrnrlat=-70,urcrnrlon=180,urcrnrlat=70)
        lats = [x['GPS'][0]['lat'] for x in S_with_GPS]
        lons = [x['GPS'][0]['lon'] for x in S_with_GPS]

        sx,sy = m(lons, lats)


        m.drawcoastlines(color='k',linewidth=1,ax=m_ax);
        m.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0]);
        m.drawmeridians(np.arange(m.lonmin,m.lonmax+30,60),labels=[0,0,1,0]);
        m.drawmapboundary(fill_color='cyan');
        m.fillcontinents(color='white',lake_color='cyan');

        # This is sloppy -- we need to stash the scatterplot in a persistent object,
        # but because this is just a script and not a class, it vanishes. So we're
        # sticking it into the top figure for now. (This is so we can update the point
        # visibility when zooming in and out in the GUI)
        m_ax.s = m.scatter(sx,sy,c=T_gps, marker='.', s=10, cmap = get_cmap('plasma'), zorder=100, picker=5)
        
        hits = np.where(dates >= datetime.datetime(1979,1,1,0,0,0))

        # Enable click events on the map:
        def onpick(event):
            ''' Event handler for a point click '''
            ind = event.ind
            t_center = dates[ind[0]]
            logger.info(f't = {t_center}')
            ax_lines[-1].set_xlim(t_center - datetime.timedelta(minutes=15), t_center + datetime.timedelta(minutes=15))
            onzoom(ax1)
            fig.canvas.draw()


        def onzoom(axis, *args, **kwargs):
            # Update the map to only show points within range:
            [tt1, tt2] = axis.get_xlim()
            d1 = mdates.num2date(tt1)
            d2 = mdates.num2date(tt2)
            hits = np.where((dts_gps >= d1) & (dts_gps <= d2))[0]
            
            logger.debug(f'zoomed to {d1}, {d2} ({len(hits)} hits)')
            try:
                m_ax.s.remove()
            except:
                logger.debug('failed to remove scatter points')

            m_ax.s = m.scatter(np.array(sx)[hits],np.array(sy)[hits],c=T_gps[hits], marker='.', s=10, cmap = get_cmap('plasma'), zorder=100, picker=5)

        # Attach callback
        ax1.callbacks.connect('xlim_changed', onzoom)
        # ax2.callbacks.connect('xlim_changed', onzoom)

        cid= fig.canvas.mpl_connect('pick_event', lambda event: onpick(event))
    # -----------------------------------
    # Line plots
    # -----------------------------------
    if len(line_plots) > 0:
        gs_lineplots = GS.GridSpecFromSubplotSpec(len(line_plots), 1, hspace=0.5, subplot_spec=gs_root[1,0])

        ax_lines = []

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
                v_horiz = np.array([x['GPS'][0]['horiz_speed'] for x in S_with_GPS])
                v_vert = np.array([x['GPS'][0]['vert_speed'] for x in S_with_GPS])
                vel = np.sqrt(v_horiz*v_horiz + v_vert*v_vert)/1000.

                ax_lines[ind].plot(dts_gps, vel, markerface, markersize=markersize, alpha=markeralpha, label='Velocity')
                ax_lines[ind].set_ylabel('Velocity\n[km/sec]', rotation=0, labelpad=30)
                ax_lines[ind].set_ylim([5,10])
            elif a in 'Lshell':
                try:
                    # This way using a precomputed lookup table:
                    with open(lshell_file,'rb') as file:
                        Ldict = pickle.load(file)
                    L_interp = interp2d(Ldict['glon'], Ldict['glat'], Ldict['L'], kind='cubic')
                    Lshell = np.array([L_interp(x,y) for x,y in zip(lons, lats)])
                    
                    ax_lines[ind].plot(dts_gps, Lshell,markerface, markersize=markersize,  alpha=markeralpha, label='L shell')
                    ax_lines[ind].set_ylabel('L shell', rotation=0, labelpad=30)
                    ax_lines[ind].set_ylim([1,8])
                except:
                    logger.warning(f'Missing {lshell_file}')
            elif a in 'daylight':
                # Day or night based on ground track, using the daynight terminator from Basemap
                dayvec = np.array([is_day(x, y, z) for x,y,z in zip(dts_gps, lats, lons)])
                ax_lines[ind].plot(dts_gps, dayvec, markerface, markersize=markersize,  alpha=markeralpha, label='Day / Night')
                ax_lines[ind].set_yticks([False, True])
                ax_lines[ind].set_yticklabels(['Night','Day'])


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

        ax_lines[-1].set_xlim([t1,t2])


    fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.12)
    # fig.suptitle(f"VPM Survey Data\n {dts[0].strftime('%D%, %H:%m:%S')} -- {dts[-1].strftime('%D%, %H:%m:%S')}")
    fig.suptitle(f"VPM Survey Data\n {t1.strftime('%D%, %H:%M:%S')} -- {t2.strftime('%D%, %H:%M:%S')}")

    return fig
