# Python 2 and 3 cross-compatibility:
from __future__ import print_function, division, unicode_literals, absolute_import
from builtins import (bytes, str, int, dict, object, range, map, filter, zip, round, pow, open)
from future.utils import (iteritems, itervalues)

import re
import os
import sys
import numbers
import io
import functools
import itertools
import operator
import inspect
import traceback
import heapq

## TODO overall:

## 1. 2-3 compatibility
## 2. Error handling
## 3. Docstrings & cleanup
## 4. Unit tests? (both 2 and 3)
## 5. Hierarchy file
## 6. Parsers

## 7. User-friendly pattern syntax
## 8. Composable query syntax??

structureFileName = ".structure.txt"

class Dataset(object):
    # TODO: dict-like?  --> sort of---just __getitem__
    def __init__(self, path, structure= None):
        if structure is None:
            # TODO: smarter finding structure file
            dirname, basename = os.path.split(path)
            if basename == "":
                basename = structureFileName
            self.base = Entry(dirname)
            self.endpoints = self._parseStructureFile(structfilePath= os.path.join(dirname, basename))
        else:
            self.base = Entry(path)
            self.endpoints = self._parseStructureFile(structfileString= str(structure))

    def __getattr__(self, attr):
        try:
            return self.endpoints[attr]
        except KeyError:
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError("Dataset instance has no endpoint or attribute '{}'".format(attr))

    def __dir__(self):
        # TODO: infinite recursion!!
        return self.endpoints.keys() + dir(self)

    def __repr__(self):
        return 'Dataset("{}")\nEndpoints:\n{}'.format(self.base.path, "\n".join("  - {}: {}".format(name, repr(endpoint)) for name, endpoint in iteritems(self.endpoints)))

    def _parseStructureFile(self, structfilePath= None, structfileString= None):
        if structfilePath is None and structfileString is None:
            raise ValueError("No structure file path or string given")

        indent = None
        patternsStack = []
        endpoints = {}
        lastIndent = 0

        # TODO: maybe custom exception class?:
        def error(msg, line, linenum):
            print('Error in structure file "{}", line {}:\n{}\n{}'.format(structfilePath, linenum+1, line, msg), file= sys.stderr)
            raise ValueError('Error on line {} in file "{}"'.format(linenum, structfilePath))

        linePattern = re.compile(r"(\s*)(.*)")      # groups: indent, content
        importLinePattern = re.compile(r"^(?:from\s+.+\s+)?(?:import\s+.+\s*)(?:as\s+.+\s*)?$")
        contentPattern = re.compile(r"(?:([A-z]\w*):\s?)?(.+)")     # groups: endpointName, endpointPattern
        with open(structfilePath, encoding= "utf-8") if structfilePath else io.StringIO(structfileString) as f:
            # TODO: comments
            # TODO: more descriptive errors?
            # TODO: show neighboring lines and highlight error
            # TODO: ensure endpoint names are valid Python identifiers

            for linenum, line in enumerate(f):
                # split indentation and content
                try:
                    ind, content = linePattern.match(line).groups()
                except AttributeError:
                    error("Unparseable line", line, linenum)

                if content == "":
                    # skip blank lines
                    # TODO: maybe only allow if ind == "" as well?
                    continue

                # split (possible) endpoint name, pattern
                try:
                    name, pattern = contentPattern.match(content).groups()
                except AttributeError:
                    error("Unparseable entry", line, linenum)

                # parse pattern
                try:
                    pattern = Pattern(pattern)
                except ValueError as e:
                    error(e.args[0], line, linenum)

                # determine indentation format from first lines
                if indent is None:
                    if ind == "":
                        currentIndent = 0
                    else:
                        if patternsStack == []:
                            error("Unexpected indent in first entry", line, linenum)
                        else:
                            indent = ind
                            currentIndent = 1
                # check indentation and figure out indentation level
                else:
                    currentIndent = len(ind) / len(indent)
                    currentIndint = int(currentIndent)
                    if currentIndent != currentIndint:
                        error("Inconsistent indent width: expected a multiple of {} whitespace characters, instead found {}".format(len(indent), len(ind)), line, linenum)
                    else:
                        currentIndent = currentIndint
                    if currentIndent * indent != ind:
                        error("Inconsistent indent characters: expected {}s, found a {}".format("space" if indent[0] == " " else "tab", "tab" if indent[0] == " " else "space"), line, linenum)

                # based on indentation, modify pattern stack
                if currentIndent == 0:
                    patternsStack[:] = [pattern]
                elif currentIndent == lastIndent + 1:
                    patternsStack.append(pattern)
                elif currentIndent == lastIndent:
                    patternsStack[-1] = pattern
                elif currentIndent < lastIndent:
                    patternsStack = patternsStack[:currentIndent]
                    patternsStack.append(pattern)
                else:
                    error("Too many indents: previous line was indented {} times, so this can be indented at most {} times, but found {} indents".format(lastIndent, lastIndent+1, currentIndent), line, linenum)

                lastIndent = currentIndent

                # if a name is given, register (a copy of) the current pattern stack as an endpoint
                # TODO: multiple leaf patterns
                if name is not None:
                    if name in endpoints:
                        error("The endpoint '{}' already exists, try a different name".format(name), line, linenum)
                    else:
                        endpoints[name] = Endpoint(list(patternsStack), self.base)

        return endpoints


class Endpoint(object):
    def __init__(self, parts, base):
        # TODO: hold dataset instead of base?
        self.base = base if isinstance(base, Entry) else Entry(base)
        self.parts = parts if isinstance(parts[0], Pattern) else list(map(Pattern, parts))
        self.fields = set.union( *(set(part.fields) for part in self.parts) )

    def __call__(self, sort= None, **params):
        if sort is not None:
            # singleton string (entry attr to sort on)
            if isinstance(sort, basestring):
                sortFunc = operator.attrgetter(sort)
            # function (entry -> orderable type)
            elif hasattr(sort, "__call__"):
                sortFunc = sort
            # iterable of strings
            else:
                try:
                    iter(sort)
                except TypeError:
                    raise TypeError("Sort key must be a singleton string, iterable of strings, or function; instead got non-iterable type {}".format(type(sort)))
                if all(isinstance(key, basestring) for key in sort):
                    sortFunc = lambda e: tuple(getattr(e, key) for key in sort)
                else:
                    raise TypeError("When an iterable of sort keys are given, all must be strings")
            
            # sorting is not at all intelligent or particularly efficeint. TODO: any way to sort while traversing without knowing contents of subdirs?
            matches = self._match(self.base, self.parts, params)
            matches = sorted(matches, key= sortFunc)

        else:
            matches = self._match(self.base, self.parts, params)

        return Subset(matches)

    def _match(self, baseEntry, partsPatterns, params):
        # TODO: what about multiple leaf patterns?
        # TODO: error handling
        # TODO eventually: before anything else, check baseEntry for a definition file and potentially load a new partsPatterns from it
        pattern, rest = partsPatterns[0], partsPatterns[1:]

        if pattern.isLiteral:
            here = baseEntry._join(pattern.value, {})
            if here._exists():
                if rest == []:
                    yield here
                else:
                    for entry in self._match(here, rest, params):
                        yield entry

        else:
            for name in baseEntry._listdir():
                fieldVals = pattern.matches(name, **params)
                if fieldVals is not None:
                    here = baseEntry._join(name, fieldVals)
                    if rest == []:
                        yield here
                    else:
                        for entry in self._match(here, rest, params):
                            yield entry

    def __repr__(self):
        return "Endpoint('{}'), fields: {}".format([part.value for part in self.parts],
                                                   ", ".join(self.fields))

class Subset(object):
    # A chainable iterator (that probably needs a different name)
    # Allows basic vectorized operations on an iterable

    # head()
    # tail()
    # slice()
    # filter()
    # map() -> combine()
    # attrs for each field in endpoint give subsets that iterate through just that field, not whole Entry
    # all of which return a new subset with a modified parser chain
    # + to union
    # TODO: print / repr

    def __init__(self, iterable):
        self._iter = iter(iterable)

    def chain(self, func):
        # TODO: private? or classmethod?
        return Subset( func(self._iter) )

    def __getattr__(self, attr):
        try:
            return self.__dict__[attr]
        except KeyError:
            return self.chain( functools.partial(map, operator.attrgetter(attr)) )

    def __iter__(self):
        return self._iter
        # return functools.reduce(lambda chain, func: func(chain), self._operations, self._entries)

    def __add__(self, subset):
        if not isinstance(subset, Subset):
            raise TypeError("Expected another Subset, instead got '{}'".format(type(subset).__name__))
        return Subset( itertools.chain(self._iter, subset._iter) )

    def head(self, n= 5):
        def do_head(iterable):
            return itertools.islice(iterable, n)
        return self.chain(do_head)

    def tail(self, n= 5):
        def do_tail(iterable):
            return itertools.islice(iterable, -n, -1)
        return self.chain(do_tail)

    def slice(self, *args):
        # slice([start,] stop [, step])
        if len(args) == 0:
            raise TypeError("slice expected at least 1 argument, got 0")
        elif len(args) > 3:
            raise TypeError("slice expected at most 3 argument, got {}".format(len(args)))
        else:
            def do_slice(iterable):
                return itertools.islice(iterable, *args)

            return self.chain(do_slice)

    def filter(self, predicate):
        return self.chain( functools.partial(filter, predicate) )

    def map(self, func):
        return self.chain( functools.partial(map, func) )

    def combine(self, func):
        return func(self._iter)


class Pattern(object):

    # value: str
    # regex: compiled regex
    # __init__ compiles regex
    # fields: readonly tuple of names of fields in pattern
    # matches(string, **kwargs) : returns dict of field values matched in string, as restricted by **kwargs, or None if pattern not matched
    # isLiteral: bool

    # TODO: should pattern be explicitly full-line, ie insert ^ and $ ?
    def __init__(self, pattern):
        self.value = pattern
        try:
            self.regex = re.compile(pattern)
        except re.error as e:
            raise ValueError("Regex syntax error in pattern '{}': {}".format(pattern, e.args[0]))
        self.fields = tuple(self.regex.groupindex.keys())
        self.isLiteral = not any(char in pattern for char in r"\\*+?|[](){}^$")  # hack-y way to check if pattern is a literal string, not a regex

    def matches(self, string, **params):
        if self.isLiteral:
            return {} if self.value == string else None
        else:
            match = self.regex.match(string)
            if match is not None:
                groups = match.groupdict()
                for field, restriction in iteritems(params):
                    if field in groups:
                        value = groups[field]

                        ## TODO:
                        ## - automatic conversion? (numeric, datetime)
                        ## - binary arrays?
                        ## - indexed pandas frames

                        if restriction is None:
                            continue

                        ## Singletons
                        if isinstance(restriction, str):
                            if value == restriction:
                                continue
                            else:
                                return None

                        elif isinstance(restriction, numbers.Number) and not isinstance(restriction, bool):
                            try:
                                if float(value) == restriction:
                                    continue
                                else:
                                    return None
                            except ValueError:
                                return None

                        ## Dict-like exclusion: {value: False}
                        try:
                            restrictionValue = restriction[value]
                            
                            if not restrictionValue:
                                return None
                            else:
                                raise TypeError("A dict excluding specific values from a field must only contain False; instead, got '{}' for key '{}' in field '{}'".format(restrictionValue, value, field))
                                
                        except KeyError:
                            # Values not explicitly excluded are considered a match
                            continue
                        except TypeError:
                            pass

                        ## Iterable
                        try:
                            present = False
                            for restrictionValue in restriction:
                                if restrictionValue == value:
                                    present = True
                                    continue
                            if not present:
                                return None
                            else:
                                continue
                        except TypeError:
                            pass

                        ## Callable
                        # TODO: check for __call__ instead, and catch errors from within function nicely
                        try:
                            if restriction(value):
                                continue
                            else:
                                return None
                        except TypeError:
                            pass

                        raise TypeError("Unsupported type {} from parameter '{}'".format(type(restriction), field))

                    # Skip raising error for invalid fields, since matches is typically called with all params for whole endpoint,
                    # which don't all apply to just this one pattern

                    # else:
                    #   raise TypeError("'{}' is an invalid keyword argument. Fields in the pattern '{}' are: {}".format(field, self.value, self.fields))
            
                return groups
            else:
                return None


class Entry(object):

    # path: str
    # fields: {}
    # attrs for each field
    # ._join(path, dict of fields) -> new Entry with path joined to this and fields extended
    # ._exists()
    # ._listdir()
    # TODO: dict-like?
    # TODO: open()
    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        return open(self.path, mode= mode, buffering= buffering, encoding= encoding, errors= errors, newline= newline)

    def __init__(self, path, fields= {}):
        self.__dict__["path"] = path
        self.__dict__["fields"] = fields

    def _join(self, path, newFields):
        newPath = os.path.join(self.path, path)
        newEntry = Entry(newPath, dict(self.fields))
        newEntry.fields.update(newFields)
        return newEntry

    def _exists(self):
        return os.path.exists(self.path)
    def _listdir(self):
        return os.listdir(self.path)

    def __getattr__(self, attr):
        try:
            return self.fields[attr]
        except KeyError:
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError("Entry instance has no field or attribute '{}'".format(attr))

    def __setattr__(self, attr, val):
        if attr in self.__dict__:
            self.__dict__[attr] = val
        else:
            self.fields[attr] = val

    def __getitem__(self, item):
        try:
            return self.fields[item]
        except KeyError:
            if item == "path":
                return self.path
            else:
                raise KeyError("Entry has no field '{}'".format(item))

    def __setitem__(self, item, val):
        self.fields[item] = val

    def __dir__(self):
        # TODO: infinite recursion!!
        return self.fields.keys() + dir(self)

    def __eq__(self, other):
        if isinstance(other, Entry):
            return self.path == other.path
        elif isinstance(other, str):
            return other == self.path
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, Entry):
            return self.path < other.path
        elif isinstance(other, str):
            return other < self.path
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, Entry):
            return self.path > other.path
        elif isinstance(other, str):
            return other > self.path
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, Entry):
            return self.path >= other.path
        elif isinstance(other, str):
            return other >= self.path
        else:
            return False

    def __le__(self, other):
        if isinstance(other, Entry):
            return self.path <= other.path
        elif isinstance(other, str):
            return other <= self.path
        else:
            return False

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return self.path

    def __repr__(self):
        return "Entry('{}', fields= {})".format(self.path, self.fields)

