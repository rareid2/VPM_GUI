import tkinter as tk # Python 3.x
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import datetime
import logging
import pickle
import os

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

# Individual plot scripts
from plots.packet_inspector import packet_inspector as packet_inspector_core
from plots.plot_survey_data_and_metadata import plot_survey_data_and_metadata as plot_survey_core
from plots.plot_burst_data import plot_burst_TD, plot_burst_FD
from plots.plot_burst_map import plot_burst_map as plot_map_core


def packet_inspector(parent, packets):
    ''' wrap the packet inspector tool with a TK window '''

    figure_window = tk.Toplevel(parent)
    fig = Figure(figsize=(12,6))


    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # call the core plot:
    packet_inspector_core(fig, packets)


def plot_survey_data_and_metadata(parent, S_data, **kwargs):
    ''' wrap the survey plotter with a TK window '''
    
    figure_window = tk.Toplevel(parent)

    fig = Figure(figsize=(12,8))

    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Call the core plotting script; forward all the keyword arguments.
    plot_survey_core(fig, S_data, **kwargs)

    return

def plot_burst_data(parent, burst, cal_file=None):
    ''' wrap the burst plotter with a TK window '''

    logger = logging.getLogger(__name__)

    # Cal data?
    cal_data = None
    if cal_file:    
        try:
            with open(cal_file,'rb') as file:
                logger.info(f'loading calibration file {cal_file}')
                cal_data = pickle.load(file)
        except:
            logger.warning(f'Failed to load calibration file {cal_file}')
        
    # Configuration (TD or FD)
    cfg = burst['config']

    # Set up figure and Tk window
    figure_window = tk.Toplevel(parent)
    fig = Figure(figsize=(12,8))
    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Call it (time or frequency domain)
    if cfg['TD_FD_SELECT'] == 1:
        plot_burst_TD(fig, burst, cal_data = cal_data)

    elif cfg['TD_FD_SELECT'] == 0:
        plot_burst_FD(fig, burst, cal_data = cal_data)

    return


def plot_burst_map(parent, gps_data, **kwargs):
    ''' wrap the burst map plotter with a TK window '''

    # Set up figure and Tk window
    figure_window = tk.Toplevel(parent)
    fig = Figure(figsize=(12,7))
    canvas = FigureCanvasTkAgg(fig, master=figure_window)  # A tk.DrawingArea.
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    toolbar = NavigationToolbar2Tk(canvas, figure_window)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Call the core plotting script; forward all the keyword arguments.
    plot_map_core(fig, gps_data, **kwargs)

    return

