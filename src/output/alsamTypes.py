"""
Segment Style data container
"""
class SegmentStyle():
    def __init__(self) -> None:
        self._id="" #name of segment style
        self._vProfileID="" #name of velocity profile to associate with segment style
        self._laserMode="Independent" #string from set { "Independent", "FollowMe" }
        self._travelers=[] #list of traveler objects
    
    @property
    def id(self):
        return self._id
    @id.setter
    def setID(self,name:str):
        self._id=name
    
    @property
    def vProfileID(self):
        return self._vProfileID
    @vProfileID.setter
    def setVProfileID(self,name:str):
        self._vProfileID=name

    @property
    def laserMode(self):
        return self._laserMode
    @laserMode.setter
    def setLaserMode(self,mode:str):
        self.laserMode=mode

    @property
    def travelers(self):
        return self._travelers
    @travelers.setter
    def setTravelers(self,list:list): #needs to be defined as looking for a list of traveler types
        self.travelers=list
"""
Wobble data container
"""
class Wobble():
    def __init__(self) -> None:
        self._on=True
        self._freq=0.0
        self._shape=0
        self._transAmp=0.0
        self._longAmp=0.0
    
    @property
    def on(self):
        return self._on
    @on.setter
    def setOn(self,on:bool):
        self._on=on
    
    @property
    def frequency(self):
        return self._freq
    @frequency.setter
    def setFrequency(self,freq:float):
        self._freq=freq

    @property
    def shape(self):
        return self._shape
    @shape.setter
    def setShape(self,shape:int):
        self._shape=shape

    @property
    def transAmp(self):
        return self._transAmp
    @transAmp.setter
    def setTransAmp(self,amp:float):
        self._transAmp=amp

    @property
    def longAmp(self):
        return self._longAmp
    @transAmp.setter
    def setLongAmp(self,amp:float):
        self._longAmp=amp
"""
Traveler data container
"""
class Traveler():
    def __init__(self) -> None:
        self._id=0 #int
        self._syncDelay=0.0 #float
        self._power=0.0 #float
        self._spotSize=0 #spot size?
        self._wobble=Wobble()
    
    @property
    def id(self):
        return self._id
    @id.setter
    def setID(self,id:int):
        self._id=id

    @property
    def syncDelay(self):
        return self._syncDelay
    @id.setter
    def setSyncDelay(self,delay:float):
        self._syncDelay=delay

    @property
    def power(self):
        return self._power
    @power.setter
    def setPower(self,power:float):
        self._power=power

    @property
    def spotSize(self):
        return self._spotSize
    @spotSize.setter
    def setSpotSize(self,size:int):
        self._spotSize=size

    @property
    def wobble(self):
        return self._wobble
    @wobble.setter
    def setWobble(self,wobble:Wobble):
        self._wobble=wobble

"""
Velocity profile data container
"""
class VelocityProfile():
    def __init__(self) -> None:
        self._id=""
        self._velocity=0.0
        self._mode="Auto"
        self._laserOnDelay=0.0
        self._laserOffDelay=0.0
        self._jumpDelay=0.0
        self._markDelay=0.0
        self._polygonDelay=0.0

    @property
    def id(self):
        return self._id
    @id.setter
    def setID(self,id:str):
        self._id=id

    @property
    def velocity(self):
        return self._velocity
    @velocity.setter
    def setVelocity(self, vel:float):
        self._velocity=vel

    @property
    def mode(self):
        return self._mode
    @mode.setter
    def setMode(self,mode:str):
        self._mode=mode

    @property
    def laserOnDelay(self):
        return self._laserOnDelay
    @laserOnDelay.setter
    def setLaserOnDelay(self,delay:float):
        self._laserOnDelay=delay

    @property
    def laserOffDelay(self):
        return self._laserOffDelay
    @laserOffDelay.setter
    def setLaserOffDelay(self,delay:float):
        self._laserOffDelay=delay 

    @property
    def jumpDelay(self):
        return self._jumpDelay
    @jumpDelay.setter
    def setJumpDelay(self,delay:float):
        self._jumpDelay=delay 

    @property
    def markDelay(self):
        return self._markDelay
    @markDelay.setter
    def setMarkDelay(self,delay:float):
        self._markDelay=delay 

    @property
    def polygonDelay(self):
        return self._polygonDelay
    @polygonDelay.setter
    def setPolygonDelay(self,delay:float):
        self._polygonDelay=delay 
