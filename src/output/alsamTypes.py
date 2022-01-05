"""
Segment Style data container
"""
class SegmentStyle():
    def __init__(self):
        self.id="" #name of segment style
        self.vProfileID="" #name of velocity profile to associate with segment style
        self.laserMode="Independent" #string from set { "Independent", "FollowMe" }
        self.travelers=[] #list of traveler objects     
"""
Wobble data container
"""
class Wobble():
    def __init__(self) -> None:
        self.on=True
        self.freq=0.0
        self.shape=0
        self.transAmp=0.0
        self.longAmp=0.0
"""
Traveler data container
"""
class Traveler():
    def __init__(self) -> None:
        self.id=0 #int
        self.syncDelay=0.0 #float
        self.power=0.0 #float
        self.spotSize=0 #spot size?
        self.wobble=Wobble()
"""
Velocity profile data container
"""
class VelocityProfile():
    def __init__(self) -> None:
        self.id=""
        self.velocity=0.0
        self.mode="Auto"
        self.laserOnDelay=0.0
        self.laserOffDelay=0.0
        self.jumpDelay=0.0
        self.markDelay=0.0
        self.polygonDelay=0.0
