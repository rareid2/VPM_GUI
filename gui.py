import time
import logging
import os
import sys
import pickle
import gzip
import queue
import tkinter as tk # Python 3.x
import tkinter.scrolledtext as ScrolledText
from tkinter import filedialog
from tkinter import ttk
from data_handlers import *  # Data processing modules
from file_handlers import *  # Loading and writing modules
from gui_plots import *      # Plotting modules
from db_handlers import get_packets_within_range
import datetime
import dateutil
import subprocess

from scipy.io import savemat, loadmat
# try:
#     from __ver__ import __ver__
# except:
#     __ver__ = "N/A"


class GUI(tk.Frame):

    # This class defines the graphical user interface             
    def __init__(self, parent, *args, **kwargs):


        try:
            process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], shell=False, stdout=subprocess.PIPE)
            git_head_hash = process.communicate()[0].strip()[0:8]
            git_str = "commit # " + git_head_hash.decode('utf-8')
        except:
            git_str = ''


        # ----------------------- GUI setup ---------------------------
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent

        if getattr( sys, 'frozen', False ) :
            # Fr
            self.runpath = sys.args[0]
        else :
            # running live
            self.runpath = os.getcwd()


        ncols = 5
        nrows = 50
        decoding_row = 5
        process_row = 15
        save_row = 25
        plot_row = 35



        self.grid(column=ncols, row=nrows, sticky='ew')

        logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
        logging.getLogger('matplotlib').setLevel(logging.WARNING)

        # data fields
        self.packets = [] # Decoded packets from telemetry
        self.burst_products = []    # Decoded data products from packets
        self.survey_products = []
        self.status_messages = []

        self.do_tlm = tk.BooleanVar()
        self.do_csv = tk.BooleanVar()
        self.do_previous = tk.BooleanVar()
        self.move_completed = tk.BooleanVar()

        self.do_tlm.set(True)
        self.do_csv.set(True)
        self.do_previous.set(False)
        self.move_completed.set(False)
        self.in_progress_file = tk.StringVar()
        self.in_progress_file.set('in_progress.pkl')

        self.burst_mode = tk.StringVar()
        self.burst_choices = ['Group by Status Packets','Group by Trailing Status Packet','Group by Experiment Number','Group by Timestamps']
        self.do_burst = tk.BooleanVar()
        self.do_survey = tk.BooleanVar()
        self.plot_map = tk.BooleanVar()

        self.burst_mode.set(self.burst_choices[0])
        self.do_burst.set(True)
        self.do_survey.set(True)
        self.plot_map.set(True)
                   
        self.line_plot_fields = ['lat', 'lon', 'altitude','velocity','Lshell', 'tracked_sats',
                                'used_sats','time_status', 'receiver_status', 'weeknum', 'sec_offset', 'solution_status',
                                'solution_type','horiz_speed', 'vert_speed', 'ground_track', 'daylight', 'timestamp', 'header_timestamp']
        self.line_plot_enables = [tk.BooleanVar() for x in self.line_plot_fields]
        # Some default enables for the survey plots
        self.line_plot_enables[self.line_plot_fields.index('lat')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('lon')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('altitude')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('used_sats')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('Lshell')].set(True)

        self.file_format = tk.StringVar()
        self.available_formats =['XML','Pickle','Matlab']
        self.file_suffixes =    ['xml','pkl','mat']
        self.file_format.set(self.available_formats[0])
        self.file_suffix = tk.StringVar()
        self.file_suffix.set(self.file_suffixes[0])

        self.cal_file = os.path.join(self.runpath,'resources','calibration_data.pkl')

        # Build GUI
        self.root.title('VPM Ground Support Software')
        self.root.option_add('*tearOff', 'FALSE')

        self.header_text = tk.StringVar()
        self.header_text.set(f"VPM Ground Support Software\n{git_str}")
        self.label = tk.Label(self.root, font=('Helvetica', 14, 'bold'), textvariable=self.header_text)
        self.label.grid(row=0, column=0, rowspan=4, columnspan=ncols, sticky='ew')

        self.logo = tk.PhotoImage(file=os.path.join(self.runpath,'resources','logo.png')).subsample(12,12)
        self.logo_button = tk.Button(self.root, image=self.logo, command=self.display_help)
        self.logo_button.grid(row=0, column=0, rowspan=4, sticky='w')

        self.burst_packet_text = tk.StringVar()
        self.burst_packet_label = tk.Label(self.root, textvariable=self.burst_packet_text, font=('Helvetica', 14, 'bold'))
        self.burst_packet_label.grid(row=1, column=4, sticky='e')

        self.survey_packet_text = tk.StringVar()
        self.survey_packet_label = tk.Label(self.root, textvariable=self.survey_packet_text, font=('Helvetica', 14, 'bold'))
        self.survey_packet_label.grid(row=2, column=4, sticky='e')

        self.stat_packet_text = tk.StringVar()
        self.stat_packet_label = tk.Label(self.root, textvariable=self.stat_packet_text, font=('Helvetica', 14, 'bold'))
        self.stat_packet_label.grid(row=3, column=4, sticky='e')

        self.sep = ttk.Separator(self.root, orient="horizontal")
        self.sep.grid(row=decoding_row, column=0, columnspan=ncols, sticky='ew')
        
        self.sec1_text = tk.StringVar()
        self.sec1_text.set("Load packets from raw telemetry:")
        self.sec1_label = tk.Label(self.root, textvariable=self.sec1_text,  font=('Helvetica', 14, 'bold'))
        self.sec1_label.grid(row=decoding_row + 1, column=0, columnspan=ncols-1, sticky='w')

        self.packet_len_text = tk.StringVar()
        self.packet_len_label = tk.Label(self.root, textvariable=self.packet_len_text, font=('Helvetica', 14, 'bold'))
        self.packet_len_label.grid(row=0, column=4, sticky='e')

        # -------------- Decode packets -------------

        # text fields
        self.in_dir = tk.StringVar()
        self.in_dir.set(os.getcwd())

        self.out_dir = tk.StringVar()
        self.out_dir.set(os.path.join(os.getcwd(), 'output'))

        self.packet_db = tk.StringVar()
        self.packet_db.set('no db selected')

        # buttons
        self.reset_button = tk.Button(self.root, text="Clear All Data", command=self.clear_data)
        self.reset_button.grid(row=decoding_row-1, column=4, sticky='ew')
        
        self.decode_button = tk.Button(self.root, text="Read Telemetry Files", command=self.process_packets)
        self.decode_button.grid(row=decoding_row +2, column=0, sticky='ew')
        self.load_prev_button = tk.Button(self.root, text="Load from Pickle File", command=self.load_previous_packets)
        self.load_prev_button.grid(row=decoding_row+1, column=4, sticky='ew')  

        self.packet_inspector_button = tk.Button(self.root, text="Packet Inspector", command = self.call_packet_inspector)
        self.packet_inspector_button.grid(row=decoding_row-1, column=3, sticky='ew')  
        self.pickle_button = tk.Button(self.root, text="Save Packets", command=self.save_packets)
        self.pickle_button.grid(row=decoding_row+2, column=4, sticky='ew')

        # checkboxes
        self.tlm_chk = tk.Checkbutton(self.root, text='load TLM files', variable=self.do_tlm)
        self.tlm_chk.grid(row=decoding_row+2, column=1, sticky='w')
        self.tlm_chk.var = self.do_tlm
        self.csv_chk = tk.Checkbutton(self.root, text='load CSV files', variable=self.do_csv)
        self.csv_chk.grid(row=decoding_row+2, column=2, sticky='w')
        self.csv_chk.var = self.do_csv

        # horizontal line
        self.sep1 = ttk.Separator(self.root, orient="horizontal")
        self.sep1.grid(row=decoding_row+3, column=0, columnspan=6, sticky='ew')

        self.select_db_button = tk.Button(self.root, text="Select Packet Database", command=self.select_packet_db)
        self.select_db_button.grid(row=decoding_row+4, column=4, sticky='ew')
        tk.Label(self.root, text="Packet Database:",).grid(row=decoding_row + 4, column=1, sticky='e')
        self.packet_db_text = tk.Label(self.root, textvariable = self.packet_db, borderwidth=2)
        self.packet_db_text.grid(row=decoding_row+4, column=2, columnspan = 2, sticky='ew')


        self.sec1b_text = tk.StringVar()
        self.sec1b_text.set("Load packets from database:")
        self.sec1b_label = tk.Label(self.root, textvariable=self.sec1b_text,  font=('Helvetica', 14, 'bold'))
        self.sec1b_label.grid(row=decoding_row + 4, column=0, columnspan=ncols-1, sticky='w')


        tk.Label(self.root, text="Start Time:").grid(row=decoding_row + 5, column=0, sticky='e')
        tk.Label(self.root, text="Stop Time:").grid(row=decoding_row + 5, column=2, sticky='e')

        self.p1_entry = tk.Entry(self.root)
        self.p1_entry.grid(row = decoding_row + 5, column=1, sticky='ew')
        self.p1_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')
        # self.p1_entry.insert(0,'2020-05-01')

        self.p2_entry = tk.Entry(self.root)
        self.p2_entry.grid(row = decoding_row + 5, column=3, sticky='ew')
        self.p2_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')
        # self.p2_entry.insert(0,'2020-05-02')

        self.load_from_db_button = tk.Button(self.root, text="Load from database", command=self.load_from_db)
        self.load_from_db_button.grid(row=decoding_row + 5, column=4, sticky='ew')


        
        # horizontal line
        self.sep2 = ttk.Separator(self.root, orient="horizontal")
        self.sep2.grid(row=decoding_row+7, column=0, columnspan=6, sticky='ew')

        # ----------- Process burst and survey data from decoded packets ----------
        tk.Label(self.root, text="Reassemble Data Products from Packets:",  font=('Helvetica', 14, 'bold')).grid(row=process_row, column=0, columnspan=2, sticky='w')
        tk.Label(self.root, text="Burst decoding method:").grid(row=process_row +1, column=0, sticky='w')

        self.bm_menu = tk.OptionMenu(self.root, self.burst_mode, *self.burst_choices)
        self.bm_menu.grid(row=process_row+1, column=1, sticky='w')

        self.burst_chk = tk.Checkbutton(self.root, text='Process Burst Data', variable=self.do_burst)
        self.burst_chk.grid(row=process_row+1, column=2, sticky='w')
        self.burst_chk.var = self.do_burst

        self.survey_chk = tk.Checkbutton(self.root, text='Process Survey Data', variable=self.do_survey)
        self.survey_chk.grid(row=process_row+1, column=3, sticky='w')
        self.survey_chk.var = self.do_survey

        self.process_packets_button = tk.Button(self.root, text="Reassemble Data Products", command=self.process_burst_and_survey)
        self.process_packets_button.grid(row=process_row+1, column=4)  

        tk.Label(self.root, text="Header Start Time:").grid(row=process_row +2, column=0, sticky='e')
        tk.Label(self.root, text="Header Stop Time:").grid(row=process_row +3, column=0, sticky='e')

        self.t1_entry = tk.Entry(self.root)
        self.t1_entry.grid(row = process_row +2, column=1, sticky='ew')
        self.t1_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')

        self.t2_entry = tk.Entry(self.root)
        self.t2_entry.grid(row = process_row +3, column=1, sticky='ew')
        self.t2_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')

        tk.Label(self.root, text="Burst Command:").grid(row=process_row +2, column=2, sticky='e')
        tk.Label(self.root, text="Repeats:").grid(row=process_row +3, column=2, sticky='e')

        self.cmd_entry = tk.Entry(self.root)
        self.cmd_entry.grid(row = process_row +2, column=3, sticky='ew')
        self.cmd_entry.insert(0,'burst command')

        self.repeats_entry = tk.Entry(self.root)
        self.repeats_entry.grid(row = process_row +3, column=3, sticky='ew')
        self.repeats_entry.insert(0,'1')


        # ----------- Status messages -------
        tk.Label(self.root, text="Status Messages:",  font=('Helvetica', 12)).grid(row=save_row+1, column=0, columnspan=2, sticky='ew')

        self.statbox = tk.Listbox(self.root, height=6, width=30)
        self.statbox.grid(row = save_row + 2, column = 0, columnspan = 2, rowspan=6, sticky='n')
        self.statbox.bind('<<ListboxSelect>>', self.select_stat)

        # ----------- Save data ----------
        ttk.Separator(self.root, orient="horizontal").grid(row=save_row, column=0, columnspan=ncols, sticky='ew')
        tk.Label(self.root, text="Save Data Products:",  font=('Helvetica', 14, 'bold')).grid(row=save_row+1, column=2, columnspan=1, sticky='w')

        self.save_all_button = tk.Button(self.root, text="Save All", command=self.save_all)
        self.save_all_button.grid(row=save_row+1, column=4, sticky='ew')  
        self.save_survey_button = tk.Button(self.root, text="Save Survey", command=self.save_survey)
        self.save_survey_button.grid(row=save_row+2, column=4, sticky='ew')  
        self.save_burst_button = tk.Button(self.root, text="Save Burst", command=self.save_burst)
        self.save_burst_button.grid(row=save_row+3, column=4, sticky='ew')  
        self.save_stats_button = tk.Button(self.root, text="Save Status", command=self.save_stats)
        self.save_stats_button.grid(row=save_row+4, column=4, sticky='ew')  

        self.survey_entry = tk.Entry(self.root)
        self.survey_entry.grid(row = save_row +2, column=2, columnspan=2, sticky='e')
        self.survey_entry.insert(0,'survey_data.' + self.file_suffix.get())
        self.burst_entry = tk.Entry(self.root)
        self.burst_entry.grid(row = save_row +3, column=2, columnspan=2, sticky='e')
        self.burst_entry.insert(0,'burst_data.' + self.file_suffix.get())
        self.status_entry = tk.Entry(self.root)
        self.status_entry.grid(row = save_row +4, column=2, columnspan=2, sticky='e')
        self.status_entry.insert(0,'status_data.' + self.file_suffix.get())
        
        tk.Label(self.root, text="Output file names:", font=('Helvetica', 12, 'bold')).grid(row=save_row + 1, column=3, sticky='w')
        tk.Label(self.root, text="Output file format:").grid(row=save_row +2, column=2, sticky='w')
        self.ff_menu = tk.OptionMenu(self.root, self.file_format, *(self.available_formats), command=self.update_outfiles)
        self.ff_menu.grid(row=save_row+3, column=2, sticky='w')

        tk.Label(self.root, text="Header start time:", font=('Helvetica', 12, 'bold')).grid(row=save_row + 5, column=3, sticky='e')
        self.save_t1_entry = tk.Entry(self.root)
        self.save_t1_entry.grid(row = save_row +5, column=4, sticky='ew')
        self.save_t1_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')

        tk.Label(self.root, text="Header stop time:", font=('Helvetica', 12, 'bold')).grid(row=save_row + 6, column=3, sticky='e')
        self.save_t2_entry = tk.Entry(self.root)
        self.save_t2_entry.grid(row = save_row +6, column=4, sticky='ew')
        self.save_t2_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')

        ttk.Separator(self.root, orient="vertical").grid(row=save_row+1, column=2, rowspan=6, sticky='nsw')

        # ----------- Plot survey data ----------
        ttk.Separator(self.root, orient="horizontal").grid(row=plot_row, column=0, columnspan=ncols, sticky='ew')
        tk.Label(self.root, text="Plot Survey Data:",  font=('Helvetica', 14, 'bold')).grid(row=plot_row+1, column=0, columnspan=1, sticky='w')

        self.load_survey_button = tk.Button(self.root, text="Load survey data", command=self.load_survey_file)
        self.load_survey_button.grid(row=plot_row+8, column=4, sticky='ew')

        tk.Label(self.root, text="E channel gain:", font=('Helvetica', 12)).grid(row=plot_row + 2, column=0,rowspan=2, sticky='e')
        tk.Label(self.root, text="B channel gain:", font=('Helvetica', 12)).grid(row=plot_row + 4, column=0,rowspan=2, sticky='e')
        tk.Label(self.root, text="Time axis:", font=('Helvetica', 12)).grid(row=plot_row + 6, column=0,rowspan=2, sticky='e')

        self.survey_clim_sliders = tk.BooleanVar()
        self.survey_clim_sliders.set(True)
        self.survey_clim_check = tk.Checkbutton(self.root, text='Show colorbar sliders', variable=self.survey_clim_sliders)
        self.survey_clim_check.grid(row=plot_row+1, column=1, sticky='w')

        self.survey_E_gain = tk.BooleanVar()
        self.survey_E_low_gain_button = tk.Radiobutton(self.root, text="Low", variable=self.survey_E_gain, value=False)
        self.survey_E_low_gain_button.grid(row = plot_row+2, column=1, sticky='w')
        self.survey_E_hi_gain_button = tk.Radiobutton(self.root, text="High", variable=self.survey_E_gain, value=True)
        self.survey_E_hi_gain_button.grid(row = plot_row+3, column=1, sticky='w')

        self.survey_B_gain = tk.BooleanVar()
        self.survey_B_low_gain_button = tk.Radiobutton(self.root, text="Low", variable=self.survey_B_gain, value=False)
        self.survey_B_low_gain_button.grid(row = plot_row+4, column=1, sticky='w')
        self.survey_B_hi_gain_button = tk.Radiobutton(self.root, text="High", variable=self.survey_B_gain, value=True)
        self.survey_B_hi_gain_button.grid(row = plot_row+5, column=1, sticky='w')

        self.survey_time_axis = tk.BooleanVar()
        self.survey_time_axis.trace("w",self.update_survey_time_fields)
        self.survey_time_button_1 = tk.Radiobutton(self.root, text="Payload", variable=self.survey_time_axis, value=False)
        self.survey_time_button_1.grid(row = plot_row+6, column=1, sticky='w')
        self.survey_time_button_2 = tk.Radiobutton(self.root, text="Bus", variable=self.survey_time_axis, value=True)
        self.survey_time_button_2.grid(row = plot_row+7, column=1, sticky='w')


        self.metadata_chk = tk.Checkbutton(self.root, text='Show map', variable=self.plot_map)
        self.metadata_chk.grid(row=plot_row+1, column=2, sticky='w')
        self.metadata_chk.var = self.plot_map 

        self.plot_survey_button = tk.Button(self.root, text="Plot Survey Data", command=self.call_plot_survey)
        self.plot_survey_button.grid(row=plot_row+1, column=4, sticky='ew')

        self.update_outfiles(None);

        self.lineplot_chks = [tk.Checkbutton(self.root, text = self.line_plot_fields[x], variable = self.line_plot_enables[x]) for x in range(len(self.line_plot_fields))]

        for ind, k in enumerate(self.lineplot_chks[0:6]):
            k.grid(row=plot_row + 2 + ind, column = 2, sticky='w')
            k.var = self.line_plot_enables[ind]
        for ind, k in enumerate(self.lineplot_chks[6:13]):
            k.grid(row=plot_row + 1 + ind, column = 3, sticky='w')
            k.var = self.line_plot_enables[ind]
        for ind, k in enumerate(self.lineplot_chks[13:]):
            k.grid(row=plot_row + 2 + ind, column = 4, sticky='w')
            k.var = self.line_plot_enables[ind]


        tk.Label(self.root, text="Survey Start Time:", font=('Helvetica', 12, 'bold')).grid(row=plot_row + 8, column=0, sticky='e')
        tk.Label(self.root, text="Survey Stop Time:",  font=('Helvetica', 12, 'bold')).grid(row=plot_row + 8, column=2, sticky='e')

        self.s1_entry = tk.Entry(self.root)
        self.s1_entry.grid(row = plot_row + 8, column=1, sticky='ew')
        self.s1_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')

        self.s2_entry = tk.Entry(self.root)
        self.s2_entry.grid(row = plot_row +8, column=3, sticky='ew')
        self.s2_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')


        # ----------- Plot burst data ----------
        ttk.Separator(self.root, orient="horizontal").grid(row=plot_row + 9, column=0, columnspan=ncols, sticky='ew')
        tk.Label(self.root, text="Plot Burst Data:",  font=('Helvetica', 14, 'bold')).grid(row=plot_row+11, column=0, columnspan=1, sticky='w')
             
        self.load_burst_xml_button = tk.Button(self.root, text="Load burst data", command=self.load_burst_file)
        self.load_burst_xml_button.grid(row=plot_row+11, column=4, sticky='ewn')

        self.plot_burst_button = tk.Button(self.root, text="Plot burst data", command=self.call_plot_burst)
        self.plot_burst_button.grid(row=plot_row+12, column=4, sticky='ewn')

        self.plot_burst_map_button = tk.Button(self.root, text = "Plot burst map", command=self.call_burst_map)
        self.plot_burst_map_button.grid(row=plot_row+13, column=4, sticky='ewn')

        self.burst_checkboxes = ['plot terminator','plot trajectory','show transmitters','print GPS entries']

        self.burst_check_vars = dict()
        for x in self.burst_checkboxes:
            self.burst_check_vars[x] = tk.BooleanVar()
            self.burst_check_vars[x].set(True)

        self.burst_chks = [tk.Checkbutton(self.root, text = self.burst_checkboxes[x],
                          variable = self.burst_check_vars[self.burst_checkboxes[x]])
                          for x in range(len(self.burst_checkboxes))]

        for ind, k in enumerate(self.burst_chks[0:2]):
            k.grid(row=plot_row + 12, column=ind, sticky='w')
        for ind, k in enumerate(self.burst_chks[2:]):
            k.grid(row=plot_row + 13, column=ind, sticky='w')

        self.clim_sliders = tk.BooleanVar()
        self.clim_sliders.set(True)
        self.color_slider_check = tk.Checkbutton(self.root, text= "show colorbar sliders", variable = self.clim_sliders)
        self.color_slider_check.grid(row=plot_row+14, column=0, sticky='w')
         
        tk.Label(self.root, text="Available bursts:",  font=('Helvetica', 12)).grid(row=plot_row+11, column=2, sticky='ew')


        self.listbox = tk.Listbox(self.root, height=6, width=30, selectmode = tk.EXTENDED)
        self.listbox.grid(row = plot_row + 12, column = 2, columnspan=2, rowspan=6)

        # Run some updaters. eh, this should be done in a callback, but... shrug
        self.update_burst_list()
        self.update_counters()


    # ----------------------- Actions ---------------------------

    def load_from_db(self):

        try:
            p1 = dateutil.parser.parse(self.p1_entry.get()).replace(tzinfo=datetime.timezone.utc)
            p2 = dateutil.parser.parse(self.p2_entry.get()).replace(tzinfo=datetime.timezone.utc)
        except:
            logging.warning("couldn't parse packet start and end times")
            p1 = None
            p2 = None
            return False

        logging.info(f"Loading packets with header timestamps between {p1} and {p2}")

        database = self.packet_db.get()
        if not os.path.exists(database):
            logging.warning(f'could not find database: {database}')
            return False

        self.packets.extend(get_packets_within_range(database, t1=p1, t2=p2))
        self.update_counters()


        return True

    def load_calibration(self):
        logging.info('Selecting calibration file')
        self.cal_file = filedialog.askopenfilename(initialdir=os.getcwd())

        logging.info(f'calibration file is {self.cal_file}')
        return

    def clear_data(self):
        logging.info('Clearing all loaded data')
        self.packets = []
        self.burst_products = []
        self.survey_products = []
        self.status_messages = []
        self.update_counters()
        self.update_burst_list()
        self.update_survey_time_fields()
        self.update_stat_list()
        return True

    def save_packets(self):
        ''' Save decoded (but unassembled) packets to a Pickle file '''
        logging.info('Please select an output directory')
        self.out_dir.set(filedialog.askdirectory(initialdir=self.in_dir.get()))
        fname = os.path.join(self.out_dir.get(), 'packets.pkl')
        logging.info(f'Saving decoded packets to {fname}')
        with open(fname,'wb') as file:
            pickle.dump(self.packets, file)
        return

    def save_survey(self, update_dir=True):

        if self.survey_products:
            if update_dir:
                self.out_dir.set(filedialog.askdirectory(initialdir=self.out_dir.get()))

            outpath = os.path.join(self.out_dir.get(), self.survey_entry.get())
            try:
                t1 = dateutil.parser.parse(self.save_t1_entry.get()).replace(tzinfo=datetime.timezone.utc)
                t2 = dateutil.parser.parse(self.save_t2_entry.get()).replace(tzinfo=datetime.timezone.utc)
                outdata = list(filter(lambda p: (p['header_timestamp'] >= t1.timestamp()) and (p['header_timestamp'] <= t2.timestamp()), self.survey_products))
                logging.info(f'saving survey products between {t1} and {t2}')
            except:
                t1 = None
                t2 = None
                outdata = self.survey_products

            if self.file_format.get() in 'XML':
                logging.info(f'saving {len(outdata)} survey products to {outpath}')
                write_survey_XML(outdata,outpath)
            
            elif self.file_format.get() in 'Matlab':
                logging.info(f'saving {len(outdata)} survey products to {outpath}')
                savemat(outpath, {'survey_data' : outdata})
            
            elif self.file_format.get() in 'Pickle':
                logging.info(f'saving {len(outdata)} survey products to {outpath}')
                with open(outpath,'wb') as file:
                    pickle.dump(outdata, file)
            else:
                logging.info(f'{self.file_format.get()} not yet implemented - go bug Austin about it')
        else:
            logging.info('No survey data to save')
        return


    def save_burst(self, update_dir=True):

        if self.burst_products:
            if update_dir:
                self.out_dir.set(filedialog.askdirectory(initialdir=self.out_dir.get()))

            outpath = os.path.join(self.out_dir.get(), self.burst_entry.get())

            try:
                t1 = dateutil.parser.parse(self.save_t1_entry.get()).replace(tzinfo=datetime.timezone.utc)
                t2 = dateutil.parser.parse(self.save_t2_entry.get()).replace(tzinfo=datetime.timezone.utc)
                outdata = list(filter(lambda p: (p['header_timestamp'] >= t1.timestamp()) and (p['header_timestamp'] <= t2.timestamp()), self.burst_products))
                logging.info(f'saving burst products between {t1} and {t2}')
            except:
                t1 = None
                t2 = None
                outdata = self.burst_products


            if self.file_format.get() in 'XML':
                logging.info(f'saving {len(outdata)} burst products to {outpath}')
                write_burst_XML(outdata, outpath)

            elif self.file_format.get() in 'Matlab':
                logging.info(f'saving {len(outdata)} burst products to {outpath}')
                savemat(outpath, {'burst_data' : outdata})

            elif self.file_format.get() in 'Pickle':
                logging.info(f'saving {len(outdata)} burst products to {outpath}')
                with open(outpath, 'wb') as file:
                    pickle.dump(outdata, file)
            else:
                logging.info(f'{self.file_format.get()} not yet implemented - go bug Austin about it')
        else:
            logging.info('NO burst data to save')    
        return

    def save_stats(self, update_dir=True):
        if self.status_messages:
            if update_dir:
                self.out_dir.set(filedialog.askdirectory(initialdir=self.out_dir.get()))

            outpath = os.path.join(self.out_dir.get(), self.status_entry.get())
         
            try:
                t1 = dateutil.parser.parse(self.save_t1_entry.get()).replace(tzinfo=datetime.timezone.utc)
                t2 = dateutil.parser.parse(self.save_t2_entry.get()).replace(tzinfo=datetime.timezone.utc)
                outdata = list(filter(lambda p: (p['header_timestamp'] >= t1.timestamp()) and (p['header_timestamp'] <= t2.timestamp()), self.status_messages))
                logging.info(f'saving status messages between {t1} and {t2}')
            except:
                t1 = None
                t2 = None
                outdata = self.status_messages


            if self.file_format.get() in 'XML':
                logging.info(f'saving {len(outdata)} status messages to {outpath}')
                write_status_XML(outdata, outpath)

            elif self.file_format.get() in 'Matlab':
                logging.info(f'saving {len(outdata)} status messages to {outpath}')
                savemat(outpath, {'status_messages' : outdata})

            elif self.file_format.get() in 'Pickle':
                logging.info(f'saving {len(outdata)} status messages to {outpath}')
                with open(outpath,'wb') as file:
                    pickle.dump(outdata, file)

            else:
                logging.info(f'{self.file_format.get()} not yet implemented - go bug Austin about it')
        else:
            logging.info('NO status messages to save')    
        return

    def save_all(self):
        logging.info(f'Saving all decoded data products')
        logging.info(f'Please select an output directory')
        self.out_dir.set(filedialog.askdirectory(initialdir=self.out_dir.get()))
        self.save_survey(update_dir=False)
        self.save_burst( update_dir=False)
        self.save_stats( update_dir=False)
        return True

    def update_burst_list(self):
        logger = logging.getLogger(__name__)
        self.listbox.delete(0, tk.END)
        for b in self.burst_products:
            datestr = datetime.datetime.fromtimestamp(b['header_timestamp'], tz=datetime.timezone.utc)

            namestr = datestr.strftime('%m/%d/%Y %H:%M') + ': '
            if b['config']['TD_FD_SELECT']:
                namestr+='Time Domain, '
            else:
                namestr+='Freq Domain, '
            namestr+= f"n={b['config']['burst_pulses']}"
            self.listbox.insert(tk.END, namestr)

        # self.root.after(100, self.update_burst_list)
        

    def update_time_fields(self):
        if self.packets:
            self.packets = sorted(self.packets, key = lambda p: p['header_timestamp'])
            self.t1_entry.delete(0, tk.END)
            self.t1_entry.insert(0, datetime.datetime.utcfromtimestamp(self.packets[0]['header_timestamp']).isoformat())
            self.t2_entry.delete(0, tk.END)
            self.t2_entry.insert(0, datetime.datetime.utcfromtimestamp(self.packets[-1]['header_timestamp']).isoformat())
        
    def update_survey_time_fields(self, *kwargs):
        if len(self.survey_products) > 0:
            bus_timestamps=self.survey_time_axis.get()
            if bus_timestamps:
                s1 = min([x['header_timestamp'] for x in self.survey_products])
                s2 = max([x['header_timestamp'] for x in self.survey_products])
            else:
                S_with_GPS = list(filter(lambda x: (('GPS' in x) and ('timestamp' in x['GPS'][0])), self.survey_products))
                s1 = min([x['GPS'][0]['timestamp'] for x in S_with_GPS])
                s2 = max([x['GPS'][0]['timestamp'] for x in S_with_GPS])

            self.s1_entry.delete(0, tk.END)
            self.s1_entry.insert(0, datetime.datetime.utcfromtimestamp(s1).isoformat())
            self.s2_entry.delete(0, tk.END)
            self.s2_entry.insert(0, datetime.datetime.utcfromtimestamp(s2).isoformat())
        else:
            self.s1_entry.delete(0, tk.END)
            self.s1_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')
            self.s2_entry.delete(0, tk.END)
            self.s2_entry.insert(0,'YYYY-MM-DDTHH:MM:SS')

    def update_stat_list(self):
        self.statbox.delete(0, tk.END)
        for stat in self.status_messages:
            datestr = datetime.datetime.fromtimestamp(stat['header_timestamp'], tz=datetime.timezone.utc)
            namestr = 'source: ' + stat['source'] + ', ' + datestr.strftime('%m/%d/%Y %H:%M:%S')
            self.statbox.insert(tk.END, namestr)


    def update_outfiles(self, event):
        self.file_suffix.set(self.file_suffixes[self.available_formats.index(self.file_format.get())])

        survey_name = self.survey_entry.get().split('.')[0] + '.' + self.file_suffix.get()
        self.survey_entry.delete(0, tk.END)
        self.survey_entry.insert(0, survey_name)
        burst_name = self.burst_entry.get().split('.')[0] + '.' + self.file_suffix.get()
        self.burst_entry.delete(0, tk.END)
        self.burst_entry.insert(0, burst_name)
        status_name = self.status_entry.get().split('.')[0] + '.' + self.file_suffix.get()
        self.status_entry.delete(0, tk.END)
        self.status_entry.insert(0, status_name)

    def update_counters(self):
        self.stat_packet_text.set(f"{len(self.status_messages)} Status loaded")
        self.survey_packet_text.set(f"{len(self.survey_products)} Surveys loaded")
        self.burst_packet_text.set(f"{len(self.burst_products)} Bursts loaded")
        self.packet_len_text.set(f"{len(self.packets)} Packets loaded")
        # Poll repeatedly (currently no, we're just calling the appropriate
        # updates whenever we need to)
        # self.root.after(100, self.update_counters) 

    def load_survey_file(self):
        logger = logging.getLogger(__name__)
        fname=filedialog.askopenfilename(initialdir=self.in_dir.get())

        if fname and fname.endswith(".xml"):
            self.survey_products.extend(read_survey_XML(fname))

        if fname and fname.endswith(".mat"):
            self.survey_products.extend(read_survey_matlab(fname))

        if fname and fname.endswith(".pkl"):
            with open(fname,'rb') as file:
                self.survey_products.extend(pickle.load(file))

        logger.info(f'Loaded {len(self.survey_products)} survey entries from {fname}')
        self.update_counters()
        self.update_survey_time_fields()            

    def load_burst_file(self):
        logger = logging.getLogger(__name__)
        fname=filedialog.askopenfilename(initialdir=self.in_dir.get())

        if fname:
            if fname.endswith(".xml"):
                self.burst_products.extend(read_burst_XML(fname))

            if fname.endswith(".mat"):

                self.burst_products.extend(read_burst_matlab(fname))

            if fname.endswith(".pkl"):
                with open(fname,'rb') as file:
                    self.burst_products.extend(pickle.load(file))

            logger.info(f'Loaded {len(self.burst_products)} burst entries from {fname}')
            self.update_counters()
            self.update_burst_list()
            self.update_stat_list()
        
    def load_previous_packets(self):
        logger = logging.getLogger(__name__)

        fname=filedialog.askopenfilename(initialdir=self.in_dir)

        if fname and fname.endswith(".pkl"):
            logger.info(f'Opening {fname}')
            with open(fname,'rb') as file:
                self.packets.extend(pickle.load(file))

        if fname and fname.endswith(".pklz"):
            logger.info(f'Opening {fname}')
            with gzip.open(fname,'rb') as file:
                self.packets.extend(pickle.load(file))

            self.packet_len_text.set(f"{len(self.packets)} packets loaded")
        
        return

    def select_packet_db(self):
        self.packet_db.set(filedialog.askopenfilename(initialdir=self.in_dir.get()))
        
    def call_packet_inspector(self):
        if not self.packets:
            logging.info(f'No packets to inspect')
            return

        packet_inspector(self.root, self.packets)

    def call_plot_survey(self):
        if not self.survey_products:
            logging.info(f'No survey data present')
            return
        
        # Get selected metadata plots:
        lines_to_do = [self.line_plot_fields[x] for x in range(len(self.line_plot_fields))
                 if self.line_plot_enables[x].get()]
        logging.info(lines_to_do)

        
        try:
            # Select subset of the survey data
            s1 = dateutil.parser.parse(self.s1_entry.get()).replace(tzinfo=datetime.timezone.utc)
            s2 = dateutil.parser.parse(self.s2_entry.get()).replace(tzinfo=datetime.timezone.utc)
            if self.survey_time_axis.get():
                # GPS timestamps
                cur_survey = list(filter(lambda x:  ('GPS' in x) and 
                                                    ('timestamp' in x['GPS'][0]) and
                                                    (x['GPS'][0]['timestamp'] > s1.timestamp() - 60) and
                                                    (x['GPS'][0]['timestamp'] < s2.timestamp() + 60), self.survey_products))
            else:
                # bus timestamps
                cur_survey = list(filter(lambda x:  (x['header_timestamp'] > s1.timestamp() - 60) and
                                                    (x['header_timestamp'] < s2.timestamp() + 60), self.survey_products))

        except:
            logging.warning("couldn't parse survey start and end times -- using defaults")
            s1 = None
            s2 = None
            cur_survey = self.survey_products

        if not cur_survey:
            logging.info('No survey data within selected time range')
            return

        plot_survey_data_and_metadata(self.root, cur_survey, self.survey_clim_sliders.get(),
            line_plots=lines_to_do, cal_file=None, 
            plot_map = self.plot_map.get(),
            E_gain=self.survey_E_gain.get(),
            B_gain=self.survey_B_gain.get(), 
            bus_timestamps=self.survey_time_axis.get(),
            t1 = s1, t2 = s2)
        
        
    def call_plot_burst(self):
        if not self.burst_products:
            logging.info(f'No burst data present')
            return
        burst_index = self.listbox.curselection()

        for ind in self.listbox.curselection():        
            logging.info(f'Plotting burst {ind}')
            cur_burst = self.burst_products[int(ind)]
            plot_burst_data(self.root, cur_burst, cal_file=self.cal_file, show_clim_sliders=self.clim_sliders.get())


    def call_burst_map(self):
        if not self.burst_products:
            logging.info(f'No burst data present')
            return
        burst_index = self.listbox.curselection()

        for ind in self.listbox.curselection():        
            logging.info(f'Plotting burst map {ind}')
            cur_burst = self.burst_products[int(ind)]

            if len(cur_burst['G']) > 0:
                plot_burst_map(self.root, cur_burst['G'],
                show_terminator   = self.burst_check_vars['plot terminator'].get(),
                plot_trajectory   = self.burst_check_vars['plot trajectory'].get(),
                show_transmitters = self.burst_check_vars['show transmitters'].get(),
                print_GPS_entries = self.burst_check_vars['print GPS entries'].get())

    def get_burst_command(self):
        ''' Parse and validate the command entered in the text box '''
        logger=logging.getLogger(__name__)
        inp_str = self.cmd_entry.get().strip(' []{}\t')

        logger.info(f'inp_str: {inp_str}')
        if inp_str.startswith('0x'):
            # Hex string
            logger.info('hex')
            cmd = [int(inp_str[2:4], 16),int(inp_str[4:6], 16),int(inp_str[6:8], 16)]
        elif len(inp_str) == 24:
            # Binary ascii string
            logger.info('binary')
            cmd = [int(inp_str[0:8],2), int(inp_str[8:16],2), int(inp_str[16:],2)]
        else:
            # 3 ints:
            logger.info('ints')
            if ',' in inp_str:
                cmd = np.fromstring(inp_str, dtype=int, sep=',')
            else:
                cmd = np.fromstring(inp_str, dtype=int, sep=' ')
        logger.info(f'cmd: {cmd}')
        return cmd

    def process_burst_and_survey(self):
        logger = logging.getLogger("root.process_burst_and_survey")

        logger.info("Processing burst and survey packets...") 
        # ----------------- Process any packets we have -------------
        if self.packets:
            # Sort by header timestamp
            self.packets = sorted(self.packets, key = lambda p: p['header_timestamp'])
            # Process status messages
            logger.info("Decoding status messages")
            stats = decode_status(self.packets)
            self.status_messages = stats

            # Process any bursts
            if self.do_burst.get():
                # Three different burst decoding methods to choose from:
                logger.info("Decoding burst data")
                if self.burst_mode.get() in 'Group by Status Packets':
                    # Decode by binning burst packets between two adjacent status packets,
                    # which are automatically requested at the beginning and end of a burst
                    logger.info(f'Processing bursts between status packets')
                    B_data, unused_burst = decode_burst_data_between_status_packets(self.packets)
                    self.burst_products.extend(B_data)
                elif self.burst_mode.get() in 'Group by Timestamps':
                    # Manually bin burst packets between two timestamps
                    t1 = dateutil.parser.parse(self.t1_entry.get()).replace(tzinfo=datetime.timezone.utc)
                    t2 = dateutil.parser.parse(self.t2_entry.get()).replace(tzinfo=datetime.timezone.utc)
                    burst_cmd = self.get_burst_command()
                    n_pulses = int(self.repeats_entry.get())
                    logger.info(f'Processing bursts between {t1} and {t2}')

                    B_data, unused_burst = decode_burst_data_in_range(self.packets,
                                           t1.timestamp(), t2.timestamp(),
                                           burst_cmd = burst_cmd, burst_pulses = n_pulses)
                    
                    self.burst_products.extend(B_data)
                    
                elif self.burst_mode.get() in 'Group by Experiment Number':
                #     # Bin bursts by experiment number
                    burst_cmd = self.get_burst_command()
                    try:
                        n_pulses = int(self.repeats_entry.get())
                    except:
                        n_pulses = None
                    logger.info(f'Processing bursts by experiment number')
                    B_data, unused_burst = decode_burst_data_by_experiment_number(self.packets, 
                                           burst_cmd = burst_cmd, burst_pulses = n_pulses)
                #     outs['burst'] = B_data
                    self.burst_products.extend(B_data)

                elif self.burst_mode.get() in 'Group by Trailing Status Packet':

                    logger.info(f'Processing bursts by trailing status packets')
                    B_data, unused_burst = decode_burst_data_by_trailing_status_packet(self.packets)
                    self.burst_products.extend(B_data)


            # Process any survey data
            if self.do_survey.get():
                logger.info("Decoding survey data")
                S_data, unused_survey = decode_survey_data(self.packets)
                self.survey_products = S_data

        else:
            logger.info('No packets loaded!')

        self.update_counters()
        self.update_burst_list()
        self.update_stat_list()
        self.update_time_fields()
        self.update_survey_time_fields()

        return True

    def process_packets(self):
        logger = logging.getLogger()

        
        logger.info("Processing telemetry packets...") 
        logger.info("Please select an input directory")
        self.in_dir.set(filedialog.askdirectory(initialdir=self.in_dir.get()))

        d = os.listdir(self.in_dir.get())

        tlm_files = [x for x in d if x.endswith('.tlm')]
        csv_files = [x for x in d if x.endswith('.csv')]

        logger.info(f"found {len(tlm_files)} .tlm files")
        logger.info(f"found {len(csv_files)} .csv files")

        packets = []

        if self.do_tlm.get() and (len(tlm_files) > 0):        
            # Load packets from each TLM file, tag with the source filename, and decode
            for fname in tlm_files:
                packets.extend(decode_packets_TLM(self.in_dir.get(), fname))

                # Move the original file to the "processed" directory
                if self.move_completed.get():
                    shutil.move(fpath, os.path.join(self.out_dir.get(),fname))

        if self.do_csv.get() and (len(csv_files) > 0):
            # Load packets from each CSV file, tag with the source filename, and decode
            for fname in csv_files:
                packets.extend(decode_packets_CSV(self.in_dir.get(), fname))

                # Move the original file to the "processed" directory
                if self.move_completed.get():
                    shutil.move(fpath, os.path.join(self.out_dir.get(),fname))

        self.packets = packets
    
        self.update_counters()        
        self.update_time_fields()
        self.update_survey_time_fields()

        return True

    def display_help(self):
        self.help_window = tk.Toplevel(self.root)
        self.help_window.pack_propagate(0)

        helpstr = ' ------ VPM Ground Support Software ------\n' + \
                  '            GUI widget help ' 
        self.help_msg = tk.Message(self.help_window, anchor='center', text=helpstr, width=80)
        self.help_msg.pack()

 
    def select_stat(self, *args):
        stat_ind = int(self.statbox.curselection()[0])
        stat_str = print_status([self.status_messages[stat_ind]])       
        logging.info(stat_str)


def main():

    logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    root = tk.Tk()
    gui = GUI(root)

    console_log = logging.getLogger()

    # # ----- Automatic actions (for debugging) -----
    # infile = "/Users/austin/Dropbox/VPM working directory/VPM Data/tmp/survey_data.xml"
    # gui.survey_products.extend(read_survey_XML(infile))
    # gui.update_counters()
    # gui.update_survey_time_fields()

    # infile = "/Users/austin/afrl/vpm/data/2020-05-20_2/outputs/burst_data.xml"
    # gui.burst_products.extend(read_burst_XML(infile))
    # gui.update_counters()
    # gui.update_survey_time_fields()
    # gui.update_burst_list()

    # gui.call_plot_burst()
    # gui.call_plot_survey()

    # Load a burst:
    # infile = "/Users/austin/Dropbox/VPM working directory/VPM Data/processed/burst/mat/2020/05/15/VPM_burst_TD_2020-05-15_1147.mat"
    # gui.burst_products.extend(read_burst_matlab(infile))
    # gui.update_counters()
    # gui.update_survey_time_fields()
    # gui.update_burst_list()
    # gui.call_plot_burst()
    
    gui.root.mainloop()
    # t1.join()


main()
