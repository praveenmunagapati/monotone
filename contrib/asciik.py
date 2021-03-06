#!/usr/bin/python

# BUGS:
#
# 1)
#
# | | | | | | |\ \ \ \ 
# | | | | | | o | | | |    145c71fb56cff358dd711773586ae6b5219b0cfc
# | | | | | | |\ \ \ \ \ 
#
# should be
# 
# | | | | | | |\ \ \ \ 
# | | | | | | o \ \ \ \    145c71fb56cff358dd711773586ae6b5219b0cfc
# | | | | | | |\ \ \ \ \
#
# need some sort "inertia", if we moved sideways before and are moving
# sideways now...
#
# 2)
#
# It actually is possible to remove a ghost on the same line as a long
# rightwards edge -- and it even looks better than not doing it, at least in
# some cases.  Consider:
#
# Current:
# 
# | | | o | | | | |    0f07da5974be8bf91495a34093efc635dcf1f01c
# | | | |\ \ \ \ \ \ 
# | | | | .-o | | | |    20037e09def77cc217679bf2f72baf5fa0415649
# | | | |/|   | | | |
# | | | o---. | | | |    de74b6e2bd612ba40f1afc3eba3f9a3d8f419135
# | | | | |  \| | | |
# | | | o |   | | | |    3fd16665caab9d942e6c5254b477587ff7d3722d
# | | | | |  / / / / 
# | | | o | | | | |    38f3561cc4bf294b99436f98cd97fc707b422bfa
# | | | | | | | | |
# | | | | .-o | | |    59017bc836986a59fd1ac6fba4f78fe1045c67e9
# | | | |/| | | | |
# | | | o | | | | |    97e8f96bb34774003de428292edbdd562ca6d867
# | | | | | | | | |
#
# Desired:
# 
# | | | o | | | | |    0f07da5974be8bf91495a34093efc635dcf1f01c
# | | | |\ \ \ \ \ \ 
# | | | | .-o | | | |    20037e09def77cc217679bf2f72baf5fa0415649
# | | | |/|   | | | |
# | | | o-.   | | | |    de74b6e2bd612ba40f1afc3eba3f9a3d8f419135
# | | | | |\ / / / /
# | | | o | | | | |    3fd16665caab9d942e6c5254b477587ff7d3722d
# | | | | | | | | | 
# | | | o | | | | |    38f3561cc4bf294b99436f98cd97fc707b422bfa
# | | | | | | | | |
# | | | | .-o | | |    59017bc836986a59fd1ac6fba4f78fe1045c67e9
# | | | |/| | | | |
# | | | o | | | | |    97e8f96bb34774003de428292edbdd562ca6d867
# | | | | | | | | |
#
# Possibly the no-shift-while-drawing-long-edges code could even be removed,
# deferring to the no-edge-crossings code.




# How this works:
#   This is completely iterative; we have no lookahead whatsoever.  We output
#     each line before even looking at the next.  (This means the layout is
#     much less clever than it could be, because there is no global
#     optimization; but it also means we can calculate these things in zero
#     time, incrementally while running log.)
#
#   Output comes in two-line chunks -- a "line", which contains exactly one
#   node, and then an "interline", which contains edges that will link us to
#   the next line.
#
#   A design goal of the system is that you can always trivially increase the
#   space between two "lines", by adding another "| | | |"-type interline
#   after the real interline.  This allows us to put arbitrarily long
#   annotations in the space to the right of the graph, for each revision --
#   we can just stretch the graph portion to give us more space.
#   
# Loop:
#   We start knowing, for each logical column, what thing has to go there
#     (because this was determined last time)
#   We use this to first determine what thing has to go in each column next
#     time (though we will not draw them yet).
#   This is somewhat tricky, because we do want to squish things towards the
#   left when possible.  However, we have very limited drawing options -- we
#   can slide several things 1 space to the left or right and do no other long
#   sideways edges; or, we can draw 1 or 2 long sideways edges, but then
#   everything else must go straight.  So, we try a few different layouts.
#   The options are, remove a "ghost" if one exists, don't remove a ghost, and
#   insert a ghost.  (A "ghost" is a blank space left by a line that has
#   terminated or merged back into another line, but we haven't shifted things
#   over sideways yet to fill in the space.)
#
#   Having found a layout that works, we draw lines connecting things!  Yay.

import sys
from sets import Set as set

# returns a dict {node: (parents,)}
def parsegraph(f):
    g = {}
    for line in f:
        pieces = line.strip().split()
        g[pieces[0]] = tuple(pieces[1:])
    return g

# returns a list from bottom to top
def parseorder(f):
    order = []
    for line in f:
        order.append(line.strip())
    order.reverse()
    return order

# takes two files:
#   one is output of 'automate graph'
#   other is output of 'automate select i: | automate toposort -@-'
def main(name, args):
    assert len(args) == 2
    graph = parsegraph(open(args[0]))
    order = parseorder(open(args[1]))

    row = []
    for rev in order:
        row = print_row(row, rev, graph[rev])
    
def print_row(curr_row, curr_rev, parents):
    if curr_rev not in curr_row:
        curr_row.append(curr_rev)
    curr_loc = curr_row.index(curr_rev)

    new_revs = []
    for p in parents:
        if p not in curr_row:
            new_revs.append(p)
    next_row = list(curr_row)
    next_row[curr_loc:curr_loc + 1] = new_revs
    
    # now next_row contains exactly the revisions it needs to, except that no
    # ghost handling has been done.

    no_ghost = without_a_ghost(next_row)
    if try_draw(curr_row, no_ghost, curr_loc, parents):
        return no_ghost
    if try_draw(curr_row, next_row, curr_loc, parents):
        return next_row
    if not new_revs: # this line has disappeared
        extra_ghost = with_a_ghost_added(next_row, curr_loc)
        if try_draw(curr_row, extra_ghost, curr_loc, parents):
            return extra_ghost
    assert False

def without_a_ghost(next_row):
    wo = list(next_row)
    if None in next_row:
        wo.pop(next_row.index(None))
    return wo

def with_a_ghost_added(next_row, loc):
    w = list(next_row)
    w.insert(loc, None)
    return w

# coordinates of the columns where we draw sideways-moving links
def links_cross(links):
    crosses = set()
    for i, j in links:
        if i != j:
            for coord in xrange(2 * min(i, j) + 1, 2 * max(i, j)):
                crosses.add(coord)
    return crosses

def try_draw(curr_row, next_row, curr_loc, parents):
    curr_items = len(curr_row)
    next_items = len(next_row)
    curr_ghosts = []
    for i in xrange(curr_items):
        if curr_row[i] is None:
            curr_ghosts.append(i)
    preservation_links = []
    have_shift = False
    for rev in curr_row:
        if rev is not None and rev in next_row:
            i = curr_row.index(rev)
            j = next_row.index(rev)
            if i != j:
                have_shift = True
            if abs(i - j) > 1:
                return False
            preservation_links.append((i, j))
    parent_links = []
    for p in parents:
        i = curr_loc
        j = next_row.index(p)
        if abs(i - j) > 1 and have_shift:
            return False
        parent_links.append((i, j))

    preservation_crosses = links_cross(preservation_links)
    parent_crosses = links_cross(parent_links)
    if preservation_crosses.intersection(parent_crosses):
        return False

    links = preservation_links + parent_links
    draw(curr_items, next_items, curr_loc, links, curr_ghosts, curr_row[curr_loc])
    return True

def draw(curr_items, next_items, curr_loc, links, curr_ghosts, annotation):
    line = [" "] * (curr_items * 2 - 1)
    interline = [" "] * (max(curr_items, next_items) * 2 - 1)

    # first draw the flow-through bars in the line
    for i in xrange(curr_items):
        line[i * 2] = "|"
    # but then erase it for ghosts
    for i in curr_ghosts:
        line[i * 2] = " "
    # then the links
    dots = set()
    for i, j in links:
        if i == j:
            interline[2 * i] = "|"
        else:
            if j < i:
                # | .---o
                # |/| | |
                # 0 1 2 3
                # j     i
                # 0123456
                #    s  e
                start = 2*j + 3
                end = 2*i
                dot = start - 1
                interline[dot - 1] = "/"
            else: # i < j
                # o---.
                # | | |\|
                # 0 1 2 3
                # i     j
                # 0123456
                #  s  e
                start = 2*i + 1
                end = 2*j - 2
                dot = end
                interline[dot + 1] = "\\"
            if end - start >= 1:
                dots.add(dot)
            line[start:end] = "-" * (end - start)
    # add any dots (must do this in a second pass, so that if there are 
    # cases like:
    #   | .-----.-o
    #   |/| | |/|
    # where we want to make sure the second dot overwrites the first --.
    for dot in dots:
        line[dot] = "."
    # and add the main attraction (may overwrite a ".").
    line[curr_loc * 2] = "o"

    print "".join(line) + "    " + annotation
    print "".join(interline)

if __name__ == "__main__":
    main(sys.argv[0], sys.argv[1:])
