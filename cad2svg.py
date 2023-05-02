#!/usr/bin/env python
# coding: utf-8
"""
Combining CAD and SVG scripts offers advantage of including die pin nos.
Currently bonds in clockwise order, starting North.

Input data 5 columns .csv file
1/ Die pin no
2/ Source x position
3/ Source y position
4/ Destination x position
5/ Destination y position

TODO:
Rotation
Scale
"""
from math import radians, pi, cos, sin, atan2
import sys
from pprint import pprint



# This part for Jupyter notebook only
# from IPython.display import SVG
# class ImageFile(object):
#     """Class for storing an image location."""
#
#     def __init__(self, fpath):
#         self.fpath = fpath
#         self.format = fpath.split('.')[-1]
#
#     def _repr_png_(self):
#         if self.format == 'png':
#             return open(self.fpath, 'r').read()
#
#     def _repr_jpeg_(self):
#         if self.format == 'jpeg' or self.format == 'jpg':
#             return open(self.fpath, 'r').read()
#
#     def _repr_svg_(self):
#         if self.format == 'svg':
#             return open(self.fpath, 'r').read()


"""
 First some defs
"""


def pp(string, thing):
    print(string)
    pprint(thing, width=99)


def list_n(list_of_lists, n):
    """from nested lists, build list of a given index"""
    return [lst[n] for lst in list_of_lists]


def mid_value(num_list):
    n = sorted(num_list)
    m = rnd((n[0] + n[-1]) / 2)
    return m


def rnd(num):
    return round(num, 3)


def eqls(num, comp, band):
    """true if within tolerance"""
    if num - band < comp < num + band:
        return True


def min_max(num_list):
    """min and max of list"""
    result = sorted(num_list)
    return result[0], result[-1]


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
    """Determine side of Die for each wire.
    Adjust qpi value in radians to change quadrant-angle to suit wire-angles
          \nw____ /ne
      +    |     |
     pi ---|     |--- 0
      -    |_____|
          /sw     \se
    """
    up = []
    lf = []
    dn = []
    rt = []

    ne = qpi
    nw = pi - qpi
    sw = -pi + qpi
    se = -qpi

    for lin in nlst:
        _, srcx, srcy, desx, desy = lin
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


class DieSide:

    def __init__(self, facing, wires):
        self.facing = facing
        self.wires = wires
        srce_idx = 1 if self.facing in ['W', 'E'] else 2
        dest_idx = 3 if self.facing in ['W', 'E'] else 4
        # filter values to establish rank count
        self.srce_dupes = self.get_dupes([wire[srce_idx] for wire in wires], 0)
        self.dest_dupes = self.get_dupes([wire[dest_idx] for wire in wires], 0)
        self.wires_by_srce = self.wires_to_ranks(index=srce_idx)
        self.wires_by_dest = self.split_srce_ranks_by_dest(index=dest_idx)

        # rank diffs only used to decide on merging neighbouring ranks
        if len(self.srce_dupes) > 1:
            self.srce_rank_diffs = self.get_diffs(self.srce_dupes)
        if len(self.dest_dupes) > 1:
            self.dest_rank_diffs = self.get_diffs(self.dest_dupes)

    def get_dupes(self, lst, min_row):
        """Assumes duplication of values constitutes separate rows of pads"""
        d = {i:lst.count(i) for i in lst}
        n = []
        for key, val in d.items():
            if val > min_row:
                n.append([key, val])
        return n

    def get_diffs(self, ranks):
        """Distances between rows of pads"""

        diffs = []
        for i in range(len(ranks)-1):
            diffs.append(rnd(abs(ranks[i][0] - ranks[i+1][0])))
        return diffs

    def wires_to_ranks(self, index):
        """ Sorts into ranks according to duplicated values """
        wires_by_rank = []
        for dupe in self.srce_dupes:
            rank = self.dupe_to_rank(dupe, self.wires, index)
            wires_by_rank.append(rank)
        return wires_by_rank

    def split_srce_ranks_by_dest(self, index):
        """ Split source ranks according to destination duplicated values """
        wires_by_rank = []
        for srce_rank in self.wires_by_srce:
            for dupe in self.dest_dupes:
                rank = self.dupe_to_rank(dupe, srce_rank, index)
                wires_by_rank.append(rank)
        return wires_by_rank

    def dupe_to_rank(self, dupe, wires, index) -> list:
        """ Test given index value against duplicate value and return collection """
        rank = []
        for wire in wires:
            if wire[index] == dupe[0]:
                rank.append(wire)
        return rank


class References:
    """
    Builds the headers of the CAD file for each reference system
    """
    _ref_count = 0
    _wire_count = 0
    dest_strings = []
    srce_strings = []
    ref_sys_points = []
    ref_headers = []

    def __init__(self, wires_by_dest):
        #order of ref systems, always one dest ref system, one or more srce ref systems
        self.dest_ref_system = self.dest_refs(wires_by_dest)
        References.ref_sys_points.append(self.dest_ref_system)
        self.srce_ref_systems = []
        self.cad_strings = []
        for rank in wires_by_dest:
            self.srce_refs(rank)
            self.wires_to_strings(rank)
        for srce in self.srce_ref_systems:
            References.ref_sys_points.append(srce)

    def srce_refs(self, rank) -> None:
        """
        Coordinate strings for ref points
        :param rank:
        :return: None
        """
        References._ref_count +=1
        self.srce_strings.append(str(References._ref_count))
        self.srce_ref_systems.append({
            str(References._ref_count): {
                "1": (str(rank[0][1]), str(rank[0][2])),
                "2": (str(rank[-1][1]), str(rank[-1][2]))
            }
        })

    def dest_refs(self, wires_by_dest) -> dict:
        """
        Coordinate strings for ref points
        :param wires_by_dest:
        :return: dict
        """
        References._ref_count += 1
        rank = wires_by_dest[-1]
        self.dest_strings.append(str(References._ref_count))
        return {
            str(References._ref_count): {
                "1": (str(rank[0][3]), str(rank[0][4])),
                "2": (str(rank[-1][3]), str(rank[-1][4]))
            }
        }

    def wires_to_strings(self, rank) -> None:
        """ Two lines to represent one wire in the CAD file """
        gap = ',    '
        dref = list(self.dest_ref_system.keys())[0]
        nums = [d.keys() for d in self.srce_ref_systems]
        sref = list(nums[-1])[0]
        for wire in rank:
            References._wire_count += 1
            w_num = str(References._wire_count)
            srce = str(wire[1]) + gap + str(wire[2])
            dest = str(wire[3]) + gap + str(wire[4])
            self.cad_strings.append('bondpnt '+w_num+',    1,    '+str(sref) + gap+srce)
            self.cad_strings.append('bondpnt '+w_num+',    2,    '+str(dref) + gap+dest)


def refheader(ref_sys: str, first_co: str, second_co: str, settings: dict) -> str:
    """This paragraph is required for each reference system at the top of the file"""
    return (
        f'''refpnt         {ref_sys},         1,   {first_co[0]},    {first_co[1]}'''
        f'''\rrefpnt         {ref_sys},         2,   {second_co[0]},    {second_co[1]}'''
        f'''\rrefuspower     {ref_sys},         1,    {settings['usp']}'''
        f'''\rrefforce       {ref_sys},         1,    {settings[ 'bf']}'''
        f'''\rrefustime      {ref_sys},         1,    {settings['ust']}'''
    )


def get_refheaders(srce_params, dest_params):
    for refsystem in References.ref_sys_points:
        for key, coords in refsystem.items():
            header = "No header assigned: " + key
            if key in References.dest_strings:
                header = refheader(key, coords['1'], coords['2'], dest_params)
            if key in References.srce_strings:
                header = refheader(key, coords['1'], coords['2'], srce_params)
            References.ref_headers.append(header)

"""
User settings
"""
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
    'tolerance': 0.02,  # in mm
    'bonding': 'out'
}
tolerance = user_settings['tolerance'] # in mm
bonding = user_settings['bonding']

"""
 Input file name
"""

title = "C100mm.csv" 
out_file = [x.strip() for x in [x.strip() for x in title.split('.')][0].split('\\')][-1]
# print(out_file)

"""
 Organize according to angle of wire, requires centres checking
"""
fin = open(title, 'rt')  # comma delimited, or tab csv
lines = fin.readlines()
fin.close()

nlines = []
for line in lines:
    line = [float(xy.strip()) for xy in line.split(',')]
    pin = int(line[0])
    sx = line[1]
    sy = line[2]
    dx = line[4]
    dy = line[5]
    # insert hack for origin discrepancy here!
    nlines.append((pin, sx-125000, sy-131000, dx-125000, dy-131000))
    #nlines.append((pin, sx, sy, dx, dy))

lines = None

# Test for origin discrepancy in data
# Origin must be corrected before sorting wires by angle!

# print(mid_value(list_n(nlines, 0)), 'srce-x')
# print(mid_value(list_n(nlines, 1)), 'srce-y')
# print(mid_value(list_n(nlines, 2)), 'dest-x')
# print(mid_value(list_n(nlines, 3)), 'dest-y')

# Find ranks of coords and build ranks per direction
up, lf, dn, rt = sort_by_angle(nlines, radians(45))

nort = DieSide(facing='N', wires=up)
west = DieSide(facing='W', wires=lf)
sout = DieSide(facing='S', wires=dn)
east = DieSide(facing='E', wires=rt)

"""
Establish the order of ref_systems (and pass on to svg)
Always dest first, per side
"""
s_params = user_settings['srce']
d_params = user_settings['dest']

nort_refs = References(nort.wires_by_dest)
west_refs = References(west.wires_by_dest)
sout_refs = References(sout.wires_by_dest)
east_refs = References(east.wires_by_dest)

get_refheaders(s_params, d_params)

"""
# Build the CAD file!
"""
FOUT = open(out_file + '.CAD', 'wt')

for head in References.ref_headers:
    print(head, file=FOUT)
print("", file=FOUT)
for side in [nort_refs, west_refs, sout_refs, east_refs]:
    for string in side.cad_strings:
        print(string, file=FOUT)

print(out_file+'.CAD file created')

"""
# SVG output 
A few defs to hold svg strings
"""

def html_head(title) -> str:
    """header strings for html file"""
    return (
        '<!DOCTYPE html>'
        '\r<html lang="en">'
        '\r\t<head>'
        f'''\r\t\t<title>{ title }</title>'''
        '\r\t\t<meta charset="utf-8">'
        '\r\t\t<meta name="viewport" content="width=device-width, user-scalable=no,'
        '\r\t\t\tminimum-scale=1.0, maximum-scale=1.0">'
        '\r\t\t<link rel="stylesheet" type="text/css" href="svg.css" media="screen">'
        '\r\t\t<style> </style>'
        '\r\t\t<!--<script src="inline_files/svg-pan-zoom.js"></script>-->'
        '\r\t</head>'
        '\r<body>'
        f'''\r<h2>{ title }</h2>'''
    )


def svg_container() -> str:
    """opening div for svg container in html file"""
    return '<div class="svgcont">'


def svg_container_close() -> str:
    """closing div for svg container in html file"""
    return '</div>'


def svg_head(scale, x_size, y_size, x_abs, y_abs) -> str:
    """svg header"""
    return (
        '<svg id="svg" xmlns="http://www.w3.org/2000/svg" version="1.1" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'ev="http://www.w3.org/2001/xml-events" '
        f'''width="{ rnd(x_size * scale) }" '''
        f'''height="{ rnd(y_size * scale) }" '''
        f'''viewBox="{ rnd(x_abs) } { rnd(y_abs) } { rnd(x_size) } { rnd(y_size) }">'''
    )


def js_close() -> str:
    """optional pan-zoom feature, but breaks for inset svgs"""
    return (
        '<script>'
        '(function() {'
        'window.graphic = svgPanZoom("#svg", {'
        'zoomEnabled: true,'
        'controlIconsEnabled: true,'
        'fit: true,'
        'center: true'
        ' });'
        '})();'
        '</script>'
        )


def html_close() -> str:
    return '</body></html>'


def svg_close() -> str:
    return '</svg>'


def to_grp(group, params) -> None:
    "wraps list in SVG group tags; opener applies styles"
    group.insert(0, params)
    group.append('</g>')


def svg_square(name, size) -> str:
    """SVG path element string in a bond-pad shape"""
    d = str(size/2)
    s = str(size)
    return '<rect id="'+name+'" x="-'+d+'" y="-'+d+'" height="'+s+'" width="'+s+'"/>'


def svg_cross(name, size) -> str:
    """SVG path element string in a cross shape"""
    s = str(size)
    return '<path id="'+name+'" d="M-'+s+' 0L'+s+' 0 M0 -'+s+'L0 '+s+'"/>'


def svg_use(name, x, y) -> str:
    """SVG use element string"""
    return '\t<use xlink:href="#'+name+'" x="' +x+ '" y="' +y+ '" />'


def svg_text(content, x='0', y='0', dx='0', dy='0') -> str:
    """SVG text element string"""
    return '\t<text dx="'+dx+'" dy="'+dy+'" x="'+x+'" y="'+y+'">'+content+'</text>'


def svg_tspan(font_size, content, dx='0', dy='0') -> str:
    """SVG tspan element string"""
    return '<tspan dx="'+dx+'" dy="'+dy+'" font-size="'+font_size+'">'+content+'</tspan>'


def svg_text_path(href, content) -> str:
    """SVG textPath element string"""
    return '<textPath xlink:href="#'+href+'">'+content+'</textPath>'


def svg_defs() -> str:
    """shapes for re-use in SVG"""
    return  (
        '<defs>'
        f'''\r\t{svg_square('chip', 0.08)}'''
        f'''\r\t{svg_square('pcb', 0.15)}'''
        f'''\r\t{svg_cross('cross', 0.2)}'''
        f'''\r\t{svg_cross('centre', 0.9)}'''
        '\r</defs>'
    )


def detail_corner(bg_size, viewbox, px, py) -> str:
    """Detail svg derived from the whole, group used when detail is inset within the whole"""
    return (
        f'''<svg class="pagebreak" viewBox="{viewbox}">'''
        f'''\r<!--<rect id="bgrnd" height="{bg_size[1]}" width="{bg_size[0]}" opacity="0.05"/>-->'''
        f'''\r{svg_use("everything", str(px), str(py))}'''
        '\r</svg>'
    )


def inset_detail_corner(bg_size, viewbox, scale, tx, ty, px, py) -> str:
    """Detail svg derived from the whole, group used when detail is inset within the whole"""
    return (
        f'''<g transform="translate({tx},{ty}) scale({scale})">'''
        f'''\r{detail_corner(bg_size, viewbox, px, py)}'''
        '\r</g>'
    )


colors = ['red', 'purple']#, 'orange', 'brown', 'green', 'blue']
wire_grps = []

pins = []
text_size = str(.15)
wirenums = []
wnum = 0
index = 0
dexes = ['2.6', '3', '3', '8.6', '2.5', '3', '2.2', '3'] # number alignment to wires

for side in [nort, west, sout, east]:
    for row in side.wires_by_dest:
        dx = dexes[index]
        w_grp = []
        for wire in row:
            wnum += 1
            pin = str(wire[0])
            src = str(wire[1]) + ' ' + str(-wire[2])
            dst = str(wire[3]) + ' ' + str(-wire[4])
            wId = 'w' + str(pin)
            path = '\t<path id="'+wId+'" d="M '+src+' L '+dst+' z"/>'
            w_grp.append(path)

            pin_txt = svg_text(svg_text_path(wId, svg_tspan(text_size, pin, dx='0')))
            pins.append(pin_txt)

            wnum_txt = svg_text(svg_text_path(wId, svg_tspan(text_size, str(wnum), dx=dx)))
            wirenums.append(wnum_txt)
        index += 1
        wire_grps.append(w_grp)

# ref points
ref_marks = []
ref_text = []
offsets = [
    ('-0.1', '0.15'),
    ('0', '-0.02'),
    ('-0.1', '-0.02'),
    ('-0.3', '-0.02'),
]
for i, side in enumerate([nort_refs, west_refs, sout_refs, east_refs]):
    label_offset = offsets[i]
    offx = label_offset[0]
    offy = label_offset[1]
    for ref_num, pts in side.dest_ref_system.items():
        for key, pt in pts.items():
            px = pt[0]
            py = str(-float(pt[1]))
            ref_marks.append(svg_use('cross', px, py))
            ref_label = ref_num + '.' + key
            ref_text.append(svg_text(ref_label, x=px, y=py, dx=offx, dy=offy))
    for system in side.srce_ref_systems:
        for ref_num, pts in system.items():
            for key, pt in pts.items():
                px = pt[0]
                py = str(-float(pt[1]))
                ref_marks.append(svg_use('cross', px, py))
                ref_label = ref_num + '.' + key
                ref_text.append(svg_text(ref_label, x=px, y=py, dx=offx, dy=offy))
#print(ref_text)
# wrap lists of shapes in styled 'g' elements, wire stroke, font-size
MAG = 20 # up to 60 for readable text on A3!
stroke_width = str(0.05)
ref_text_size = str(0.2)
ref_stroke_width = str(0.02)
ref_id = 'ref' + str(1)
for i, grp in enumerate(wire_grps):
    col = colors[i % len(colors)]
    to_grp(grp, params='<g stroke-opacity="0.3" stroke="'+col+'" stroke-width="'+stroke_width+'" id="'+ref_id+'">')

to_grp(pins, params='<g id="pins" fill="#a42">')
to_grp(wirenums, '<g id="reftext" font-size="'+ref_text_size+'" fill="#089">') #  text-anchor="end"
to_grp(ref_text, '<g id="reftext" font-size="'+ref_text_size+'" fill="#089">') #  text-anchor="end"
to_grp(ref_marks, '<g id="refmarks" stroke="#089" stroke-width="'+ref_stroke_width+'">')


# viewBox settings
DEST_X_RANGE = min_max(list_n(nlines, 3))
DEST_Y_RANGE = min_max(list_n(nlines, 4))
X_MIN = DEST_X_RANGE[0]
X_MAX = DEST_X_RANGE[1]
Y_MIN = DEST_Y_RANGE[0]
Y_MAX = DEST_Y_RANGE[1]
BORDER = 0.2

X_SIZE = (X_MAX - X_MIN + 2 * BORDER)/1
Y_SIZE = (Y_MAX - Y_MIN + 2 * BORDER)/1
X_ABS = X_MIN - BORDER
Y_ABS = -Y_MAX - BORDER # due to -y scaling conversion


FOUT = open(out_file + '.html', 'wt')
print(html_head(out_file), file=FOUT)
print(svg_container(), file=FOUT)
print(svg_head(scale=MAG, x_size=X_SIZE, y_size=Y_SIZE, x_abs=X_ABS, y_abs=Y_ABS), file=FOUT)
print(svg_defs(), file=FOUT)

print('<g id="everything">', file=FOUT) # detail script
# print('<g class="svg-pan-zoom_viewport">', file=FOUT) # zoom script  
for grp in wire_grps:
    for val in grp:
        print(val, file=FOUT)

for val in pins:
    print(val, file=FOUT)

for val in wirenums:
    print(val, file=FOUT)

for val in ref_marks:
    print(val, file=FOUT)

for val in ref_text:
    print(val, file=FOUT)

print('</g>', file=FOUT) # zoom or detail script


detscale = 0.1 # defines scope of detail but changes scale
bg_size = (X_SIZE*detscale, Y_SIZE*detscale)
viewbox = "0 0 " + str(bg_size[0]) + " " + str(bg_size[1])

# Inset version inserts corner detail into the main diagram, results may vary
# comp_scale = detscale * 8
# die_minx, die_maxx = min_max(list_n(nlines, 1))
# die_miny, die_maxy = min_max(list_n(nlines, 2))
# tr_diffx = die_minx + X_SIZE/2
# tr_diffy = die_maxy - Y_SIZE/2
# tl = inset_detail_corner(bg_size, viewbox, comp_scale, tx=die_minx, ty=-die_maxy, px=-X_ABS, py=-Y_ABS)
# tr = inset_detail_corner(bg_size, viewbox, comp_scale, tx=tr_diffx, ty=-die_maxy, px=pict_x, py=-Y_ABS)
# bl = inset_detail_corner(bg_size, viewbox, comp_scale, tx=die_minx, ty=-tr_diffy, px=-X_ABS, py=pict_y)
# br = inset_detail_corner(bg_size, viewbox, comp_scale, tx=tr_diffx, ty=-tr_diffy, px=pict_x, py=pict_y)

# Corner details separated from main diagram
pict_x = -X_ABS-X_SIZE * 0.9
pict_y = -Y_ABS-Y_SIZE * 0.9
tl = detail_corner(bg_size, viewbox, px=-X_ABS, py=-Y_ABS)
tr = detail_corner(bg_size, viewbox, px=pict_x, py=-Y_ABS)
bl = detail_corner(bg_size, viewbox, px=-X_ABS, py=pict_y)
br = detail_corner(bg_size, viewbox, px=pict_x, py=pict_y)

print(svg_close(), file=FOUT)
print(svg_container_close(), file=FOUT)
print('<h2>Top Left</h2>', file=FOUT)
print(tl, file=FOUT)
print('<h2>Top Right</h2>', file=FOUT)
print(tr, file=FOUT)
print('<h2>Bottom Left</h2>', file=FOUT)
print(bl, file=FOUT)
print('<h2>Bottom Right</h2>', file=FOUT)
print(br, file=FOUT)

print(html_close(), file=FOUT)
FOUT.close()
print(out_file+'.html file created')







# img = ImageFile(FOUT.name)
# img


# def merge_by_diff(lst, diffs, tol):
#     for i in range(len(diffs)):
#         count = []
#         for j in range(len(diffs[i])):
#             if diffs[i][j] < tol:
#                 lst[i][j] += lst[i][j + 1]
#                 count.append(j+1)
#         count.sort(reverse=True)
#         for k in range(len(count)):
#             lst[i].pop(count[k])


# def chk_list(w, strg):
#     s = 0
#     a = []
#     for i in range(len(w)):
#         a.append(len(w[i]))
#         s += len(w[i])
#     print(strg, s, a)


# def chk_nested(w, strg):
#     for i in range(len(w)):
#         chk_list(w[i], strg + str(i) + ':')

# def dbg(thing, num):
#     flout = open('dbg'+str(num)+'.py', 'wt')
#     print(thing, file=flout)
#     flout.close()


# def create_rank_lists(ranks):
#     arr = []
#     for i in range(len(ranks)):
#         arr.append(list())
#         for j in range(len(ranks[i])):
#             arr[i].append(list())
#     return arr



# def dbg_num_wires(wirelist, string):
#     total = 0
#     for i in range(len(wirelist)):
#         for j in range(len(wirelist[i])):
#             total += len(wirelist[i][j])
#     print(string, total)