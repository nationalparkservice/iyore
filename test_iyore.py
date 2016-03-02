from __future__ import print_function, division, unicode_literals, absolute_import
from builtins import (bytes, str, int, dict, object, range, map, filter, zip, round, pow, open)

import os
import shutil
import re
import random
import math

import iyore

import pytest

def touch(path):
    open(path, 'a').close()

base = "TestTree"
structureFile = ".structure.txt"

datafiles = iyore.Endpoint([r"static one", r"dir_(?P<char>[A-Z])", r"(?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt"], base)
siteDocs = iyore.Endpoint([r"static two", r"(?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+)"], base)
basic = iyore.Endpoint([r"static three", r"file_(?P<char>[A-Z])\.txt"], base)

@pytest.fixture(scope= "module")
def makeTestTree(request):
    if os.path.exists(base):
        shutil.rmtree(base)

    os.mkdir(base)

    structure = """
static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+)
static three
    basic: file_(?P<char>[A-Z])\.txt
"""

    with open(os.path.join(base, structureFile), "w") as f:
        f.write(structure)

    os.mkdir(os.path.join(base, "static one"))
    for char in "ABCDE":
        os.mkdir(os.path.join(base, "static one", "dir_"+char))
        for name in ["MURI", "WOCR", "UPST", "THRI", "TETH"]:
            for num in range(1,5):
                touch(os.path.join(base, "static one", "dir_"+char, "{}_{}_{}.txt".format(name, num, char)))
            
            touch(os.path.join(base, "static one", "dir_"+char, "{}_0_INVALID.txt".format(name, num)))
        
    os.mkdir(os.path.join(base, "static one", "dir_X"))
    touch(os.path.join(base, "static one", "dir_X", "bleh.txt"))
    os.mkdir(os.path.join(base, "static one", "dir_Z"))
    os.mkdir(os.path.join(base, "static one", "party planning documents"))


    os.mkdir(os.path.join(base, "static two"))
    for name in ["MURI", "WOCR", "UPST", "THRI", "TETH"]:
        touch(os.path.join(base, "static two", "{} photo.png".format(name)))
        touch(os.path.join(base, "static two", "{} description.txt".format(name)))
        touch(os.path.join(base, "static two", "{} note {}.txt".format(name, ' '.join(["bad", "data", "error", "timestamp"][random.randint(0, 3)] for i in range(random.randint(2, 5))) )))

    os.mkdir(os.path.join(base, "static three"))
    for char in "ABC":
        touch(os.path.join(base, "static three", "file_{}.txt".format(char)))
    
    touch(os.path.join(base, "static three", "file_1.txt".format(char)))
    touch(os.path.join(base, "static three", "file_AB.txt".format(char)))
    touch(os.path.join(base, "static three", "file_D.csv".format(char)))

    def teardown():
        if os.path.exists(base):
            shutil.rmtree(base)
    
    # Allow this test file to be run interactively for easy REPL-ing with the test tree and endpoints already set up
    try:
        request.addfinalizer(teardown)
    except AttributeError:
        print("Created test tree in '{}'".format(base))

class TestBasics:
    def test_no_parameters_gives_all_matching_files(self, makeTestTree):
        chars = "ABC"
        paths = {os.path.join(base, "static three", "file_{}.txt".format(char)) for char in chars}

        entries = list(basic())
        assert len(entries) == len(chars)
        for entry in entries:
            assert entry.path in paths
            paths.remove(entry.path)
        assert len(paths) == 0

    def test_attribute_access_mirrors_endpoint_fields(self, makeTestTree):
        chars = set("ABC")

        for entry in basic():
            assert entry.fields["char"] == entry.char
            assert entry.char in chars
            chars.remove(entry.char)
            with pytest.raises(AttributeError):
                entry.asdf

        assert len(chars) == 0

    def test_endpoint_creation(self):
        parts = ["static", "with some spaces", r"regex_no_groups \w+", r"regex_no_named_groups (?:[A-z0-9]*)", r"(?P<duplicate_name>.*)", r"(?P<group_one>\w+)\s+(?P<group_two>\w{3})", r"(?P<duplicate_name>.*)"]
        # is_literal = [True,    True,                 False,                         False,                              False,                        False,                                      False]
        base = "base"

        ep = iyore.Endpoint(parts, base)
        assert ep.fields == {"duplicate_name", "group_one", "group_two"}

    def test_invalid_regex_in_endpoint(self):
        path = [r"static", r"more static", r"working regex: (?P<field>\w+ \d{4})", r"invalid regex (+)"]
        with pytest.raises(ValueError):
            ep = iyore.Endpoint(path, "base")

class TestMatchingAndQuerying:

    @pytest.fixture(scope= "module", params= ["manual", "parsed"])
    def datafiles_endpoint(self, request, makeTestTree):
        if request.param == "manual":
            return datafiles
        else:
            return iyore.Dataset(os.path.join(base, structureFile)).datafiles


    def test_datafiles_all(self, makeTestTree, datafiles_endpoint):

        allFiles = {u'TestTree/static one/dir_A/MURI_1_A.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_A/MURI_3_A.txt', u'TestTree/static one/dir_A/MURI_4_A.txt', u'TestTree/static one/dir_A/TETH_1_A.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_A/TETH_3_A.txt', u'TestTree/static one/dir_A/TETH_4_A.txt', u'TestTree/static one/dir_A/THRI_1_A.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_A/THRI_3_A.txt', u'TestTree/static one/dir_A/THRI_4_A.txt', u'TestTree/static one/dir_A/UPST_1_A.txt', u'TestTree/static one/dir_A/UPST_2_A.txt', u'TestTree/static one/dir_A/UPST_3_A.txt', u'TestTree/static one/dir_A/UPST_4_A.txt', u'TestTree/static one/dir_A/WOCR_1_A.txt', u'TestTree/static one/dir_A/WOCR_2_A.txt', u'TestTree/static one/dir_A/WOCR_3_A.txt', u'TestTree/static one/dir_A/WOCR_4_A.txt', u'TestTree/static one/dir_B/MURI_1_B.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_B/MURI_3_B.txt', u'TestTree/static one/dir_B/MURI_4_B.txt', u'TestTree/static one/dir_B/TETH_1_B.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_B/TETH_3_B.txt', u'TestTree/static one/dir_B/TETH_4_B.txt', u'TestTree/static one/dir_B/THRI_1_B.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_B/THRI_3_B.txt', u'TestTree/static one/dir_B/THRI_4_B.txt', u'TestTree/static one/dir_B/UPST_1_B.txt', u'TestTree/static one/dir_B/UPST_2_B.txt', u'TestTree/static one/dir_B/UPST_3_B.txt', u'TestTree/static one/dir_B/UPST_4_B.txt', u'TestTree/static one/dir_B/WOCR_1_B.txt', u'TestTree/static one/dir_B/WOCR_2_B.txt', u'TestTree/static one/dir_B/WOCR_3_B.txt', u'TestTree/static one/dir_B/WOCR_4_B.txt', u'TestTree/static one/dir_C/MURI_1_C.txt', u'TestTree/static one/dir_C/MURI_2_C.txt', u'TestTree/static one/dir_C/MURI_3_C.txt', u'TestTree/static one/dir_C/MURI_4_C.txt', u'TestTree/static one/dir_C/TETH_1_C.txt', u'TestTree/static one/dir_C/TETH_2_C.txt', u'TestTree/static one/dir_C/TETH_3_C.txt', u'TestTree/static one/dir_C/TETH_4_C.txt', u'TestTree/static one/dir_C/THRI_1_C.txt', u'TestTree/static one/dir_C/THRI_2_C.txt', u'TestTree/static one/dir_C/THRI_3_C.txt', u'TestTree/static one/dir_C/THRI_4_C.txt', u'TestTree/static one/dir_C/UPST_1_C.txt', u'TestTree/static one/dir_C/UPST_2_C.txt', u'TestTree/static one/dir_C/UPST_3_C.txt', u'TestTree/static one/dir_C/UPST_4_C.txt', u'TestTree/static one/dir_C/WOCR_1_C.txt', u'TestTree/static one/dir_C/WOCR_2_C.txt', u'TestTree/static one/dir_C/WOCR_3_C.txt', u'TestTree/static one/dir_C/WOCR_4_C.txt', u'TestTree/static one/dir_D/MURI_1_D.txt', u'TestTree/static one/dir_D/MURI_2_D.txt', u'TestTree/static one/dir_D/MURI_3_D.txt', u'TestTree/static one/dir_D/MURI_4_D.txt', u'TestTree/static one/dir_D/TETH_1_D.txt', u'TestTree/static one/dir_D/TETH_2_D.txt', u'TestTree/static one/dir_D/TETH_3_D.txt', u'TestTree/static one/dir_D/TETH_4_D.txt', u'TestTree/static one/dir_D/THRI_1_D.txt', u'TestTree/static one/dir_D/THRI_2_D.txt', u'TestTree/static one/dir_D/THRI_3_D.txt', u'TestTree/static one/dir_D/THRI_4_D.txt', u'TestTree/static one/dir_D/UPST_1_D.txt', u'TestTree/static one/dir_D/UPST_2_D.txt', u'TestTree/static one/dir_D/UPST_3_D.txt', u'TestTree/static one/dir_D/UPST_4_D.txt', u'TestTree/static one/dir_D/WOCR_1_D.txt', u'TestTree/static one/dir_D/WOCR_2_D.txt', u'TestTree/static one/dir_D/WOCR_3_D.txt', u'TestTree/static one/dir_D/WOCR_4_D.txt', u'TestTree/static one/dir_E/MURI_1_E.txt', u'TestTree/static one/dir_E/MURI_2_E.txt', u'TestTree/static one/dir_E/MURI_3_E.txt', u'TestTree/static one/dir_E/MURI_4_E.txt', u'TestTree/static one/dir_E/TETH_1_E.txt', u'TestTree/static one/dir_E/TETH_2_E.txt', u'TestTree/static one/dir_E/TETH_3_E.txt', u'TestTree/static one/dir_E/TETH_4_E.txt', u'TestTree/static one/dir_E/THRI_1_E.txt', u'TestTree/static one/dir_E/THRI_2_E.txt', u'TestTree/static one/dir_E/THRI_3_E.txt', u'TestTree/static one/dir_E/THRI_4_E.txt', u'TestTree/static one/dir_E/UPST_1_E.txt', u'TestTree/static one/dir_E/UPST_2_E.txt', u'TestTree/static one/dir_E/UPST_3_E.txt', u'TestTree/static one/dir_E/UPST_4_E.txt', u'TestTree/static one/dir_E/WOCR_1_E.txt', u'TestTree/static one/dir_E/WOCR_2_E.txt', u'TestTree/static one/dir_E/WOCR_3_E.txt', u'TestTree/static one/dir_E/WOCR_4_E.txt'}
        assert allFiles == set(entry.path for entry in datafiles_endpoint())

    def test_datafiles_one_scalar_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = {u'TestTree/static one/dir_A/MURI_1_A.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_A/MURI_3_A.txt', u'TestTree/static one/dir_A/MURI_4_A.txt', u'TestTree/static one/dir_B/MURI_1_B.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_B/MURI_3_B.txt', u'TestTree/static one/dir_B/MURI_4_B.txt', u'TestTree/static one/dir_C/MURI_1_C.txt', u'TestTree/static one/dir_C/MURI_2_C.txt', u'TestTree/static one/dir_C/MURI_3_C.txt', u'TestTree/static one/dir_C/MURI_4_C.txt', u'TestTree/static one/dir_D/MURI_1_D.txt', u'TestTree/static one/dir_D/MURI_2_D.txt', u'TestTree/static one/dir_D/MURI_3_D.txt', u'TestTree/static one/dir_D/MURI_4_D.txt', u'TestTree/static one/dir_E/MURI_1_E.txt', u'TestTree/static one/dir_E/MURI_2_E.txt', u'TestTree/static one/dir_E/MURI_3_E.txt', u'TestTree/static one/dir_E/MURI_4_E.txt'}
        assert allFiles == set(entry.path for entry in datafiles_endpoint(name= "MURI"))

    def test_datafiles_one_iterable_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = set([u'TestTree/static one/dir_A/UPST_1_A.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_A/UPST_2_A.txt', u'TestTree/static one/dir_B/MURI_4_B.txt', u'TestTree/static one/dir_B/UPST_3_B.txt', u'TestTree/static one/dir_B/UPST_2_B.txt', u'TestTree/static one/dir_A/TETH_3_A.txt', u'TestTree/static one/dir_A/TETH_4_A.txt', u'TestTree/static one/dir_B/THRI_1_B.txt', u'TestTree/static one/dir_B/WOCR_4_B.txt', u'TestTree/static one/dir_A/UPST_4_A.txt', u'TestTree/static one/dir_A/UPST_3_A.txt', u'TestTree/static one/dir_B/UPST_4_B.txt', u'TestTree/static one/dir_B/MURI_3_B.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_A/MURI_1_A.txt', u'TestTree/static one/dir_B/THRI_3_B.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_B/WOCR_1_B.txt', u'TestTree/static one/dir_A/MURI_3_A.txt', u'TestTree/static one/dir_A/MURI_4_A.txt', u'TestTree/static one/dir_B/WOCR_3_B.txt', u'TestTree/static one/dir_A/THRI_3_A.txt', u'TestTree/static one/dir_A/WOCR_2_A.txt', u'TestTree/static one/dir_B/TETH_1_B.txt', u'TestTree/static one/dir_A/WOCR_1_A.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_B/TETH_3_B.txt', u'TestTree/static one/dir_B/WOCR_2_B.txt', u'TestTree/static one/dir_B/MURI_1_B.txt', u'TestTree/static one/dir_A/WOCR_4_A.txt', u'TestTree/static one/dir_A/WOCR_3_A.txt', u'TestTree/static one/dir_A/TETH_1_A.txt', u'TestTree/static one/dir_B/THRI_4_B.txt', u'TestTree/static one/dir_B/TETH_4_B.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_B/UPST_1_B.txt', u'TestTree/static one/dir_A/THRI_4_A.txt', u'TestTree/static one/dir_A/THRI_1_A.txt'])
        assert allFiles == set(entry.path for entry in datafiles_endpoint(char= ["A", "B"]))

    def test_datafiles_one_exclusion_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = set([u'TestTree/static one/dir_C/TETH_2_C.txt', u'TestTree/static one/dir_E/UPST_2_E.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_A/UPST_2_A.txt', u'TestTree/static one/dir_B/UPST_2_B.txt', u'TestTree/static one/dir_E/MURI_2_E.txt', u'TestTree/static one/dir_D/WOCR_2_D.txt', u'TestTree/static one/dir_C/WOCR_2_C.txt', u'TestTree/static one/dir_D/MURI_2_D.txt', u'TestTree/static one/dir_D/TETH_2_D.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_E/WOCR_2_E.txt', u'TestTree/static one/dir_C/MURI_2_C.txt', u'TestTree/static one/dir_C/THRI_2_C.txt', u'TestTree/static one/dir_D/THRI_2_D.txt', u'TestTree/static one/dir_C/UPST_2_C.txt', u'TestTree/static one/dir_A/WOCR_2_A.txt', u'TestTree/static one/dir_E/THRI_2_E.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_D/UPST_2_D.txt', u'TestTree/static one/dir_B/WOCR_2_B.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_E/TETH_2_E.txt'])
        assert allFiles == set(entry.path for entry in datafiles_endpoint(num= {"1": False, "3": False, "4": False}))

    def test_datafiles_one_callable_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = set([u'TestTree/static one/dir_C/TETH_2_C.txt', u'TestTree/static one/dir_C/TETH_4_C.txt', u'TestTree/static one/dir_E/THRI_3_E.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_C/THRI_2_C.txt', u'TestTree/static one/dir_C/THRI_4_C.txt', u'TestTree/static one/dir_D/THRI_3_D.txt', u'TestTree/static one/dir_C/TETH_3_C.txt', u'TestTree/static one/dir_D/THRI_4_D.txt', u'TestTree/static one/dir_D/TETH_4_D.txt', u'TestTree/static one/dir_A/TETH_3_A.txt', u'TestTree/static one/dir_A/TETH_4_A.txt', u'TestTree/static one/dir_C/TETH_1_C.txt', u'TestTree/static one/dir_B/THRI_1_B.txt', u'TestTree/static one/dir_D/TETH_2_D.txt', u'TestTree/static one/dir_C/THRI_1_C.txt', u'TestTree/static one/dir_D/THRI_1_D.txt', u'TestTree/static one/dir_B/THRI_3_B.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_C/THRI_3_C.txt', u'TestTree/static one/dir_E/TETH_4_E.txt', u'TestTree/static one/dir_D/THRI_2_D.txt', u'TestTree/static one/dir_A/THRI_3_A.txt', u'TestTree/static one/dir_E/THRI_2_E.txt', u'TestTree/static one/dir_B/TETH_1_B.txt', u'TestTree/static one/dir_E/TETH_3_E.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_B/TETH_3_B.txt', u'TestTree/static one/dir_D/TETH_1_D.txt', u'TestTree/static one/dir_E/THRI_1_E.txt', u'TestTree/static one/dir_E/THRI_4_E.txt', u'TestTree/static one/dir_A/TETH_1_A.txt', u'TestTree/static one/dir_B/THRI_4_B.txt', u'TestTree/static one/dir_A/THRI_4_A.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_E/TETH_1_E.txt', u'TestTree/static one/dir_E/TETH_2_E.txt', u'TestTree/static one/dir_D/TETH_3_D.txt', u'TestTree/static one/dir_B/TETH_4_B.txt', u'TestTree/static one/dir_A/THRI_1_A.txt'])
        assert allFiles == set(entry.path for entry in datafiles_endpoint(name= lambda s: s.startswith("T")))

    def test_datafiles_invalid_parameter(self, makeTestTree, datafiles_endpoint):
        with pytest.raises(TypeError):
            set(entry.path for entry in datafiles_endpoint(name= False))

    def test_datafiles_nonexisting_field(self, makeTestTree, datafiles_endpoint):
        with pytest.raises(TypeError):
            set(entry.path for entry in datafiles_endpoint(character= "pooh"))

    @pytest.fixture(scope= "module")
    def all_sitedocs(makeTestTree):
        return set(siteDocs())

    def test_sitedocs_two_singletons(self, makeTestTree, all_sitedocs):
        subset = set(siteDocs(name= "MURI", extension= "txt"))
        predicate = lambda entry: entry.name == "MURI" and entry.extension == "txt"
        correct = set(filter(predicate, all_sitedocs))

        assert subset == correct

    def test_sitedocs_two_iterables(self, makeTestTree, all_sitedocs):
        subset = set(siteDocs(name= ["MURI", "WOCR"], extension= ["txt", "png"]))
        predicate = lambda entry: entry.name in ["MURI", "WOCR"] and entry.extension in ["txt", "png"]
        correct = set(filter(predicate, all_sitedocs))

        assert subset == correct

## TODO: TestItemSelection

class TestSorting:
    @pytest.fixture(scope= "module", params= ["manual", "parsed"])
    def datafiles_endpoint(self, request, makeTestTree):
        if request.param == "manual":
            return datafiles
        else:
            return iyore.Dataset(os.path.join(base, structureFile)).datafiles

    def test_datafiles_sort_actually_sorts(self, makeTestTree, datafiles_endpoint):
        correct = [u'TestTree/static one/dir_A/MURI_1_A.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_A/MURI_3_A.txt', u'TestTree/static one/dir_A/MURI_4_A.txt', u'TestTree/static one/dir_A/TETH_1_A.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_A/TETH_3_A.txt', u'TestTree/static one/dir_A/TETH_4_A.txt', u'TestTree/static one/dir_A/THRI_1_A.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_A/THRI_3_A.txt', u'TestTree/static one/dir_A/THRI_4_A.txt', u'TestTree/static one/dir_A/UPST_1_A.txt', u'TestTree/static one/dir_A/UPST_2_A.txt', u'TestTree/static one/dir_A/UPST_3_A.txt', u'TestTree/static one/dir_A/UPST_4_A.txt', u'TestTree/static one/dir_A/WOCR_1_A.txt', u'TestTree/static one/dir_A/WOCR_2_A.txt', u'TestTree/static one/dir_A/WOCR_3_A.txt', u'TestTree/static one/dir_A/WOCR_4_A.txt', u'TestTree/static one/dir_B/MURI_1_B.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_B/MURI_3_B.txt', u'TestTree/static one/dir_B/MURI_4_B.txt', u'TestTree/static one/dir_B/TETH_1_B.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_B/TETH_3_B.txt', u'TestTree/static one/dir_B/TETH_4_B.txt', u'TestTree/static one/dir_B/THRI_1_B.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_B/THRI_3_B.txt', u'TestTree/static one/dir_B/THRI_4_B.txt', u'TestTree/static one/dir_B/UPST_1_B.txt', u'TestTree/static one/dir_B/UPST_2_B.txt', u'TestTree/static one/dir_B/UPST_3_B.txt', u'TestTree/static one/dir_B/UPST_4_B.txt', u'TestTree/static one/dir_B/WOCR_1_B.txt', u'TestTree/static one/dir_B/WOCR_2_B.txt', u'TestTree/static one/dir_B/WOCR_3_B.txt', u'TestTree/static one/dir_B/WOCR_4_B.txt', u'TestTree/static one/dir_C/MURI_1_C.txt', u'TestTree/static one/dir_C/MURI_2_C.txt', u'TestTree/static one/dir_C/MURI_3_C.txt', u'TestTree/static one/dir_C/MURI_4_C.txt', u'TestTree/static one/dir_C/TETH_1_C.txt', u'TestTree/static one/dir_C/TETH_2_C.txt', u'TestTree/static one/dir_C/TETH_3_C.txt', u'TestTree/static one/dir_C/TETH_4_C.txt', u'TestTree/static one/dir_C/THRI_1_C.txt', u'TestTree/static one/dir_C/THRI_2_C.txt', u'TestTree/static one/dir_C/THRI_3_C.txt', u'TestTree/static one/dir_C/THRI_4_C.txt', u'TestTree/static one/dir_C/UPST_1_C.txt', u'TestTree/static one/dir_C/UPST_2_C.txt', u'TestTree/static one/dir_C/UPST_3_C.txt', u'TestTree/static one/dir_C/UPST_4_C.txt', u'TestTree/static one/dir_C/WOCR_1_C.txt', u'TestTree/static one/dir_C/WOCR_2_C.txt', u'TestTree/static one/dir_C/WOCR_3_C.txt', u'TestTree/static one/dir_C/WOCR_4_C.txt', u'TestTree/static one/dir_D/MURI_1_D.txt', u'TestTree/static one/dir_D/MURI_2_D.txt', u'TestTree/static one/dir_D/MURI_3_D.txt', u'TestTree/static one/dir_D/MURI_4_D.txt', u'TestTree/static one/dir_D/TETH_1_D.txt', u'TestTree/static one/dir_D/TETH_2_D.txt', u'TestTree/static one/dir_D/TETH_3_D.txt', u'TestTree/static one/dir_D/TETH_4_D.txt', u'TestTree/static one/dir_D/THRI_1_D.txt', u'TestTree/static one/dir_D/THRI_2_D.txt', u'TestTree/static one/dir_D/THRI_3_D.txt', u'TestTree/static one/dir_D/THRI_4_D.txt', u'TestTree/static one/dir_D/UPST_1_D.txt', u'TestTree/static one/dir_D/UPST_2_D.txt', u'TestTree/static one/dir_D/UPST_3_D.txt', u'TestTree/static one/dir_D/UPST_4_D.txt', u'TestTree/static one/dir_D/WOCR_1_D.txt', u'TestTree/static one/dir_D/WOCR_2_D.txt', u'TestTree/static one/dir_D/WOCR_3_D.txt', u'TestTree/static one/dir_D/WOCR_4_D.txt', u'TestTree/static one/dir_E/MURI_1_E.txt', u'TestTree/static one/dir_E/MURI_2_E.txt', u'TestTree/static one/dir_E/MURI_3_E.txt', u'TestTree/static one/dir_E/MURI_4_E.txt', u'TestTree/static one/dir_E/TETH_1_E.txt', u'TestTree/static one/dir_E/TETH_2_E.txt', u'TestTree/static one/dir_E/TETH_3_E.txt', u'TestTree/static one/dir_E/TETH_4_E.txt', u'TestTree/static one/dir_E/THRI_1_E.txt', u'TestTree/static one/dir_E/THRI_2_E.txt', u'TestTree/static one/dir_E/THRI_3_E.txt', u'TestTree/static one/dir_E/THRI_4_E.txt', u'TestTree/static one/dir_E/UPST_1_E.txt', u'TestTree/static one/dir_E/UPST_2_E.txt', u'TestTree/static one/dir_E/UPST_3_E.txt', u'TestTree/static one/dir_E/UPST_4_E.txt', u'TestTree/static one/dir_E/WOCR_1_E.txt', u'TestTree/static one/dir_E/WOCR_2_E.txt', u'TestTree/static one/dir_E/WOCR_3_E.txt', u'TestTree/static one/dir_E/WOCR_4_E.txt']
        result = datafiles_endpoint(sort= lambda e: e.path)

        assert list(result) == correct

    def test_datafiles_sort_func_by_path(self, makeTestTree, datafiles_endpoint):
        keyfunc = lambda e: e.path
        correct = sorted(datafiles_endpoint(), key= keyfunc)
        result = list(datafiles_endpoint(sort= keyfunc))

        assert result == correct

    def test_datafiles_sort_func_by_num(self, makeTestTree, datafiles_endpoint):
        keyfunc = lambda e: e.num
        correct = sorted(datafiles_endpoint(), key= keyfunc)
        result = list(datafiles_endpoint(sort= keyfunc))

        assert result == correct

    def test_datafiles_sort_string_by_num(self, makeTestTree, datafiles_endpoint):
        correct = sorted(datafiles_endpoint(), key= lambda e: e.num)
        result = list(datafiles_endpoint(sort= "num"))

        assert result == correct

    def test_datafiles_sort_strings_by_char_num(self, makeTestTree, datafiles_endpoint):
        correct = sorted(datafiles_endpoint(), key= lambda e: (e.char, e.num))
        result = list(datafiles_endpoint(sort= ("char", "num")))

        assert result == correct

    def test_datafiles_subset_sort_strings_by_char_num(self, makeTestTree, datafiles_endpoint):
        params = {"num": ["2", "4"], "char": list("ACD")}

        correct = sorted(datafiles_endpoint(**params), key= lambda e: (e.char, e.num))
        result = list(datafiles_endpoint(sort= ("char", "num"), **params))

        assert result == correct

class TestFillingWithLiterals:
    @pytest.fixture(scope= "module", params= ["manual", "parsed"])
    def datafiles_endpoint(self, request, makeTestTree):
        if request.param == "manual":
            return datafiles
        else:
            return iyore.Dataset(os.path.join(base, structureFile)).datafiles

    def test_isLiteral(self):
        assert iyore.Pattern(r"  asdf123-sdf _!@#%&").isLiteral
        assert iyore.Pattern(r"").isLiteral
        assert not iyore.Pattern("data *").isLiteral
        assert not iyore.Pattern(r"test\.txt").isLiteral
        assert not iyore.Pattern(r"item (?P<grp>\d{3})").isLiteral

    def test_filling_literal_is_unchanged(self):
        literal_pattern = iyore.Pattern("this is a literal pattern with 8 words!")
        assert literal_pattern.isLiteral
        filled = literal_pattern.fill({})
        assert filled.value == literal_pattern.value

    def test_filling_no_named_groups_is_unchanged(self):
        pattern = iyore.Pattern(r"(\w+)\s+: ((\d{1-5})\.(\d+))")
        filled = pattern.fill({})
        assert filled.value == pattern.value

    def test_filling_basic_named_group(self):
        pattern = iyore.Pattern(r"(?P<word_one>\w+) cat [d|fr]og")
        filled = pattern.fill({"word_one": "orangutan"})
        assert filled.value == r"orangutan cat [d|fr]og"

    def test_filling_named_group_spans_whole_pattern(self):
        pattern = iyore.Pattern(r"(?P<thing>\d+ \w+)")
        filled = pattern.fill({"thing": "22 blue"})
        assert filled.value == "22 blue"
        assert filled.isLiteral

    def test_filling_multiple_named_groups(self):
        pattern = iyore.Pattern(r"uses (?P<desc>\d+ \w+) (?P<thing>\w+)s for (?P<num>\d+) (?P<use>.+)")
        filled = pattern.fill({
            "desc": "8 sizeable",
            "thing": "lozenge",
            "num": "4",
            "use":"parties and general throat healing"
            })
        assert filled.value == r"uses 8 sizeable lozenges for 4 parties and general throat healing"

    def test_escaping_filled_literals(self):
        pattern = iyore.Pattern(r"I said, (?P<statement>.+)")
        statement = r'"Golly, what many of you! Hark, where is your milkman? (I must give\pay him $$ [*quickly!*])"'
        filled = pattern.fill({"statement": statement})
        assert filled.matches("I said, "+statement) == {"statement": statement}

    @pytest.mark.xfail
    def test_filling_inner_nested_named_group(self):
        pattern = iyore.Pattern(r"(?P<outer>song_(?P<song_name>.+))\.mp3")
        filled = pattern.fill({"song_name": "close_ur_2_eyes"})
        assert filled.matches("song_close_ur_2_eyes.mp3") == {"song_name": "close_ur_2_eyes", "outer": "song_close_ur_2_eyes"}

    @pytest.mark.xfail
    def test_filling_outer_nested_named_group(self):
        pattern = iyore.Pattern(r"(?P<outer>song_(?P<song_name>.+))\.mp3")
        filled = pattern.fill({"outer": "song_gimmie_shelter"})
        assert filled.matches("song_gimmie_shelter.mp3") == {"outer": "song_gimmie_shelter", "song_name": "gimmie_shelter"}

    def test_catches_nonexistant_field(self):
        pattern = iyore.Pattern(r"map (?P<number>\d) for client (?P<client>.+)")
        with pytest.raises(ValueError):
            pattern.fill({"client": "Alfred P. Sloan", "account": "200120"})

    def test_catches_malformatted_literal(self):
        pattern = iyore.Pattern(r"(?P<bird>[\w|\s]+) call #(?P<num>\d+)\.mp3")
        with pytest.raises(ValueError):
            pattern.fill({"bird": "Blue-eyed penguin", "num": "03"})

    def test_filled_results_all_literals(self, datafiles_endpoint):
        params = {
            "char": "B",
            "name": "MURI",
            "num": "3"
        }
        filled_results = list(datafiles_endpoint(**params))
        actual_results = list(datafiles_endpoint(**{param: [value] for param, value in params.items()}))
        assert len(filled_results) == len(actual_results) == 1
        assert filled_results[0] == actual_results[0]
        assert filled_results[0].fields == actual_results[0].fields

    def test_filled_results_some_literals(self, datafiles_endpoint):
        params = {
            "char": "B",
            "num": "3"
        }
        filled_results = { entry.path: entry for entry in datafiles_endpoint(**params) }
        actual_results = { entry.path: entry for entry in datafiles_endpoint(**{param: [value] for param, value in params.items()}) }
        assert len(filled_results) == len(actual_results)
        for path, actual in actual_results.items():
            filled = filled_results[path]
            assert filled.fields == actual.fields

class TestStructureFileParsing:
    @staticmethod
    def assert_simple_structure(ds):
        assert set(ds.endpoints.keys()) == {"pics", "sounds", "audio", "srcid"}
        assert [part.value for part in ds.pics.parts] == ["DATA", "Photos"]
        assert [part.value for part in ds.sounds.parts] == ["DATA", "sound"]
        assert [part.value for part in ds.audio.parts] == ["DATA", "sound", "recording.wav"]
        assert [part.value for part in ds.srcid.parts] == ["ANALYSIS", "SRCID.txt"]

    def test_simple_structure_file(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound
        audio: recording.wav
ANALYSIS
    srcid: SRCID.txt""")

        ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))
        self.assert_simple_structure(ds)

    def test_simple_structure_file_tabs(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
	pics: Photos
	sounds: sound
		audio: recording.wav
ANALYSIS
	srcid: SRCID.txt""")

        ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))
        self.assert_simple_structure(ds)

    def test_simple_structure_file_skip_blanklines(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""

DATA
    pics: Photos
    
    sounds: sound
        audio: recording.wav


ANALYSIS
    srcid: SRCID.txt""")

        ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))
        self.assert_simple_structure(ds)

    def test_simple_structure_file_catches_inconsistent_indent(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
   pics: Photos
    sounds: sound
        audio: recording.wav
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_catches_overindent(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound
            audio: recording.wav
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_catches_firstline_overindent(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""    DATA
        pics: Photos
        sounds: sound
                audio: recording.wav
    ANALYSIS
        srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_catches_mixed_indents(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound
    	audio: recording.wav
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

class TestInteractions:
    @pytest.fixture(scope= "module")
    def dataset(self):
        return iyore.Dataset(os.path.join(base, structureFile))

    def test_dataset_attr_access_to_endpoint(self, dataset):
        datafiles_endpoint = dataset.endpoints["datafiles"]
        assert dataset.datafiles is datafiles_endpoint

    def test_dataset_getitem_access_to_endpoint(self, dataset):
        datafiles_endpoint = dataset.endpoints["datafiles"]
        assert dataset["datafiles"] is datafiles_endpoint

    def test_dataset_dir(self, dataset):
        dsdir = set(dir(dataset))
        endpoints = set(dataset.endpoints.keys())
        assert endpoints.issubset(dsdir)

    def test_entry_attr_access(self, dataset):
        res = dataset.basic()
        entry = next(iter(res))
        assert entry.char == entry.fields["char"]

    def test_entry_dict_access(self, dataset):
        res = dataset.basic()
        entry = next(iter(res))
        assert entry["char"] == entry.fields["char"]

    def test_entry_dir(self, dataset):
        res = dataset.basic()
        entry = next(iter(res))
        edir = set(dir(entry))
        fields = set(entry.fields.keys())
        fields.add("path")
        assert fields.issubset(edir)

if __name__ == '__main__':
    makeTestTree(None)
    # makeBasicStructureFile(None)
    print()
    print("datafiles:", datafiles)
    print("siteDocs:", siteDocs)
    print("basic:", basic)