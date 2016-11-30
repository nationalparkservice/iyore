#!/bin/bash

ME="scripts/test.sh"

git update-index --assume-unchanged $ME
git rm --cached $ME
git commit -m "Temporary commit to untrack $ME"
git checkout master
git checkout gh-pages
git reset --mixed HEAD^
#git update-index --no-assume-unchanged $ME
