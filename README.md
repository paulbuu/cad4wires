# cad4wires
Sort a given pin-list from die-to-pcb xy data into rows per side. Output format for Hesse BJ820 CAD csv file.

Currently accepts csv data in 6 columns:
Pin_no | Die_X | Die_Y | not_used | pcb_X | pcb_Y

## cad.py
Re-orders te pin list to a suitable order for wire-bonding, by side, anticlockwise from the top.

## svg.py
Used for debugging the output of cad.py, a csv file with .CAD suffix.
Can also show layouts from existing programs exported as CAD files fro Hesse 820 or Hesse 715 wire-bonding machines.
