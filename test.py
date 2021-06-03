from shapely.geometry import LineString

bottom_left = (0, 0)
bottom_right = (1, 0)
top_left = (0, 1)
top_right = (1, 1)
wayvertical_bottom = (5, -25555)
wayvertical_top = (5, 25555)
line1 = LineString([bottom_left, bottom_right])
line2 = LineString([wayvertical_bottom, wayvertical_top])
intersection = line1.intersection(line2)
print(intersection)

