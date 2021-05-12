from dataclasses import dataclass
from datetime import date
from typing import Union, List, Dict
from shapely.geometry import Polygon, MultiLineString

@dataclass
class Header():
    AmericaMakesSchemaVersion : date
    LayerThickness : float # > 0 
    DosingFactor : float  # > 0 optional
    BuildDescription : str = '' # optional

@dataclass
class VelocityProfile():
    ID : str
    Velocity : float # > 0
    LaserOnDelay : Union[float, int] # microsecond
    LaserOffDelay : Union[float, int] # microsecond
    JumpDelay : Union[float, int] # microsecond
    MarkDelay : Union[float, int] 
    PolygonDelay : Union[float, int]
    Mode : str = 'Auto' # Delay or Auto

@dataclass
class Wobble():
    On : int # 0 or 1
    Freq: int 
    Shape: int # [-1, 0, 1]
    TransAmp : float 
    LongAmp : float  

@dataclass
class Traveler():
    ID : str 
    Power : float = -1 # optional
    SpotSize : float = -1 # optional
    Wobble : Wobble = None # optional
    SyncDelay : int = 0 # only if multi laser

@dataclass
class SegmentStyle():
    ID : str
    VelocityProfileID : str 
    Traveler : Traveler
    LaserMode : str = "Independent" # FollowMe or Independent

@dataclass
class SegStart():
    X : float
    Y : float

@dataclass
class SegEnd():
    X : float 
    Y : float

@dataclass
class Segment():
    SegmentID : str
    SegStyle : str
    End : SegEnd

@dataclass
class Path():
    Type : str # hatch or contour
    Tag : str 
    NumSegments : int 
    SkyWritingMode : int # 0, 1, 2, 3
    Start : SegStart
    Segment : List[Segment]

@dataclass 
class Trajectory():
    TrajectoryID : int
    PathProcessingMode : str # sequential or concurrent
    Path : List[Path]

@dataclass
class PrintRegions():
    ID : str
    VelocityProfile : int
    ContourStyle : str 
    number_contour : int 
    contour_offset : float 
    contour_spacing : float 
    contour_skywriting : int 
    HatchStyle : str
    HatchOffset : float 
    HatchSpacing : float 
    HatchSkyWriting : int 
    HatchScheme : 0 
    InitialAngle : float 
    AngleRotation : float 

@dataclass
class PartsSetting():
    filename : str 
    x : float 
    y : float 
    z : float 
    region_profile : str
    contour_trajectory : int 
    hatch_trajectory : int
    contour : Dict[float, List[Polygon]] = None 
    hatch : Dict[float, List[MultiLineString]] = None
    