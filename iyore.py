# Python 2 and 3 cross-compatibility:
from __future__ import print_function, division, unicode_literals, absolute_import
from builtins import (bytes, str, int, dict, object, range, map, filter, zip, round, pow, open)
from future.utils import (iteritems, itervalues)

import re
import os
import sys
import numbers
import functools
import inspect
import traceback

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
    # TODO: dict-like?
    def __init__(self, path):
        # TODO: smarter finding structure file
        dirname, basename = os.path.split(path)
        if basename == "":
            basename = structureFileName
        self.base = Entry(dirname)
        self.endpoints = self._parseStructureFile(os.path.join(dirname, basename))

    def __getattr__(self, attr):
        try:
            return self.endpoints[attr]
        except KeyError:
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError("Dataset instance has no endpoint or attribute '{}'".format(attr))

    def __dir__(self):
        return self.endpoints.keys() + dir(self)

    def __repr__(self):
        return 'Dataset("{}")\nEndpoints:\n{}'.format(self.base.path, "\n".join("  - {}: {}".format(name, repr(endpoint)) for name, endpoint in iteritems(self.endpoints)))

    def _parseStructureFile(self, structfilePath):
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
        with open(structfilePath, encoding= "utf-8") as f:
            # TODO: comments
            # TODO: more descriptive errors?
            # TODO: show neighboring lines and highlight error

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

    def __call__(self, **params):
        return self._match(self.base, self.parts, params)

    def _match(self, baseEntry, partsPatterns, params):
        # TODO: what about multiple leaf patterns?
        # TODO: error handling
        # TODO eventually: before anything else, check baseEntry for a definition file and potentially load a new partsPatterns from it
        # TODO: sortedness?
        pattern, rest = partsPatterns[0], partsPatterns[1:]

        if pattern.isLiteral:
            here = baseEntry._join(pattern.value, {})
            if here._exists():
                if rest == []:
                    return [here]
                else:
                    return self._match(here, rest, params)
            else:
                return []

        else:
            matchingEntries = []
            for name in baseEntry._listdir():
                fieldVals = pattern.matches(name, **params)
                if fieldVals is not None:
                    matchingEntries.append( baseEntry._join(name, fieldVals) )

            if rest == []:
                return matchingEntries
            else:
                subsequentMatches = []
                for entry in matchingEntries:
                    subsequentMatches.extend( self._match(entry, rest, params) )
                return subsequentMatches

    def __repr__(self):
        return "Endpoint('{}'), fields: {}".format("/".join(part.value for part in self.parts),
                                                   ", ".join(self.fields))

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
    def __init__(self, path, fields= {}):
        self.path = path
        self.fields = fields

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

    def __dir__(self):
        return self.fields.keys() + dir(self)

    def __eq__(self, other):
        if isinstance(other, Entry):
            return self.path == other.path
        elif isinstance(other, str):
            return other == self.path
        else:
            return False

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return self.path

    def __repr__(self):
        return "Entry('{}', fields= {})".format(self.path, self.fields)

