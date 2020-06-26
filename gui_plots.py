import tkinter as tk # Python 3.x
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import datetime
import logging
import pickle
import os

from matplotlib.widgets import Slider, Button, RadioButtons


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




def plot_survey_data_and_metadata(parent, S_data, clim_controls, **kwargs):
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
    _, pe, pb = plot_survey_core(fig, S_data, **kwargs)

    if clim_controls:
        ctrl = clim_control_window(parent, fig, pe, pb)

    return

def plot_burst_data(parent, burst, cal_file=None, show_clim_sliders=True):
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
        figure_window.title('Time-Domain Burst')
        _, pe, pb = plot_burst_TD(fig, burst, cal_data = cal_data)
        fig.canvas.draw()

        if show_clim_sliders:
            ctrl = clim_control_window(parent, fig, pe, pb, margin=40)




    elif cfg['TD_FD_SELECT'] == 0:
        figure_window.title('Frequency-Domain Burst')
        plot_burst_FD(fig, burst, cal_data = cal_data)
        # Not fully implemented -- no frequency domain bursts to work with

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
    plot_map_core(figure, gps_data, **kwargs)

    return



class clim_control_window():
    def __init__(self, parent, figure, pe, pb, margin=None):
        self.slider_window = tk.Toplevel(parent)
        self.slider_window.title('Adjust Color Limits')
        self.f2 = Figure(figsize=(6,2))
        self.c2 = FigureCanvasTkAgg(self.f2, master=self.slider_window)  # A tk.DrawingArea.
        self.c2.draw()
        self.c2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.pe = pe
        self.pb = pb
        self.fig = figure
        self.Ecmin_ax  = self.f2.add_axes([0.15, 0.5, 0.65, 0.1])
        self.Ecmax_ax  = self.f2.add_axes([0.15, 0.7, 0.65, 0.1])

        self.Bcmin_ax  = self.f2.add_axes([0.15, 0.1, 0.65, 0.1])
        self.Bcmax_ax  = self.f2.add_axes([0.15, 0.3, 0.65, 0.1])

        self.Ecmax_ax.set_title('Click to change color scale')

        if margin:
            (vmin, vmax) = self.pe.get_clim()
            self.esmin = Slider(self.Ecmin_ax, 'E Min (FD)', vmin - margin, vmax + margin, valinit=vmin)
            self.esmax = Slider(self.Ecmax_ax, 'E Max (FD)', vmin - margin, vmax + margin, valinit=vmax)
            (vmin, vmax) = self.pb.get_clim()
            self.bsmin = Slider(self.Bcmin_ax, 'B Min (FD)', vmin - margin, vmax + margin, valinit=vmin)
            self.bsmax = Slider(self.Bcmax_ax, 'B Max (FD)', vmin - margin, vmax + margin, valinit=vmax)

        else:
            # Default to 0-255
            (vmin, vmax) = self.pe.get_clim()
            self.esmin = Slider(self.Ecmin_ax, 'E Min (FD)', 0,255, valinit=vmin)
            self.esmax = Slider(self.Ecmax_ax, 'E Max (FD)', 0,255, valinit=vmax)
            (vmin, vmax) = self.pb.get_clim()
            self.bsmin = Slider(self.Bcmin_ax, 'B Min (FD)', 0,255, valinit=vmin)
            self.bsmax = Slider(self.Bcmax_ax, 'B Max (FD)', 0,255, valinit=vmax)
                
        
        self.esmin.on_changed(self.update_e)
        self.esmax.on_changed(self.update_e)
        self.bsmin.on_changed(self.update_b)
        self.bsmax.on_changed(self.update_b)

    def update_e(self,val):
        self.pe.set_clim([self.esmin.val,self.esmax.val])
        self.fig.canvas.draw()
    def update_b(self,val):
        self.pb.set_clim([self.bsmin.val,self.bsmax.val])
        self.fig.canvas.draw()

