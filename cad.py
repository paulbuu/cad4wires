"""
MIT License

Copyright 2022 UK Research and Innovation
Author: Paul Booker (paul.booker@stfc.ac.uk)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


This script converts a .csv or .txt file into a .CAD file for a Hesse BJ820 wire-bonder:
csv file can be tab-separated, only columns 2, 3, 5 and 6 are read.
Columns 1 and 4 are free for user.
    user | srceX | srceY | user | destX | destY

I try to avoid references to "chip", "die", "pcb".
Instead use srce or dest to denote bonding direction
The test pieces have all been chip on pcb. See user_settings = {'bonding': 'out'}
It does not cater for chip in package (srce-dest reversed), = {'bonding': 'in'}. This is untested.

ASSUMED:
A 4-sided srce. SVG borders may need adapting for other formats.
A shrinking dest substrate; 0.1% shrinkage of pcb seen on large designs

No-Split option is for chips where 
each srce row needs no further dividing between destination rows
TODO
Over-write user-settings with config file and/or accept input.
"""

from math import radians, pi, cos, sin, atan2
import sys


def list_n(ll, n):
    new = []
    for l in ll:
        new.append(l[n])
    return new


def mid_value(num_list):
    n = sorted(num_list)
    m = rnd((n[0] + n[-1]) / 2)
    return m


def rnd(num):
    return round(num, 3)


def get_dupes(l, min_row):
    d = {i:l.count(i) for i in l}
    n = {}
    for kkey, val in d.items():
        if val > min_row:
            n.update({kkey:val})
    return n


def eqls(num, comp, band):
    if num - band < comp and comp < num + band:
        return True


def dbg(thing, num):
    flout = open('dbg'+str(num)+'.py', 'wt')
    print(thing, file=flout)
    flout.close()


def create_rank_lists(ranks):
    arr = []
    for i in range(len(ranks)):
        arr.append(list())
        for j in range(len(ranks[i])):
            arr[i].append(list())
    return arr


def sort_inner_ranks(inner):
    inner[0].sort(reverse=True)
    inner[1].sort()
    inner[2].sort()
    inner[3].sort(reverse=True)


def sort_outer_ranks(outer):
    outer[0].sort()
    outer[1].sort(reverse=True)
    outer[2].sort(reverse=True)
    outer[3].sort()


def dbg_num_wires(wirelist, string):
    total = 0
    for i in range(len(wirelist)):
        for j in range(len(wirelist[i])):
            total += len(wirelist[i][j])
    print(string, total)


def rotate_pt(o_x, o_y, pt_x, pt_y, angle):
    """rotate around given origin"""
    angle = radians(angle)
    c_x = pt_x - o_x
    c_y = pt_y - o_y
    cs = cos(angle)
    sn = sin(angle)
    return o_x + cs * c_x - sn * c_y, o_y + sn * c_x + cs * c_y


def rotate(o_x, o_y, pts, angle):
    """rotate srce and dest of wire about an origin"""
    s = rotate_pt(o_x, o_y, pts[0], pts[1], angle)
    d = rotate_pt(o_x, o_y, pts[2], pts[3], angle)
    return [rnd(s[0]), rnd(s[1]), rnd(d[0]), rnd(d[1])]


def scale(o_x, o_y, pts, src_scl, dst_scl):
    """apply scale about an origin"""
    s_x = (pts[0] - o_x) * src_scl + o_x
    s_y = (pts[1] - o_y) * src_scl + o_y
    d_x = (pts[2] - o_x) * dst_scl + o_x
    d_y = (pts[3] - o_y) * dst_scl + o_y
    return [s_x, s_y, d_x, d_y]


def translate(o_x, o_y, pts, settings):
    """move relative to an origin"""
    t_x = settings['x'] - o_x
    t_y = settings['y'] - o_y
    return [rnd(pts[0] + t_x), rnd(pts[1] + t_y), rnd(pts[2] + t_x), rnd(pts[3] + t_y)]


def sort_by_angle(nlst, qpi):
    """Determine side of chip for each wire.
    Adjust qpi value in radians to change quadrants based on wire-angles"""

    #       \nw____ /ne
    #   +    |     |
    #  pi ---|     |--- 0
    #   -    |_____|
    #       /sw     \se
    up = []
    lf = []
    dn = []
    rt = []

    ne = qpi
    nw = pi - qpi
    sw = -pi + qpi
    se = -qpi

    for lin in nlst:
        srcx, srcy, desx, desy = lin
        dx = desx - srcx
        dy = desy - srcy
        angle = atan2(dy, dx)

        if ne <= angle < nw:
            up.append(lin)
        if angle >= nw or angle < sw:
            lf.append(lin)
        if sw <= angle < se:
            dn.append(lin)
        if se <= angle < ne:
            rt.append(lin)
    return up, lf, dn, rt


def get_diffs(ranks):
    diffs = []
    for i in range(len(ranks)):
        diffs.append([])
        for j in range(len(ranks[i]) - 1):
            diffs[i].append(rnd(abs(ranks[i][j] - ranks[i][j+1])))
    return diffs


def merge_by_diff(lst, diffs, tol):
    for i in range(len(diffs)):
        count = []
        for j in range(len(diffs[i])):
            if diffs[i][j] < tol:
                lst[i][j] += lst[i][j + 1]
                count.append(j+1)
        count.sort(reverse=True)
        for k in range(len(count)):
            lst[i].pop(count[k])


def chk_list(w, strg):
    s = 0
    a = []
    for i in range(len(w)):
        a.append(len(w[i]))
        s += len(w[i])
    print(strg, s, a)


def chk_nested(w, strg):
    for i in range(len(w)):
        chk_list(w[i], strg + str(i) + ':')


def refheader(ref, xy1, xy2, settings):
    return f'''refpnt         {ref},         1,   {xy1['x']},    {xy1['y']}
refpnt         {ref},         2,   {xy2['x']},    {xy2['y']}
refuspower     {ref},         1,    {settings['usp']}
refforce       {ref},         1,    {settings[ 'bf']}
refustime      {ref},         1,    {settings['ust']}'''


user_settings = {
    'srce': {
        'usp': '26.000',
        'ust': '0.060',
        'bf' : '20.000',
        'scale': 1,
        'no-split': False},
    'dest': {
        'usp': '24.000',
        'ust': '0.060',
        'bf' : '20.000',
        'scale': 0.99975},
    '715-table': {
        'x' : -126,
        'y' : -10},
    '820-table': {
        'x' : -196,
        'y' : 10},
    'rotation': 0,
    'tolerance': 0.02, # in mm
    'bonding': 'out'
}

tolerance = user_settings['tolerance'] # in mm
bonding = user_settings['bonding']

title = "C100mm.csv" # sys.argv[1]
out_file = [x.strip() for x in [x.strip() for x in title.split('.')][0].split('\\')][-1]

fin = open(title, 'rt') # comma delimited, or tab csv
lines = fin.readlines()
fin.close()

nlines = []
for line in lines:

    line = [float(xy.strip()) for xy in line.split(',')]
    nlines.append([line[1]-125000, line[2]-131000, line[4]-125000, line[5]-131000])# insert hack for origin discrepancy here!

lines = None

# Test for origin discrepancy in data
# Origin must be corrected before sorting wires by angle!

print(mid_value(list_n(nlines, 0)), 'srce-x')
print(mid_value(list_n(nlines, 1)), 'srce-y')
print(mid_value(list_n(nlines, 2)), 'dest-x')
print(mid_value(list_n(nlines, 3)), 'dest-y')

# - Find ranks of coords and build ranks per direction
wireset = sort_by_angle(nlines, radians(45))

srce_ranks = []
dest_ranks = []

srce_rank_debug = []
# getDupes can show value in each row, but only the key is used
# build alternative sorting for circle test
for i in range(len(wireset)):

    if not i%2:
        srce_dupes = get_dupes(list_n(wireset[i], 1), 0)
        dest_dupes = get_dupes(list_n(wireset[i], 3), 0)
    if i%2:
        srce_dupes = get_dupes(list_n(wireset[i], 0), 0)
        dest_dupes = get_dupes(list_n(wireset[i], 2), 0)

    if srce_dupes:
        srce_ranks.append([])
        #srce_rank_debug.append([])
    if dest_dupes:
        dest_ranks.append([])

    for key, value in srce_dupes.items():
        srce_ranks[i].append(key)
        #srce_rank_debug[i].append(value)
    for key, value in dest_dupes.items():
        dest_ranks[i].append(key)

#print(srce_dupes)
#Ensure ranks are listed in correct order for wirebonding
if bonding == 'out':
    sort_inner_ranks(srce_ranks)
    sort_outer_ranks(dest_ranks)
else:
    sort_outer_ranks(srce_ranks)
    sort_inner_ranks(dest_ranks)

# print(srce_ranks)
# print(srce_rank_debug)
# print(dest_ranks)

# Here, for Kirana, some ranks are so similar they can be merged
# but merging will be done after building wires_by_srce and wires_by_dest
# and then be re-ordered by x or y coordinate value

# First get the spacing difference between ranks
srce_rank_diffs = get_diffs(srce_ranks)

# Build nests of empty lists for each rank value
wires_by_srce = create_rank_lists(srce_ranks)

for i in range(len(srce_ranks)):
    for j in range(len(srce_ranks[i])):

        for wire in wireset[i]:

            if i%2: # l r
                srce_val = wire[0]
            if not i%2: # u d
                srce_val = wire[1]
            if srce_val == srce_ranks[i][j]:
                wires_by_srce[i][j].append(wire)

srce_rank_tol = 0.02 # mm
#merge_by_diff(wires_by_srce, srce_rank_diffs, srce_rank_tol)

# chk_nested(wires_by_srce, 'wires_by_srce')
#dbg_num_wires(wires_by_srce, 'wires_by_srce')

# - i, j, k iterate through wires_by_srce, apply wire_num, srce_ref, dest_ref

#If each srce row has only one dest row set one_to_one to True
one_to_one = user_settings['srce']['no-split']

if not one_to_one:
    wires_by_dest = create_rank_lists(dest_ranks)

    for i in range(len(wires_by_srce)):
        for wires in wires_by_srce[i]:

            leni = len(dest_ranks[i])
            if leni == 0:
                wires_by_dest[i].append(wires)

            for wire in wires:

                for m in range(len(dest_ranks[i])):
                    if i%2:
                        row_value = wire[2]
                    if not i%2:
                        row_value = wire[3]
                    if eqls(dest_ranks[i][m], row_value, tolerance):
                        wires_by_dest[i][m].append(wire)
if one_to_one:

    for i in range(len(wires_by_srce)):
        for wires in wires_by_srce[i]:
            if not i%2:
                wires.sort(key=lambda x: x[0])
            if i%2:
                wires.sort(key=lambda y: y[1])

    wires_by_dest = wires_by_srce

# If KIRANA, merge by force; merge by diffs inadequate.
# TODO: a user setting to "force merge 3 : 1 lr"
# for i in range(len(wires_by_dest)):
#     wd = wires_by_dest[i]
#     if i%2:
#         wd.append(wd[0] + wd[1] + wd[2])
#         wd.append(wd[3] + wd[4] + wd[5])
#         del wd[:6]
#         wd[0].sort(key=lambda y: y[1])
#         wd[1].sort(key=lambda y: y[1])

# If PIMMS, merge by force
# for i in range(len(wires_by_dest)):
#     wd = wires_by_dest[i]
#     wd.insert(0, wd[0] + wd[1] + wd[2])
#     del wd[1:4]


#chk_nested(wires_by_dest, 'wires_by_dest')
dbg_num_wires(wires_by_dest, 'wires_by_dest')

# Rotation, scale and translation of data - locate source centre for transforms
cx = mid_value(list_n(nlines, 0))
cy = mid_value(list_n(nlines, 1))
rotation = user_settings['rotation']
s_scale  = user_settings['srce']['scale']
d_scale  = user_settings['dest']['scale']
move_to  = user_settings['820-table']

for i in range(len(wires_by_dest)):
    for j in range(len(wires_by_dest[i])):
        for k in range(len(wires_by_dest[i][j])):

            wires_by_dest[i][j][k] = rotate(cx, cy, wires_by_dest[i][j][k], rotation)
            wires_by_dest[i][j][k] = scale(cx, cy, wires_by_dest[i][j][k], s_scale, d_scale)
            wires_by_dest[i][j][k] = translate(cx, cy, wires_by_dest[i][j][k], move_to)

print(wire)
# translation commented out while SVG output is required
print("cx", cx, "cy", cy)
cx = None # not translated
cy = None # not translated

# Dest ref points are in the first and last wire of the outer ranks... sometimes!
# Ref pt pairs are in dest_list = [[ref1: horizontal], [ref2: vertical]]
# Option to reverse order of bonding for better refpoints
boool = []
for i in range(len(wires_by_dest)):
    boool.append(1 if wires_by_dest[i] else 0)
dest_refs = []
for i in range(len(wires_by_dest)):
    # if not i % 2:
    #     wires_by_dest[i].reverse()
    dest_refs.append({
        'x': rnd(wires_by_dest[i][-1][0][2]),
        'y': rnd(wires_by_dest[i][-1][0][3])
    } if wires_by_dest[i] else None)
    dest_refs.append({
        'x': rnd(wires_by_dest[i][-1][-1][2]),
        'y': rnd(wires_by_dest[i][-1][-1][3])
    } if wires_by_dest[i] else None)

print(dest_refs)


# assumes 4-sided bonding; try one of the following!
# dest_list = [[dest_refs[2], dest_refs[6]], [ dest_refs[0], dest_refs[4]]]
# test.txt
#dest_list = [[dest_refs[3], dest_refs[6]], [ dest_refs[0], dest_refs[5]]]
# PIMMS
#dest_list = [[dest_refs[3], dest_refs[6]], [dest_refs[1], dest_refs[4]]]
# C100
dest_list = [[dest_refs[2], dest_refs[6]], [dest_refs[5], dest_refs[1]]]
# unfinished range of options
print("boool", boool)
if boool[0] == 0:
    dest_list[0] = [dest_refs[4], dest_refs[5]]
if boool[1] == 0:
    dest_list[1] = [dest_refs[6], dest_refs[7]]
if boool[2] == 0:
    dest_list[0] = [dest_refs[0], dest_refs[1]]
if boool[3] == 0:
    dest_list[1] = [dest_refs[3], dest_refs[3]]
# print(dest_list)
# [
# 	[
# 		{'x': -17.682, 'y': -12.727}, {'x': 17.682, 'y': -12.552}
# 	],
# 	[
# 		{'x': -11.039, 'y': 17.982},{'x': -11.978, 'y': -17.782}
# 	]
# ]
# Srce ref points are in the first and last wire of the rank!
srce_list = create_rank_lists(wires_by_dest)# or dest_ranks if no merging has happened

for i in range(len(wires_by_dest)):
    for j in range(len(wires_by_dest[i])):

        leni = len(dest_ranks[i])
        if not leni:
            rank = srce_list[i]
        if leni:
            rank = srce_list[i][j]
        rank.append({
            'x': rnd(wires_by_dest[i][j][0][0]),
            'y': rnd(wires_by_dest[i][j][0][1])
        })
        rank.append({
            'x': rnd(wires_by_dest[i][j][-1][0]),
            'y': rnd(wires_by_dest[i][j][-1][1])
        })
#
# Build the CAD file!
#
s_params = user_settings['srce']
d_params = user_settings['dest']
fout = open(out_file + '.CAD', 'wt')

print(refheader(1, dest_list[0][0], dest_list[0][1], d_params), file=fout)
print(refheader(2, dest_list[1][0], dest_list[1][1], d_params), file=fout)

wire_num = 1
srce_ref = 3
tb = ',    '
for i in range(len(srce_list)):
    for points in srce_list[i]:

        print(refheader(srce_ref, points[0], points[1], s_params), file=fout)
        srce_ref += 1

srce_ref = 3
for i in range(len(wires_by_dest)):
    for j in range(len(wires_by_dest[i])):
        for wire in wires_by_dest[i][j]:
            if i%2:
                dest_ref = 1
            if not i%2:
                dest_ref = 2

            n = str(wire_num)
            srce = str(wire[0]) + tb + str(wire[1])
            dest = str(wire[2]) + tb + str(wire[3])
            print('bondpnt '+n+',    1,    '+str(srce_ref)+tb+srce, file=fout)
            print('bondpnt '+n+',    2,    '+str(dest_ref)+tb+dest, file=fout)
            wire_num += 1
        srce_ref += 1

print(wire_num-1, 'wires allocated,', srce_ref-3, 'source ref-systems')

print('CAD file created')
fout.close()
