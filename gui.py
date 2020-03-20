import time
import logging
import os
import pickle
import tkinter as tk # Python 3.x
import tkinter.scrolledtext as ScrolledText
from tkinter import filedialog
from tkinter import ttk
from data_handlers import *  # Data processing modules
from file_handlers import *  # Loading and writing modules
from gui_plots import *      # Plotting modules
import datetime
import dateutil

class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        self.setLevel(level=logging.INFO)
        # Store a reference to the Text it will log to
        self.text = text
        formatter = logging.Formatter('[%(name)s]\t%(levelname)s\t%(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(tk.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


class GUI(tk.Frame):

    # This class defines the graphical user interface 

    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent

        # s = ttk.Style()
        # print(f'{s.theme_names()}')
        # s.theme_use('alt')
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
        self.burst_choices = ['Group by Status Packets','Group by Experiment Number','Group by Timestamps']
        self.do_burst = tk.BooleanVar()
        self.do_survey = tk.BooleanVar()
        self.plot_map = tk.BooleanVar()

        # self.survey_outfile = tk.StringVar()
        # self.burst_outfile = tk.StringVar()
        # self.status_outfile = tk.StringVar()

        self.burst_mode.set(self.burst_choices[0])
        self.do_burst.set(True)
        self.do_survey.set(True)
        self.plot_map.set(True)
                   
        # self.line_plot_fields = ['Lshell','altitude','velocity','lat','lon','used_sats','solution_status','solution_type']
        self.line_plot_fields = ['lat', 'lon', 'altitude','velocity','Lshell', 'tracked_sats',
                                'used_sats','time_status', 'receiver_status', 'weeknum', 'sec_offset', 'solution_status',
                                 'solution_type','horiz_speed', 'vert_speed', 'ground_track', 'latency', 'timestamp', 'header_timestamp']
        self.line_plot_enables = [tk.BooleanVar() for x in self.line_plot_fields]
        # Some default enables for the survey plots
        self.line_plot_enables[self.line_plot_fields.index('lat')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('lon')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('altitude')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('used_sats')].set(True)
        self.line_plot_enables[self.line_plot_fields.index('Lshell')].set(True)

        self.file_format = tk.StringVar()
        self.available_formats =['XML','NetCDF','Pickle','Matlab']
        self.file_suffixes =    ['xml','nc','pkl','mat']
        self.file_format.set(self.available_formats[0])
        self.file_suffix = tk.StringVar()
        self.file_suffix.set(self.file_suffixes[0])

        # self.survey_outfile.set('survey_data' + '.' + self.file_suffix.get())
        # self.burst_outfile.set('burst_data' + '.' + self.file_suffix.get())

        self.cal_file = 'calibration_data.pkl'

        # Build GUI
        self.root.title('VPM Ground Support Software')
        self.root.option_add('*tearOff', 'FALSE')

        ncols = 5
        nrows = 40
        decoding_row = 5
        process_row = 12
        save_row = 20

        plot_row = 25


        self.grid(column=ncols, row=nrows, sticky='ew')


        # logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
        # logging.getLogger('matplotlib').setLevel(logging.WARNING)
        # Console window:
        # Add text widget to display logging info
        self.st = ScrolledText.ScrolledText(self.root, state='disabled')
        self.st.configure(borderwidth=4, relief='flat', font='TkFixedFont')
        self.st.grid(row=nrows, column=0, columnspan=nrows, sticky='ew')

        # Create textLogger
        text_handler = TextHandler(self.st)
        
        # Add the handler to logger
        logger = logging.getLogger()        
        logger.addHandler(text_handler)

        logger.info("Hi!")


        self.header_text = tk.StringVar()
        self.header_text.set("VPM Ground Support Software\nFancy GUI")
        self.label = tk.Label(self.root, font=('Helvetica', 14, 'bold'), textvariable=self.header_text)
        self.label.grid(row=0, column=0, rowspan=4, columnspan=ncols, sticky='ew')

        self.logo = tk.PhotoImage(file='logo.png').subsample(12,12)
        self.logo_button = tk.Button(self.root, image=self.logo)
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
        self.sec1_text.set("Decode raw telemetry:")
        self.sec1_label = tk.Label(self.root, textvariable=self.sec1_text,  font=('Helvetica', 14, 'bold'))
        self.sec1_label.grid(row=decoding_row + 1, column=0, columnspan=ncols-1, sticky='w')

        self.packet_len_text = tk.StringVar()
        self.packet_len_label = tk.Label(self.root, textvariable=self.packet_len_text, font=('Helvetica', 14, 'bold'))
        self.packet_len_label.grid(row=0, column=4, sticky='e')

        # -------------- Decode packets -------------

        # text fields
        # self.in_dir = os.getcwd()
        self.in_dir = tk.StringVar()
        self.in_dir.set('/Users/austin/Dropbox/VPM working directory/Python GSS/Data/SCBA Deployment 10 Mar 2020')
        # self.out_dir = os.path.join(os.getcwd(), 'output')
        self.out_dir = tk.StringVar()
        self.out_dir.set('/Users/austin/Dropbox/VPM working directory/Python GSS/output/derp/')


        # self.in_dir_text = tk.Text(self.root, height=1, width=80, highlightthickness=1, highlightbackground='grey')
        # self.in_dir_text = tk.Text(self.root, height=1, width=80, highlightthickness=1, highlightbackground='grey')

        # self.in_dir_text.grid(row=decoding_row+2, column=1, columnspan = 2, sticky='ew')
        # self.in_dir_text.insert(tk.END, self.in_dir)
        # self.in_dir_text.configure(state='disabled')
        self.in_dir_text = tk.Label(self.root, textvariable = self.in_dir, borderwidth=2)
        self.in_dir_text.grid(row=decoding_row+2, column=1, columnspan = 2, sticky='w')

        self.out_dir_text= tk.Label(self.root, textvariable = self.out_dir)
        self.out_dir_text.grid(row=decoding_row +3, column=1, columnspan = 2, sticky='w')
        
        self.in_progress_text= tk.Label(self.root,textvariable= self.in_progress_file)
        self.in_progress_text.grid(row=decoding_row + 4, column=1, columnspan = 2, sticky='w')

        tk.Label(self.root, text="Input Directory:",).grid(row=decoding_row + 2, column=0, sticky='e')
        tk.Label(self.root, text="Output Directory:",).grid(row=decoding_row + 3, column=0, sticky='e')
        tk.Label(self.root, text="Cache File:",).grid(row=decoding_row + 4, column=0, sticky='e')



        # buttons
        self.load_button = tk.Button(self.root, text="Select Input Directory", command=self.select_in_directory)
        self.load_button.grid(row=decoding_row+2, column=3, sticky='ew')
        self.out_button = tk.Button(self.root, text="Select Output Directory", command=self.select_out_directory)
        self.out_button.grid(row=decoding_row+3, column=3, sticky='ew')
        self.decode_button = tk.Button(self.root, text="Decode Telemetry", command=self.process_packets)
        self.decode_button.grid(row=decoding_row +2, column=4, sticky='ew')
        self.load_prev_button = tk.Button(self.root, text="Load Pickle File", command=self.load_previous_packets)
        self.load_prev_button.grid(row=decoding_row+3, column=4, sticky='ew')  
        self.cached_data_button = tk.Button(self.root, text="Select Packet Cache", command=self.select_packet_cache)
        self.cached_data_button.grid(row=decoding_row+4, column=3, sticky='ew')  
        self.packet_inspector_button = tk.Button(self.root, text="Packet Inspector", command = self.call_packet_inspector)
        self.packet_inspector_button.grid(row=decoding_row+4, column=4, sticky='ew')  
        self.reset_button = tk.Button(self.root, text="Clear All Data", command=self.clear_data)
        self.reset_button.grid(row=decoding_row+1, column=4, sticky='ew')
        self.pickle_button = tk.Button(self.root, text="Save Packets", command=self.save_packets)
        self.pickle_button.grid(row=decoding_row+5, column=4, sticky='ew')

        # checkboxes
        self.tlm_chk = tk.Checkbutton(self.root, text='load TLM files', variable=self.do_tlm)
        self.tlm_chk.grid(row=decoding_row+5, column=0, sticky='w')
        self.tlm_chk.var = self.do_tlm
        self.csv_chk = tk.Checkbutton(self.root, text='load CSV files', variable=self.do_csv)
        self.csv_chk.grid(row=decoding_row+5, column=1, sticky='w')
        self.csv_chk.var = self.do_csv
        self.prev_chk = tk.Checkbutton(self.root, text='load previously-cached packets', variable=self.do_previous)
        self.prev_chk.grid(row=decoding_row+5, column=2, sticky='w')
        self.prev_chk.var = self.do_previous
        self.move_chk = tk.Checkbutton(self.root, text='Move processed files', variable=self.move_completed)
        self.move_chk.grid(row=decoding_row+5, column=3, sticky='w')
        
        # horizontal line
        self.sep2 = ttk.Separator(self.root, orient="horizontal")
        self.sep2.grid(row=decoding_row+6, column=0, columnspan=6, sticky='ew')

        # ----------- Process burst and survey data from decoded packets ----------
        tk.Label(self.root, text="Reassemble Data Products from Packets:",  font=('Helvetica', 14, 'bold')).grid(row=process_row, column=0, columnspan=2, sticky='w')
        tk.Label(self.root, text="Burst decoding method:").grid(row=process_row +1, column=0, sticky='w')

        self.bm_menu = tk.OptionMenu(self.root, self.burst_mode, *self.burst_choices)
        self.bm_menu.grid(row=process_row+1, column=1, sticky='w')
        # self.burst_mode.trace('w',self.burst_menu_changed)

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



        self.update_counters();

        # ----------- Status messages -------
        tk.Label(self.root, text="Status Messages:",  font=('Helvetica', 12)).grid(row=save_row+1, column=0, columnspan=2, sticky='ew')

        self.statbox = tk.Listbox(self.root, height=4, width=30)
        self.statbox.grid(row = save_row + 2, column = 0, columnspan = 2, rowspan=4, sticky='n')
        self.statbox.bind('<<ListboxSelect>>', self.select_stat)

    	# self.stat_label = tk.Text(self.root, width=80, height=40, highlightthickness=1, highlightbackground='grey')
        # self.stat_label.pack()


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
        ttk.Separator(self.root, orient="vertical").grid(row=save_row+1, column=2, rowspan=4, sticky='nsw')

        

        # ----------- Plot data ----------
        ttk.Separator(self.root, orient="horizontal").grid(row=plot_row, column=0, columnspan=ncols, sticky='ew')
        tk.Label(self.root, text="Plot Survey Data:",  font=('Helvetica', 14, 'bold')).grid(row=plot_row+1, column=0, columnspan=1, sticky='w')

        self.load_survey_xml_button = tk.Button(self.root, text="Load survey XML data", command=self.load_survey_XML_file)
        self.load_survey_xml_button.grid(row=plot_row+1, column=1)

        tk.Label(self.root, text="E channel gain:", font=('Helvetica', 12)).grid(row=plot_row + 2, column=0,rowspan=2, sticky='e')
        tk.Label(self.root, text="B channel gain:", font=('Helvetica', 12)).grid(row=plot_row + 4, column=0,rowspan=2, sticky='e')
        tk.Label(self.root, text="Time axis:", font=('Helvetica', 12)).grid(row=plot_row + 6, column=0,rowspan=2, sticky='e')

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

        ttk.Separator(self.root, orient="horizontal").grid(row=plot_row + 8, column=0, columnspan=ncols, sticky='ew')
        tk.Label(self.root, text="Plot Burst Data:",  font=('Helvetica', 14, 'bold')).grid(row=plot_row+10, column=0, columnspan=1, sticky='w')
             
        self.load_burst_xml_button = tk.Button(self.root, text="Load burst XML data", command=self.load_burst_XML_file)
        self.load_burst_xml_button.grid(row=plot_row+11, column=4, sticky='ewn')

        self.load_calibration_button = tk.Button(self.root, text="Load calibration data", command=self.load_calibration)
        self.load_calibration_button.grid(row=plot_row+12, column=4, sticky='ewn')

        # self.status_button = tk.Button(self.root, text="View Status Messages", command=self.show_status_messages_window)
        # self.status_button.grid(row=plot_row+12, column=1, sticky='n')

        tk.Label(self.root, text="Available bursts:",  font=('Helvetica', 12)).grid(row=plot_row+10, column=2, sticky='ew')
        self.plot_burst_button = tk.Button(self.root, text="Plot Burst Data", command=self.call_plot_burst)
        self.plot_burst_button.grid(row=plot_row+10, column=4, sticky='ewn')

        self.listbox = tk.Listbox(self.root, height=3, width=30, selectmode = tk.EXTENDED)
        self.listbox.grid(row = plot_row + 11, column = 2, columnspan=2, rowspan=3)
        self.update_burst_list()

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
        return True

    def save_packets(self):
        ''' Save decoded (but unassembled) packets to a Pickle file '''

        fname = os.path.join(self.out_dir.get(), 'packets.pkl')
        logging.info(f'Saving decoded packets to {fname}')
        with open(fname,'wb') as file:
            pickle.dump(self.packets, file)
        return

    def save_survey(self):
        if self.survey_products:
            if self.file_format.get() in 'XML':
                outpath = os.path.join(self.out_dir.get(), self.survey_entry.get())
                logging.info(f'saving {len(self.survey_products)} survey products to {outpath}')
                write_survey_XML(self.survey_products,outpath)
            else:

                logging.info(f'{self.file_format.get()} not yet implemented - go bug Austin about it')
        else:
            logging.info('No survey data to save')
        return
    def save_burst(self):
        if self.burst_products:
            if self.file_format.get() in 'XML':
                outpath = os.path.join(self.out_dir.get(), self.burst_entry.get())
                logging.info(f'saving {len(self.survey_products)} burst products to {outpath}')
                write_burst_XML(self.burst_products, outpath)
            else:
                logging.info(f'{self.file_format.get()} not yet implemented - go bug Austin about it')
        else:
            logging.info('NO burst data to save')    
        return

    def save_stats(self):
        if self.status_messages:
            if self.file_format.get() in 'XML':
                outpath = os.path.join(self.out_dir.get(), self.status_entry.get())
                logging.info(f'saving {len(self.status_messages)} status messages to {outpath}')
                write_status_XML(self.burst_products, outpath)
            else:
                logging.info(f'{self.file_format.get()} not yet implemented - go bug Austin about it')
        else:
            logging.info('NO status messages to save')    
        return

    def save_all(self):
        logging.info(f'Saving all decoded data products')
        self.save_survey()
        self.save_burst()
        self.save_stats()
        return True

    def update_burst_list(self):
        logger = logging.getLogger(__name__)
        self.listbox.delete(0, tk.END)
        for b in self.burst_products:
            datestr = datetime.datetime.fromtimestamp(b['header_timestamp'], tz=datetime.timezone.utc)

            namestr = datestr.strftime('%m/%d/%Y') + ': '
            if b['config']['TD_FD_SELECT']:
                namestr+='Time Domain, '
            else:
                namestr+='Freq Domain, '
            namestr+= f"n={b['config']['burst_pulses']}"
            self.listbox.insert(tk.END, namestr)

    def update_time_fields(self):
        if self.packets:
            self.packets = sorted(self.packets, key = lambda p: p['header_timestamp'])
            self.t1_entry.delete(0, tk.END)
            self.t1_entry.insert(0, datetime.datetime.utcfromtimestamp(self.packets[0]['header_timestamp']).isoformat())
            self.t2_entry.delete(0, tk.END)
            self.t2_entry.insert(0, datetime.datetime.utcfromtimestamp(self.packets[-1]['header_timestamp']).isoformat())

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


    def load_survey_XML_file(self):
        logger = logging.getLogger(__name__)
        fname=filedialog.askopenfilename(initialdir=self.in_dir.get())

        if fname and fname.endswith(".xml"):
            self.survey_products.extend(read_survey_XML(fname))

            logger.info(f'Loaded {len(self.survey_products)} survey entries from {fname}')
            self.update_counters()

    def load_burst_XML_file(self):
        logger = logging.getLogger(__name__)
        fname=filedialog.askopenfilename(initialdir=self.in_dir.get())

        if fname and fname.endswith(".xml"):
            self.burst_products.extend(read_burst_XML(fname))

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
                self.packets = pickle.load(file)

            self.packet_len_text.set(f"{len(self.packets)} packets loaded")
        
        return
    def select_in_directory(self):
        self.in_dir.set(filedialog.askdirectory(initialdir=self.in_dir.get()))
        return True
    def select_packet_cache(self):
        self.in_progress_file.set(filedialog.askopenfilename(initialdir=os.getcwd()))
        return True

    def call_packet_inspector(self):
        if not self.packets:
            logging.info(f'No packets to inspect')
            return

        packet_inspector(self.root, self.packets)

    def call_plot_survey(self):
        if not self.survey_products:
            logging.info(f'No survey data present')
            return
        
        # if self.do_metadata.get():
        # Get selected metadata plots:
        lines_to_do = [self.line_plot_fields[x] for x in range(len(self.line_plot_fields))
                 if self.line_plot_enables[x].get()]
        logging.info(lines_to_do)

        plot_survey_data_and_metadata(self.root, self.survey_products,
            lines_to_do, cal_file=None, 
            plot_map = self.plot_map.get(),
            E_gain=self.survey_E_gain.get(),
            B_gain=self.survey_B_gain.get(), 
            bus_timestamps=self.survey_time_axis.get())
        # else:
        #     # Just plot E and B, no metadata
        #     # (This is a separate function to keep the figure sizing
        #     # and axes positioning cleaner)
        #     plot_survey_data(self.root, self.survey_products, 
        #         cal_file = self.cal_file, E_gain = self.survey_E_gain.get(),
        #         B_gain = self.survey_B_gain.get(),
        #         bus_timestamps=self.survey_time_axis.get())

    def call_plot_burst(self):
        if not self.burst_products:
            logging.info(f'No burst data present')
            return
        burst_index = self.listbox.curselection()

        for ind in self.listbox.curselection():        
            logging.info(f'Plotting burst {ind}')
            plot_burst_data(self.root, self.burst_products[int(ind)], self.cal_file)

    def select_out_directory(self):
        logging.info("you pushed the button!") 
        self.out_dir.set(filedialog.askdirectory(initialdir=self.out_dir.get()))

        return True

    def get_burst_command(self):
        ''' Parse and validate the command entered in the text box '''
        logger=logging.getLogger(__name__)
        inp_str = self.cmd_entry.get()
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
            cmd = np.fromstring(inp_str, dtype=int, sep=' ')

        logger.info(f'cmd: {cmd}')
        return cmd

    def process_burst_and_survey(self):
        logger = logging.getLogger(__name__)

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
                    n_pulses = int(self.repeats_entry.get())
                    logger.info(f'Processing bursts by experiment number')
                    B_data, unused_burst = decode_burst_data_by_experiment_number(self.packets, 
                                           burst_cmd = burst_cmd, burst_pulses = n_pulses)
                #     outs['burst'] = B_data
                    self.burst_products.extend(B_data)
            # Process any survey data
            if self.do_survey.get():
                logger.info("Decoding survey data")
                S_data, unused_survey = decode_survey_data(self.packets)
                self.survey_products = S_data


            # # Delete previous unused packet file -- they've either
            # # been processed by this point, or are in the new unused list
            # if args.do_previous:
            #     if os.path.exists(in_progress_file):
            #         os.remove(in_progress_file)

            #     # Store any unused survey packets
            #     unused = []
            #     if args.do_survey:
            #         unused += unused_survey
            #     if args.do_burst:
            #         unused += unused_burst
            #     # unused = unused_survey + unused_burst
            #     if unused:
            #         logging.info(f"Storing {len(unused)} unused packets")
            #         with open(in_progress_file,'wb') as f:
            #             pickle.dump(unused, f)

        else:
            logger.info('No packets loaded!')

        self.update_counters()
        self.update_burst_list()
        self.update_stat_list()

        return True

    def process_packets(self):
        logger = logging.getLogger(__name__)

        logging.info("Processing telemetry packets...") 
        d = os.listdir(self.in_dir.get())

        tlm_files = [x for x in d if x.endswith('.tlm')]
        csv_files = [x for x in d if x.endswith('.csv')]

        logging.info(f"found {len(tlm_files)} .tlm files")
        logging.info(f"found {len(csv_files)} .csv files")

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

        # Load any previously-unused packets, and add them to the list
        if self.do_previous.get():
            if os.path.exists(self.in_progress_file):
                logging.info("loading previous unused data")
                with open(self.in_progress_file,'rb') as f:
                    packets_in_progress = pickle.load(f) 
                    logging.info(f'loaded {len(packets_in_progress)} in-progress packets')
                    packets.extend(packets_in_progress)

        self.packets = packets
    
        self.update_counters()        
        self.update_time_fields()
        return True



    # def show_status_messages_window(self):
    #     self.stat_window = tk.Toplevel(self.root)

    #     tk.Label(self.stat_window, text="Status Messages:",  font=('Helvetica', 12)).pack() #grid(row=0, column=0, sticky='ew')

    #     self.statbox = tk.Listbox(self.stat_window, height=3, width=30, selectmode = tk.EXTENDED)
    #     self.statbox.pack()
    #     self.stat_label = tk.Text(self.stat_window, width=80, height=40, highlightthickness=1, highlightbackground='grey')
    #     self.stat_label.pack()


    #     self.stat_label.config(state=tk.NORMAL)
    #     self.stat_label.delete(1.0, tk.END)
    #     self.stat_label.insert(tk.END, "hey fucker")
    #     self.stat_label.config(state=tk.DISABLED)

    #     for stat in self.status_messages:
    #         datestr = datetime.datetime.fromtimestamp(stat['header_timestamp'], tz=datetime.timezone.utc)
    #         namestr = 'source: ' + stat['source'] + ', ' + datestr.strftime('%m/%d/%Y %H:%M:%S')
    #         self.statbox.insert(tk.END, namestr)

    #         self.statbox.bind('<<ListboxSelect>>', self.select_stat)

    def select_stat(self, *args):
        stat_ind = int(self.statbox.curselection()[0])
        stat_str = print_status([self.status_messages[stat_ind]])
        
        # self.stat_window = tk.Toplevel(self.root)


        # self.stat_label = tk.Text(self.stat_window, width=80, height=40, highlightthickness=1, highlightbackground='grey')
        # self.stat_label.pack()

        # self.stat_label.config(state=tk.NORMAL)
        # self.stat_label.delete(1.0, tk.END)
        # self.stat_label.insert(tk.END, f'{stat_str}')
        # self.stat_label.config(state=tk.DISABLED)
        logging.info(stat_str)





def main():

    logging.basicConfig(level=logging.DEBUG, format='[%(name)s]\t%(levelname)s\t%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)


    root = tk.Tk()
    gui = GUI(root)

    # t1 = threading.Thread(target=worker, args=[])
    # t1.start()

    root.mainloop()
    # t1.join()

main()
