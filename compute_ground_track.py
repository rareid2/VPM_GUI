import numpy as np
import os
import ephem
import datetime



# Helper functions
class Satellite(object):
    def __init__(self, tle1, tle2, name): 
        self.tle_rec = ephem.readtle(name, tle1, tle2)
        self.curr_time = None
        self.name = name
        self.coords = None    # Long, Lat! XY on a map, but isn't pleasant to say out loud.
  
    def compute(self,plotdate):
        self.tle_rec.compute(plotdate)
        self.curr_time = plotdate
        self.coords = [(180.0/np.pi)*self.tle_rec.sublong, (180.0/np.pi)*self.tle_rec.sublat]

    def coords_at(self,plotdate):
        ''' Get full coordinates for orbit '''
        self.compute(plotdate)
        return self.coords
    
    def coords_3d_at(self,plotdate):
        ''' Get full coordinates for orbit '''
        self.compute(plotdate)
        print(self.tle_rec)
        return self.tle_rec





def compute_ground_track(TLE, t1, t2, tstep = datetime.timedelta(seconds=30)):
    '''
    plot the ground track of a satellite, as specified by its TLE, between times
    t1 and t2 
    '''
    
    assert (t2 > t1)
    # Satellite object:
    sat  = Satellite(TLE[0], TLE[1],'VPM')

    traj = []
    
    tvec = []   
    
    curtime = t1
    while curtime < t2:
        sat.compute(curtime)    
        traj.extend([sat.coords_at(curtime)])
        tvec.append(curtime)
        curtime += tstep
    traj = np.array(traj)
    
    return traj, tvec