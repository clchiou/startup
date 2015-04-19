#!/bin/bash

git ls-tree -r --name-only HEAD \
  | grep -v '^startup\|^\.' \
  | awk '{print "include " $0}' \
  > MANIFEST.in
