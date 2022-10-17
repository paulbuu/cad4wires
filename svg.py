"""
MIT License

Copyright 2022 UK Research and Innovation
Author: Paul Booker (paul.booker@stfc.ac.uk)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


This script converts a Hesse BJ820 wire-bonder CAD file into:
1/ detailed image
2/ area image
Limitations!
Assumes 2 substrate ref systems.
N.B. Area image buggy with rotated substrates!
"""
import re
import math
import sys


def dbg(thing, num):
    fout = open('dbg'+str(num)+'.py', 'wt')
    print(thing, file=fout)
    fout.close()


def rnd(flot):
    return round(flot, 3)


def min_max(num_list):
    "ok"
    result = sorted(num_list)
    return result[0], result[-1]


def mid_value(num_list):
    order = sorted(num_list)
    mid = rnd((order[0] + order[-1]) / 2)
    return mid


def square(name, size):
    d = str(size/2)
    s = str(size)
    return '<rect id="'+name+'" x="-'+d+'" y="-'+d+'" height="'+s+'" width="'+s+'"/>'


def cross(name, size):
    s = str(size)
    return '<path id="'+name+'" d="M-'+s+' 0L'+s+' 0 M0 -'+s+'L0 '+s+'"/>'


def use(name, x, y):
    return '\t<use xlink:href="#'+name+'" x="' +x+ '" y="' +y+ '" />'


def text(offx, offy, x, y, txt):
    return '\t<text dx="'+offx+'" dy="'+offy+'" x="'+x+'" y="'+y+'">'+txt+'</text>'


def svg_defs():
    "shapes for re-use in SVG"
    return  f'''<defs>
    { square('chip', 0.08) }
    { square('pcb', 0.15) } 
    { cross('cross', 0.2) }
    { cross('centre', 0.9) }
</defs>'''


def to_grp(group, opener):
    "wraps list in SVG group tags; opener applies styles"
    group.insert(0, opener)
    group.append('</g>')


def html_head(scale, x_size, y_size, x_abs, y_abs):
    "header for html file"
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<title>wirecad 2D layout</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0">

<link rel="stylesheet" type="text/css" href="svg.css" media="screen">
<style>

</style>
</head>
<body>
<div class="svgcont">
    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" 
    xmlns:xlink="http://www.w3.org/1999/xlink"
    width="{ rnd(x_size * scale) }"
    height="{ rnd(y_size * scale) }"
    viewBox="{ rnd(x_abs) } { rnd(y_abs) } { rnd(x_size) } { rnd(y_size) }">
'''

# If using this file on its own, comment these 2 lines
# title = sys.argv[1]
# out_file = [x.strip() for x in [x.strip() for x in title.split('.')][0].split('\\')][-1]

# If using this file on its own, uncomment these 4 lines
# path = 'path/to/my/file/'
# name = 'my-file'

path = ''
name = 'C100mm'
title = path + name + '.CAD'
out_file = name

MAG = input("Change magnification or Enter (60): ")
if not MAG:
    MAG = 60
else:
    MAG = int(MAG)
print("MAG", MAG)
fin = open(title, 'rt')
lines = fin.readlines()
fin.close()

print(len(lines), 'lines read')

refpnt = re.compile('refpnt ')
bondpnt = re.compile('bondpnt ')

refPts = []
crosses = []
wNums = []
srceR = []
srceX = []
srceY = []
destR = []
destX = []
destY = []

# read CAD file into lists per column of data
for line in lines:

    if refpnt.match(line):

        line = [x.strip() for x in line.split(',')]
        line[0] = [x.strip() for x in line[0].split(' ')][-1]
        refPts.append([int(line[0]), int(line[1]), float(line[2]), float(line[3])])

    elif bondpnt.match(line):

        line = [x.strip() for x in line.split(',')]
        line[0] = int([x.strip() for x in line[0].split(' ')][-1])
        line[2] = int(line[2])
        line[3] = float(line[3])
        line[4] = float(line[4])

        if line[1] == '1':
            wNums.append(line[0])
            srceR.append(line[2])
            srceX.append(line[3])
            srceY.append(line[4])

        if line[1] == '2':
            destR.append(line[2])
            destX.append(line[3])
            destY.append(line[4])

# read last bondpnt
print(line[0], 'wires found')

# test list lengths
length = len(wNums)
if any(len(chk) != length for chk in [srceR, srceX, srceY, destR, destX, destY]):
    print('data missing in list')

refMin, refMax = min_max(srceR)

colors = ['red', 'purple', 'orange', 'brown', 'green', 'blue']
wireNums = []
refText = []
refMark = []
chipPads = []
pcbPads = []
wireGrps = []
dstArea = []
srcArea = []

i = 0
while(i <= refMax - refMin):
    wireGrps.append([])
    i += 1

# refmarks and labels
for val in refPts:
    if val[1] == 1:
        rpt = 'a'
    if val[1] == 2:
        rpt = 'b'
    ref = str(val[0]) + rpt
    px = str(val[2])
    py = str(-val[3])
    dx = str(-0.06)
    refMark.append(use('cross', px, py))
    refText.append(text(dx, dx, px, py, ref)) # dx dy varies with fontsize

    # refareas
    if val[1] == 1:
        ar = [str(val[0]), px, py]#'<path id=ar"'+ val[0]+'" d="M'+val[2]+' '+val[3]+'H'
    if val[1] == 2:
        ref_path = '\t<path id="ar'+ ar[0]+'" d="M'+ar[1]+' '+ar[2]+'V'+py+'H'+px+'V'+ar[2]+'z"/>'

        if val[0] < refMin:
            dstArea.append(ref_path)
        else:
            srcArea.append(ref_path)

srce_centre = {'x': mid_value(srceX), 'y': mid_value(srceY)}
refMark.append(use('centre', str(srce_centre['x']), str(-srce_centre['y'] )))

# wireLists length 12 refers 0_11 converts 3_14
ref = refMin
for i in range(len(srceX)):

    if srceR[i] != ref:
        ref += 1
    if srceR[i] == ref:
        grp = wireGrps[ref - 3]
        src = str(srceX[i]) + ' ' + str(-srceY[i])
        dst = str(destX[i]) + ' ' + str(-destY[i])
        wId = 'w' + str( wNums[ i ] ) # str( i + 1 )

        grp.append( '\t<path id="'+wId+'" d="M'+src+'L'+dst+'z"/>' )

# wire-numbers and rects affixed to wires; adjust length to slide numbers along wires
for i in range(len(wNums)):
    length = math.sqrt((destX[i] - srceX[i])**2 + (destY[i] - srceY[i])**2)

    if srceX[i] < -500:
    #if(destX[i] < -69 or destY[i] < 0):
        length -= 1 # flips numbers upside-down, varies with font-size
    else:
        length -= 0.5
    length = rnd(length)

    #print(srceX[i], length)
    
    n = str(wNums[i])
    textpath = '<textPath xlink:href="#w'+n+'">'+n+'</textPath>'

    wireNums.append(text(str(length), '0', '0', '0', textpath))
    chipPads.append(use('chip', str(srceX[i]), str(-srceY[i])))
    pcbPads.append(use('pcb', str(destX[i]), str(-destY[i])))

#MAG = 100 # up to 60 for readable text on A3 print!
# wrap lists of shapes in styled g elements Wire stroke, font-size, x1000!
stroke_width = str(1 / MAG)
text_size = str(13 / MAG)
#print(wireGrps, file=open('wireGrps.svg', 'wt')) # debug grps
for wgrp in range(len(wireGrps)):
    col = colors[wgrp  % len(colors)]
    rId = 'ref' + str(wgrp + 2)
    to_grp(wireGrps[wgrp], '<g stroke="'+col+'" stroke-width="'+stroke_width+'" id="'+rId+'">')

to_grp(wireNums, '<g id="nums" font-size="'+text_size+'">') #  text-anchor="end" x1000?
to_grp(chipPads, '<g id="chipPads" fill="#ddd">')
to_grp(pcbPads, '<g id="pcbPads"  fill="#fda">')
to_grp(refText, '<g id="refText" font-size="'+text_size+'" fill="#089">') #  text-anchor="end"
to_grp(refMark, '<g id="crosses" stroke="#089" stroke-width="'+stroke_width+'">')
to_grp(dstArea, '<g id="dstAreas" fill="#086" fill-opacity="0.4">')
to_grp(srcArea, '<g id="srcAreas" fill="#fff" stroke="#fff" stroke-width="'+stroke_width+'" >')

# viewBox settings
DEST_X_RANGE = min_max(destX)
DEST_Y_RANGE = min_max(destY)
X_MIN = DEST_X_RANGE[0]
X_MAX = DEST_X_RANGE[1]
Y_MIN = DEST_Y_RANGE[0]
Y_MAX = DEST_Y_RANGE[1]
BORDER = 0.2

X_SIZE = X_MAX - X_MIN + 2 * BORDER
Y_SIZE = Y_MAX - Y_MIN + 2 * BORDER
X_ABS = X_MIN - BORDER
Y_ABS = -Y_MAX - BORDER # due to -y scaling conversion

# print("X_SIZE", X_SIZE)
# print("Y_SIZE", X_SIZE)

bg_X = str(X_SIZE - BORDER)
bg_Y = str(Y_SIZE - BORDER)
bgPos_X = str(X_MIN - BORDER/2)
bgPos_Y = str(-Y_MAX - BORDER/2)
bg_dest = '<rect id="destarea" x="'+ bgPos_X + '" y="'+ bgPos_Y + '" height="'+ bg_Y + '" width="'+ bg_X +'" fill="#d8e8ff" />'

mm_X = min_max(srceX)
mm_Y = min_max(srceY)
X_pitch = srceX[1] - srceX[0]

mm_W = str(mm_X[1] - mm_X[0] + 2 * X_pitch)
mm_H = str(mm_Y[1] - mm_Y[0] + 2 * X_pitch)
mmPosX = str(mm_X[0] - X_pitch)
mmPosY = str(-mm_Y[1] - X_pitch)
bg_srce = '<rect id="srcearea" x="'+ mmPosX + '" y="'+ mmPosY + '" height="'+ mm_H + '" width="'+ mm_W +'" fill="#def" />'

FOUT = open(out_file + '.html', 'wt')

print(html_head(MAG, X_SIZE, Y_SIZE, X_ABS, Y_ABS), file=FOUT)
print(svg_defs(), file=FOUT)

'''If a background colour is desired...'''
# print(bg_dest, file=FOUT)
print(bg_srce, file=FOUT)

print_lists = [chipPads, pcbPads, wireNums, refText, refMark]
print_lists.extend(wireGrps)

for lst in print_lists:
    for val in lst:
        print(val, file=FOUT)

print('</svg></div></body></html>', file=FOUT)
FOUT.close()
print('HTML file created')
# change font size by replacing the group element style
MAG = input("Change magnification for inset or Enter (10): ")
if not MAG:
    MAG = 10
else:
    MAG = int(MAG)
print("MAG", MAG)

MAG = 10
stroke_width = str(1 / MAG)
text_size = str(13 / MAG)
refText[0] = '<g id="reftext" font-size="'+text_size+'" fill="#089" text-anchor="end">' #  text-anchor="end"
refMark[0] = '<g id="crosses" stroke="#000" stroke-width="'+stroke_width+'">'


INSET_FOUT = open(out_file + '_inset.html', 'wt')

print(html_head(MAG, X_SIZE, Y_SIZE, X_ABS, Y_ABS), file=INSET_FOUT)
print(svg_defs(), file=INSET_FOUT)

print_lists = [dstArea, srcArea, refMark, refText]
for lst in print_lists:
    for val in lst:
        print(val, file=INSET_FOUT)
# for val in dstArea:
#     print(val, file=INSET_FOUT)
# for val in srcArea:
#     print(val, file=INSET_FOUT)
# for val in refMark:
#     print(val, file=INSET_FOUT)
# for val in refText:
#     print(val, file=INSET_FOUT)

print('</svg></div></body></html>', file=INSET_FOUT)

INSET_FOUT.close()
print('Insets file created')
