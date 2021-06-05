from shapely.geometry import LineString


line1 = LineString([(-31, 29), (44, 45)])
line2 = LineString([(-28, -100), (-28, 100)])
intersection = line1.intersection(line2)
print(intersection)

"""
def func(a: list):
    if not isinstance(a, list):
        raise TypeError("Expected a to be of type {}, but was instead of type {}".format(list, type(a)))
    print(a)
func(2)
"""
