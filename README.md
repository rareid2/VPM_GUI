# VPM_GUI
Ground Support Software for AFRL's VPM satellite -- now with a nice graphical interface!

## Starting

python gui.py

## Requirements

This was written on OSX, using Anaconda3.

The main dependencies should be met by Anaconda3, which include:
  - Numpy
  - Scipy
  - Pyplot
  - Basic Python modules (datetime, os, pickle, etc)
  - Tk
 
But you'll probably need to install:
  - Matplotlib.basemap
  

## Basics:

The GUI is divided into 5 sections:
  - Decode raw telemetry:
    
    This section is for decoding raw data from the satellite, either in binary ('.tlm') or csv files.
      Begin by selecting an input directory of files, and optionally an output directory, and clicking "Decode Telemetry".
      After the packets have been decoded, you can save them as an interstitial Pickle file.
      
      The Packet Inspector tool shows the various decoded packets, sorted by their bus timestamp, and the data type.
      
  - Reassemble Data Products from Packets:
    
    This section takes the decoded VPM data packets, and reassembles them into useful data products.
    
    Burst data can be decoded in several ways:
      Group by Status Packets is the ideal method -- assuming we have a complete burst loaded, this is the one-click method.
      
      Group by Timestamp bins burst data between two given timestamps. You'll need to input the number of repeats and the issuing burst command manually.
      
      Group by Experiment Number will process all burst packets with the same experiment number. Again, you'll need the burst command and number of repeats.
      
 - Save Data Products:
 
    Burst, Survey, and Status data can be saved here. So far only XML is implemented. Files are saved in the output directory specified at the top.
    
    Any decoded status messages will show up in the list box on the left. Click one to print it in the text field at the bottom.
    
    
 - Plot Survey Data:
   
   You can load previously-decoded survey data in XML formats here.
   
   The checkboxes enable / disable the different metadata fields included with the GPS card. If nothing is selected, only E and B will be plotted.
   
   If any metadata is checked, only entries with GPS data will be shown.
   
   The E and B channel gain options will be used for calibration; however they are not currently implemented.
   
   The time axis can be selected to show either the payload, or the bus timestamps.

- Plot Burst Data:
  
  You can load previously-decoded burst data in XML format here.
  
  Any loaded bursts will show up in the list box -- just hit "plot" to plot the selected ones.
      
      
