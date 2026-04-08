from itertools import cycle
from time import sleep
n_points = 5
points_l = [ '.' * i + ' ' * (n_points - i) + '\r' for i in range(n_points) ]
cond = True

for points in cycle(points_l):
    print(points, end='')
    sleep(0.1)
    if not cond:
        break
