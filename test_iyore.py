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

        entries = list(basic.where())
        assert len(entries) == len(chars)
        for entry in entries:
            assert entry.path in paths
            paths.remove(entry.path)
        assert len(paths) == 0

    def test_attribute_access_mirrors_endpoint_fields(self, makeTestTree):
        chars = set("ABC")

        for entry in basic.where():
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
        assert allFiles == set(entry.path for entry in datafiles_endpoint.where())

    def test_datafiles_one_scalar_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = {u'TestTree/static one/dir_A/MURI_1_A.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_A/MURI_3_A.txt', u'TestTree/static one/dir_A/MURI_4_A.txt', u'TestTree/static one/dir_B/MURI_1_B.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_B/MURI_3_B.txt', u'TestTree/static one/dir_B/MURI_4_B.txt', u'TestTree/static one/dir_C/MURI_1_C.txt', u'TestTree/static one/dir_C/MURI_2_C.txt', u'TestTree/static one/dir_C/MURI_3_C.txt', u'TestTree/static one/dir_C/MURI_4_C.txt', u'TestTree/static one/dir_D/MURI_1_D.txt', u'TestTree/static one/dir_D/MURI_2_D.txt', u'TestTree/static one/dir_D/MURI_3_D.txt', u'TestTree/static one/dir_D/MURI_4_D.txt', u'TestTree/static one/dir_E/MURI_1_E.txt', u'TestTree/static one/dir_E/MURI_2_E.txt', u'TestTree/static one/dir_E/MURI_3_E.txt', u'TestTree/static one/dir_E/MURI_4_E.txt'}
        assert allFiles == set(entry.path for entry in datafiles_endpoint.where(name= "MURI"))

    def test_datafiles_one_iterable_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = set([u'TestTree/static one/dir_A/UPST_1_A.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_A/UPST_2_A.txt', u'TestTree/static one/dir_B/MURI_4_B.txt', u'TestTree/static one/dir_B/UPST_3_B.txt', u'TestTree/static one/dir_B/UPST_2_B.txt', u'TestTree/static one/dir_A/TETH_3_A.txt', u'TestTree/static one/dir_A/TETH_4_A.txt', u'TestTree/static one/dir_B/THRI_1_B.txt', u'TestTree/static one/dir_B/WOCR_4_B.txt', u'TestTree/static one/dir_A/UPST_4_A.txt', u'TestTree/static one/dir_A/UPST_3_A.txt', u'TestTree/static one/dir_B/UPST_4_B.txt', u'TestTree/static one/dir_B/MURI_3_B.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_A/MURI_1_A.txt', u'TestTree/static one/dir_B/THRI_3_B.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_B/WOCR_1_B.txt', u'TestTree/static one/dir_A/MURI_3_A.txt', u'TestTree/static one/dir_A/MURI_4_A.txt', u'TestTree/static one/dir_B/WOCR_3_B.txt', u'TestTree/static one/dir_A/THRI_3_A.txt', u'TestTree/static one/dir_A/WOCR_2_A.txt', u'TestTree/static one/dir_B/TETH_1_B.txt', u'TestTree/static one/dir_A/WOCR_1_A.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_B/TETH_3_B.txt', u'TestTree/static one/dir_B/WOCR_2_B.txt', u'TestTree/static one/dir_B/MURI_1_B.txt', u'TestTree/static one/dir_A/WOCR_4_A.txt', u'TestTree/static one/dir_A/WOCR_3_A.txt', u'TestTree/static one/dir_A/TETH_1_A.txt', u'TestTree/static one/dir_B/THRI_4_B.txt', u'TestTree/static one/dir_B/TETH_4_B.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_B/UPST_1_B.txt', u'TestTree/static one/dir_A/THRI_4_A.txt', u'TestTree/static one/dir_A/THRI_1_A.txt'])
        assert allFiles == set(entry.path for entry in datafiles_endpoint.where(char= ["A", "B"]))

    def test_datafiles_one_exclusion_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = set([u'TestTree/static one/dir_C/TETH_2_C.txt', u'TestTree/static one/dir_E/UPST_2_E.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_B/MURI_2_B.txt', u'TestTree/static one/dir_A/UPST_2_A.txt', u'TestTree/static one/dir_B/UPST_2_B.txt', u'TestTree/static one/dir_E/MURI_2_E.txt', u'TestTree/static one/dir_D/WOCR_2_D.txt', u'TestTree/static one/dir_C/WOCR_2_C.txt', u'TestTree/static one/dir_D/MURI_2_D.txt', u'TestTree/static one/dir_D/TETH_2_D.txt', u'TestTree/static one/dir_A/MURI_2_A.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_E/WOCR_2_E.txt', u'TestTree/static one/dir_C/MURI_2_C.txt', u'TestTree/static one/dir_C/THRI_2_C.txt', u'TestTree/static one/dir_D/THRI_2_D.txt', u'TestTree/static one/dir_C/UPST_2_C.txt', u'TestTree/static one/dir_A/WOCR_2_A.txt', u'TestTree/static one/dir_E/THRI_2_E.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_D/UPST_2_D.txt', u'TestTree/static one/dir_B/WOCR_2_B.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_E/TETH_2_E.txt'])
        assert allFiles == set(entry.path for entry in datafiles_endpoint.where(num= {"1": False, "3": False, "4": False}))

    def test_datafiles_one_callable_parameter(self, makeTestTree, datafiles_endpoint):
        allFiles = set([u'TestTree/static one/dir_C/TETH_2_C.txt', u'TestTree/static one/dir_C/TETH_4_C.txt', u'TestTree/static one/dir_E/THRI_3_E.txt', u'TestTree/static one/dir_A/TETH_2_A.txt', u'TestTree/static one/dir_C/THRI_2_C.txt', u'TestTree/static one/dir_C/THRI_4_C.txt', u'TestTree/static one/dir_D/THRI_3_D.txt', u'TestTree/static one/dir_C/TETH_3_C.txt', u'TestTree/static one/dir_D/THRI_4_D.txt', u'TestTree/static one/dir_D/TETH_4_D.txt', u'TestTree/static one/dir_A/TETH_3_A.txt', u'TestTree/static one/dir_A/TETH_4_A.txt', u'TestTree/static one/dir_C/TETH_1_C.txt', u'TestTree/static one/dir_B/THRI_1_B.txt', u'TestTree/static one/dir_D/TETH_2_D.txt', u'TestTree/static one/dir_C/THRI_1_C.txt', u'TestTree/static one/dir_D/THRI_1_D.txt', u'TestTree/static one/dir_B/THRI_3_B.txt', u'TestTree/static one/dir_B/TETH_2_B.txt', u'TestTree/static one/dir_C/THRI_3_C.txt', u'TestTree/static one/dir_E/TETH_4_E.txt', u'TestTree/static one/dir_D/THRI_2_D.txt', u'TestTree/static one/dir_A/THRI_3_A.txt', u'TestTree/static one/dir_E/THRI_2_E.txt', u'TestTree/static one/dir_B/TETH_1_B.txt', u'TestTree/static one/dir_E/TETH_3_E.txt', u'TestTree/static one/dir_A/THRI_2_A.txt', u'TestTree/static one/dir_B/TETH_3_B.txt', u'TestTree/static one/dir_D/TETH_1_D.txt', u'TestTree/static one/dir_E/THRI_1_E.txt', u'TestTree/static one/dir_E/THRI_4_E.txt', u'TestTree/static one/dir_A/TETH_1_A.txt', u'TestTree/static one/dir_B/THRI_4_B.txt', u'TestTree/static one/dir_A/THRI_4_A.txt', u'TestTree/static one/dir_B/THRI_2_B.txt', u'TestTree/static one/dir_E/TETH_1_E.txt', u'TestTree/static one/dir_E/TETH_2_E.txt', u'TestTree/static one/dir_D/TETH_3_D.txt', u'TestTree/static one/dir_B/TETH_4_B.txt', u'TestTree/static one/dir_A/THRI_1_A.txt'])
        assert allFiles == set(entry.path for entry in datafiles_endpoint.where(name= lambda s: s.startswith("T")))

    def test_datafiles_invalid_parameter(self, makeTestTree, datafiles_endpoint):
        with pytest.raises(TypeError):
            datafiles_endpoint.where(name= False)
        with pytest.raises(TypeError):
            datafiles_endpoint.where(name= None)

    @pytest.fixture(scope= "module")
    def all_sitedocs(makeTestTree):
        return set(siteDocs.where())

    def test_sitedocs_two_singletons(self, makeTestTree, all_sitedocs):
        subset = set(siteDocs.where(name= "MURI", extension= "txt"))
        predicate = lambda entry: entry.name == "MURI" and entry.extension == "txt"
        correct = set(filter(predicate, all_sitedocs))

        assert subset == correct

    def test_sitedocs_two_iterables(self, makeTestTree, all_sitedocs):
        subset = set(siteDocs.where(name= ["MURI", "WOCR"], extension= ["txt", "png"]))
        predicate = lambda entry: entry.name in ["MURI", "WOCR"] and entry.extension in ["txt", "png"]
        correct = set(filter(predicate, all_sitedocs))

        assert subset == correct


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

    def test_simple_structure_file_with_parsers(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> lambda e: e.path.lower()>>len   ->sum
        audio: recording.wav>> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))
        assert len(ds.sounds.parsers) == 3
        assert len(ds.audio.parsers) == 1
        assert len(ds.pics.parsers) == 0

    def test_simple_structure_file_with_parsers_lt_okay(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> lambda e: len(e.path) > 3  ->sum
        audio: recording.wav>> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))
        assert len(ds.sounds.parsers) == 2
        assert len(ds.audio.parsers) == 1
        assert len(ds.pics.parsers) == 0

    def test_simple_structure_file_with_parsers_catches_dangling(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> lambda e: e.path.lower() >> len >>
        audio: recording.wav >> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_with_parsers_catches_extra_arrow(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> -> lambda e: e.path.lower() >> len
        audio: recording.wav >> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_with_parsers_catches_wrong_arrow(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> lambda e: e.path.lower() >>> len
        audio: recording.wav >> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_with_parsers_catches_syntax_error(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> lambda e: e.path.lower( >>> len
        audio: recording.wav >> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_with_parsers_catches_not_expression(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> def n(x): return x >> len
        audio: recording.wav >> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))

    def test_simple_structure_file_with_parsers_catches_not_callable(self, tmpdir):
        with open(os.path.join(str(tmpdir), "simple.txt"), "w", encoding= "utf-8") as f:
            f.write("""DATA
    pics: Photos
    sounds: sound >> 3*2 >> len
        audio: recording.wav >> lambda f: open(f)
ANALYSIS
    srcid: SRCID.txt""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(str(tmpdir), "simple.txt"))



class TestParsers:
    @pytest.fixture
    def sitedocs(self, makeTestTree):
        return iyore.Endpoint([r"static two", r"(?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+)"], base)

    @pytest.fixture
    def titles(self, sitedocs):
        return [e.title for e in sitedocs.where()]

    @pytest.fixture
    def titleLens(self, titles):
        return [ len(t) for t in titles ]

    @staticmethod
    def times(x, amt= 1):
        return x * amt
    @staticmethod
    def div(x, amt= 1):
        return x / amt

    def test_one_mapper(self, sitedocs, titles):
        sitedocs.addMappers(lambda e: e.title)
        res = list(sitedocs.where())
        assert res == titles

    def test_multiple_mappers(self, sitedocs, titleLens):
        sitedocs.addMappers(lambda e: e.title, len, math.sqrt)
        res = list(sitedocs.where())
        correct = list(map(math.sqrt, titleLens))
        assert res == correct

    def test_mappers_and_reducers(self, sitedocs, titleLens):
        sitedocs.addMappers(lambda e: e.title, len)
        sitedocs.addReducers(sum, lambda x: x / 4)
        res = sitedocs.where()
        correct = sum(titleLens) / 4
        assert res == correct

    def test_parser_kwargs(self, sitedocs, titleLens):
        sitedocs.addMappers(lambda e: e.title, len, self.times, self.div)
        print(sitedocs._parser_kwargs_order)
        res = list(sitedocs.where(times_amt= 4, div_amt= 2))
        correct = [ (x*4)/2 for x in titleLens ]
        assert res == correct

    def test_catch_invalid_kwargs(self, sitedocs):
        sitedocs.addMappers(lambda e: e.title, len, self.times, self.div)
        with pytest.raises(TypeError):
            list(sitedocs.where(times_bleh= 2))
        with pytest.raises(TypeError):
            list(sitedocs.where(bleh_amt= 2))

    def test_mappers_and_reducers_with_kwargs(self, sitedocs, titleLens):
        sitedocs.addMappers(lambda e: e.title, len, self.times, math.sqrt)
        sitedocs.addReducers(sum, self.div, int, range)
        res = list(sitedocs.where(times_amt= 2, div_amt= 4))
        
        correct = list(range(int(sum(map(lambda x: math.sqrt(x*2), titleLens)) / 4)))
        assert res == correct

class TestParsersInStructureFile:
    @pytest.fixture(scope= "class")
    def ds_unparsed(makeTestTree):
        return iyore.Dataset(os.path.join(base, structureFile))

    def test_one_mapper(self, makeTestTree, ds_unparsed):
        with open(os.path.join(base, "struct_with_parsers.txt"), "w", encoding= "utf-8") as f:
            f.write("""
static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt >> lambda e: e.name
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+) >> lambda e: e.title
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        ds = iyore.Dataset(os.path.join(base, "struct_with_parsers.txt"))

        res = list(ds.datafiles.where())
        correct = list(e.name for e in ds_unparsed.datafiles.where())
        assert res == correct

        res = list(ds.siteDocs.where())
        correct = list(e.title for e in ds_unparsed.siteDocs.where())
        assert res == correct

        os.remove(os.path.join(base, "struct_with_parsers.txt"))

    def test_multiple_mappers(self, makeTestTree, ds_unparsed):
        with open(os.path.join(base, "struct_with_parsers.txt"), "w", encoding= "utf-8") as f:
            f.write("""
static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt >> lambda e: e.name >> len >> lambda x: x*2
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+) >> lambda e: e.title  >> len >> lambda x: x*2
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        ds = iyore.Dataset(os.path.join(base, "struct_with_parsers.txt"))

        res = list(ds.datafiles.where())
        correct = list(len(e.name)*2 for e in ds_unparsed.datafiles.where())
        assert res == correct

        res = list(ds.siteDocs.where())
        correct = list(len(e.title)*2 for e in ds_unparsed.siteDocs.where())
        assert res == correct

        os.remove(os.path.join(base, "struct_with_parsers.txt"))

    def test_mappers_and_reducers(self, makeTestTree, ds_unparsed):
        with open(os.path.join(base, "struct_with_parsers.txt"), "w", encoding= "utf-8") as f:
            f.write("""
static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt >> lambda e: e.num >> int -> sum
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+)
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        ds = iyore.Dataset(os.path.join(base, "struct_with_parsers.txt"))

        res = ds.datafiles.where()
        correct = sum(int(e.num) for e in ds_unparsed.datafiles.where())
        assert res == correct

        os.remove(os.path.join(base, "struct_with_parsers.txt"))

class TestImports:
    @pytest.fixture(scope= "class")
    def ds_unparsed(makeTestTree):
        return iyore.Dataset(os.path.join(base, structureFile))

    def test_import_no_parsers(self, makeTestTree):
        with open(os.path.join(base, "struct_with_imports.txt"), "w", encoding= "utf-8") as f:
            f.write("""
import re
from math  import sqrt

from math  import ceil   as ceiling
import    random as    thatsSoRandom

static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+)
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        # No exceptions should raise
        ds = iyore.Dataset(os.path.join(base, "struct_with_imports.txt"))

        os.remove(os.path.join(base, "struct_with_imports.txt"))

    def test_import_with_parsers(self, makeTestTree, ds_unparsed):
        with open(os.path.join(base, "struct_with_imports.txt"), "w", encoding= "utf-8") as f:
            f.write("""
import math

from math import ceil as ceiling

static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt >> lambda e: e.num >> int >> math.sqrt
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+) >> lambda e: e.title >> len >> math.sqrt >> ceiling
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        ds = iyore.Dataset(os.path.join(base, "struct_with_imports.txt"))

        res = list(ds.datafiles.where())
        correct = list(math.sqrt(int(e.num)) for e in ds_unparsed.datafiles.where())
        assert res == correct

        res = list(ds.siteDocs.where())
        correct = list(math.ceil(math.sqrt(len(e.title))) for e in ds_unparsed.siteDocs.where())
        assert res == correct

        os.remove(os.path.join(base, "struct_with_imports.txt"))

    def test_import_catches_nonexistet_module(self, makeTestTree):
        with open(os.path.join(base, "struct_with_imports.txt"), "w", encoding= "utf-8") as f:
            f.write("""
import math
import lebowski

static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt >> lambda e: e.num >> int >> math.sqrt
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+) >> lambda e: e.title >> len >> math.sqrt >> math.ceiling
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(base, "struct_with_imports.txt"))

        os.remove(os.path.join(base, "struct_with_imports.txt"))

    def test_import_catches_import_error(self, makeTestTree):
        with open(os.path.join(base, "failureIsAnOption.py"), "w", encoding= "utf-8") as f:
            f.write("""
willFail = "a string" + 4
""")

        with open(os.path.join(base, "struct_with_imports.txt"), "w", encoding= "utf-8") as f:
            f.write("""
import math
from . import failureIsAnOption

static one
    dir_(?P<char>[A-Z])
        datafiles: (?P<name>[A-Z]{4})_(?P<num>\d)_(?P<char>[A-Z])\.txt >> lambda e: e.num >> int >> math.sqrt
static two
    siteDocs: (?P<name>[A-Z]{4}) (?P<title>.*)\.(?P<extension>.+) >> lambda e: e.title >> len >> math.sqrt >> math.ceiling
static three
    basic: file_(?P<char>[A-Z])\.txt
""")

        with pytest.raises(ValueError):
            ds = iyore.Dataset(os.path.join(base, "struct_with_imports.txt"))

        os.remove(os.path.join(base, "struct_with_imports.txt"))
        os.remove(os.path.join(base, "failureIsAnOption.py"))



if __name__ == '__main__':
    makeTestTree(None)
    # makeBasicStructureFile(None)
    print()
    print("datafiles:", datafiles)
    print("siteDocs:", siteDocs)
    print("basic:", basic)