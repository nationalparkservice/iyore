# Python 2 and 3 cross-compatibility:
from __future__ import print_function, division, unicode_literals, absolute_import
from builtins import (bytes, str, int, dict, object, range, map, filter, zip, round, pow, open)
from future.utils import (iteritems, itervalues)
from past.builtins import basestring

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

## [x] Multiple sets of parameters (so can specify site+year, site+year)---a list of parameter dicts
## [ ] Combining datasets/endpoints
## [x] 2-3 compatibility
## [ ] Error handling
## [ ] Docstrings & cleanup
## [x] Unit tests? (both 2 and 3)
## [x] Hierarchy file
## [ ] Block reserved terms in structure file
## [ ] Conversion for numerics
## [ ] Smarter finding of structure file
## [ ] Further optimize Pattern.fill() (or .match()) to detect when regex only contains escaped chars, and jump directly to path without searching

## Big leaps:

## [ ] User-friendly pattern syntax
## [-] Composable query syntax??
## [-] Parsers

structureFileName = ".structure.txt"

class Dataset(object):
    def __init__(self, path, structure= None):
        if structure is None:
            # TODO: smarter finding structure file
            if os.path.isdir(path):
                path = os.path.join(path, structureFileName)

            self.base = Entry(os.path.dirname(path))
            self.endpoints = self._parseStructureFile(structfilePath= path)
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

    def __getitem__(self, item):
        try:
            return self.endpoints[item]
        except KeyError:
            raise KeyError("Dataset instance has no endpoint '{}'".format(item))

    def __dir__(self):
        mydir = dir(self.__class__)
        mydir.extend(self.endpoints.keys())
        return mydir

    def __repr__(self):
        return 'Dataset("{}")\nEndpoints:\n{}'.format(self.base.path, "\n".join("  * {} - fields: {}".format(name, ", ".join(sorted(endpoint.fields))) for name, endpoint in sorted(iteritems(self.endpoints))))

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
            # TODO: more descriptive errors?
            # TODO: show neighboring lines and highlight error
            # TODO: ensure endpoint names are valid Python identifiers, and don't conflict with iyore terms (path)

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

                if content[0] == "#":
                    # allow comments on their own line
                    # TODO: allow inline comments
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
        self.parts = parts if all(isinstance(part, Pattern) for part in parts) else list(map(Pattern, parts))
        self.fields = set.union( *(set(part.fields) for part in self.parts) )

    def __call__(self, items= None, sort= None, **params):
        literal_fill_fields = {}
        for param, value in iteritems(params):
            if param not in self.fields:
                raise TypeError('"{}" is not a field in this Endpoint'.format(param))
            else:
                if Pattern.isLiteral(value):
                    literal_fill_fields[param] = value

        if len(literal_fill_fields) > 0:
            # for fields where a literal (singleton string) restriction is given, optimize search process by replacing the regex with the literal value
            parts = [ part.fill(literal_fill_fields, raise_on_nonexistant_fields= False) for part in self.parts ]
            # parts = [ part.fill({field: val for field, val in iteritems(literal_fill_fields) if field in part.fields}) for part in self.parts ]
        else:
            parts = self.parts

        if items is not None:
            if len(params) > 0:

                def items_plus_params():
                    try:
                        for item_dict in items:
                            try:
                                extended = item_dict.copy()
                                extended.update(params)
                            except TypeError:
                                raise TypeError("'items' must be an iterable of dict-like objects, instead got iterable containing a non-dict-like type {}".format(type(item_dict)))
                            yield extended
                    except TypeError:
                        raise TypeError("'items' must be an iterable of dict-like objects, instead got non-iterable type {}".format(type(items)))


                matches = self._select(items_plus_params())
            else:
                matches = self._select(items)

        else:
            matches = self._match(self.base, parts, params)
            
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
            matches = sorted(matches, key= sortFunc)

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

    def _select(self, items):
        # items: list of parameter dictionaries
        # i.e. list of dicts, where each dict is equivalent to kwards you'd give to __call__
        # effectively, parameters inside each dict are ANDed together, then all those parameter sets are ORed
        try:
            iter(items)
        except TypeError:
            raise TypeError("'items' must be an iterable of dict-like objects, instead got non-iterable type {}".format(type(items)))

        for item_dict in items:
            try:
                # TODO: attempt to fast-path the case of all dicts in iterable giving literal values for the same set of fields
                # by skipping the isLiteral check and using the previous dict's literal_fill_fields keys
                literal_fill_fields = { field: value for field, value in iteritems(item_dict) if Pattern.isLiteral(value) }
            except TypeError:
                raise TypeError("'items' must be an iterable of dict-like objects, instead got iterable containing a non-dict-like type {}".format(type(item_dict)))
            
            parts = [ part.fill(literal_fill_fields, raise_on_nonexistant_fields= False) for part in self.parts ]
            for entry in self._match(self.base, parts, item_dict):
                yield entry

    def info(self, nExamples= 2):
        """
        Prints the number of distinct values for each field, some examples of those values,
        and the total number of Entries in the Endpoint.

        Parameters
        ----------

        nExamples : int or None, default 2

            Number of example values to show for each field. Use 0 or None to not print examples.
        """
        # TODO: tests

        field_vals = {}
        entry_count = 0
        for entry in self():
            entry_count += 1
            for field, val in iteritems(entry):
                try:
                    field_vals[field].add(val)
                except KeyError:
                    field_vals[field] = {val}
        
        field_counts = { field: len(vals) for field, vals in iteritems(field_vals) }
        if nExamples:
            examples = {}
            for field, vals in iteritems(field_vals):
                exs = []
                for i in range(nExamples):
                    try:
                        exs.append(vals.pop())
                    except KeyError:
                        break
                examples[field] = exs
            
        print("Fields:")
        for field in sorted(self.fields):
            if nExamples:
                exs = ", ".join([ '"'+ex+'"' for ex in examples[field] ])
                print('    {}: {} value{}, ex. {}'.format(field, field_counts[field], "s" if field_counts[field] > 1 else "", exs))
            else:
                print('    {}: {} value{}'.format(field, field_counts[field], "s" if field_counts[field] > 1 else ""))

        print("")
        print("{} Entries".format(entry_count))

    def values(self, field):
        """
        Return a set of all values the given field takes on in this Endpoint.
        """
        return { entry[field] for entry in self() }

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
    def __init__(self, pattern, literals= {}):
        self.value = pattern
        try:
            self.regex = re.compile(pattern)
        except re.error as e:
            raise ValueError("Regex syntax error in pattern '{}': {}".format(pattern, e.args[0]))
        self.literals = literals
        self.fields = set(self.regex.groupindex.keys())
        self.fields.update(literals.keys())
        self.isLiteral = Pattern.isLiteral(pattern)
        self.pattern_parts = self.named_group_positions = self.compiled_groups = None

    def fill(self, fields, raise_on_nonexistant_fields= True):
        if self.isLiteral:
            return self
        if self.pattern_parts is None:
            self.pattern_parts, self.named_group_positions = Pattern.split_named_groups(self.value)
            # compile each capturing group on its own to use for validating literal values:            
            # extract matched pattern from each named group, wrap in ^ and $ (to make it a full-string match, as re.fullmatch is not in py2)
            self.compiled_groups = { field: re.compile("^{}$".format( self.pattern_parts[pos][ len("(?P<>")+len(field):-1 ] )) for field, pos in iteritems(self.named_group_positions) }

        new_parts = list(self.pattern_parts)
        for field, literal_value in iteritems(fields):
            # TODO: convert literal_value to str if necessary---any way to intelligently format number to format of regex??
            try:
                field_regex = self.compiled_groups[ field ]
                field_index = self.named_group_positions[ field ]
            except KeyError:
                if raise_on_nonexistant_fields:
                    raise ValueError('The field "{}" does not exist in the pattern "{}"'.format(field, self.value))
                else:
                    continue
            # ensure the given literal value actually matches its field's pattern
            if not field_regex.match(literal_value):
                raise ValueError('"{}" does not match the pattern for the field "{}" (must match the regular expression "{}")'.format(literal_value, field, field_regex.pattern))
            
            new_parts[field_index] = Pattern.escape(literal_value)

        return Pattern("".join(new_parts), literals= fields)

    @staticmethod
    def isLiteral(pattern):
        return isinstance(pattern, basestring) and not any(char in pattern for char in r"\\.*+?|[](){}^$")  # hack-y way to check if pattern is a literal string, not a regex

    @staticmethod
    def escape(literal):
        # a less-agressive version of re.escape that only escapes known regex special characters
        # converts a literal string into a regular expression that matches only that string
        return re.sub(r"[.\\+*?^$\[\]{}()|/]", r"\\\g<0>", literal)

    @staticmethod
    def isLiteralRegex(regex):
        # whether the given regular expression contains only literals and escaped special characters, i.e. has only 1 possible match
        # assumes input is a valid regex
        return re.search(r"(?<!\\)[.+*?^$\[\]{}()|/]", regex) is None and re.search(r"(?<!\\)\\([AbBdDsSwWZ]|\d+)", regex) is None

    @staticmethod
    def unescape(regex):
        # de-escape a regular expression containing only literals and escaped special characters into the literal string it matches
        # assumes input is a valid regex
        if not Pattern.isLiteralRegex(regex):
            raise ValueError("Only literal regular expressions should be unescaped, this one contains unescaped special characters: {}".format(regex))
        # return re.sub(r"(?<!\\)\\(?!\\)", "", regex).replace("\\\\", "\\")
        return re.sub(r"(?<!\\)\\", "", regex).replace("\\\\", "\\")

    @staticmethod
    def split_named_groups(regex_string):
        # returns tuple of (regex pattern parts, split into list by named group; dict of { group name: index in that list } )
        # assumes regex_string is valid regex, and all parens are matched!
        named_groups = [(match.group(1), match.start()) for match in re.finditer(r"\(\?P<(\w+)>", regex_string)]

        if len(named_groups) == 0:
            return ([regex_string], {})

        pattern_parts = []
        named_group_positions = {}

        str_list = list(regex_string)  # __getitem__ access is slightly faster from a list than a string
        i = 0
        for group_name, group_start in named_groups:
            # add any non-grouped regex between the end of the last group and the start of this one
            if group_start > i:
                pattern_parts.append( regex_string[i:group_start] )
            if group_start < i:
                raise NotImplementedError("iyore does not currently handle filling literals into nested named groups")
            i = group_start
            paren_depth = 0
            have_backslash = False
            try:
                while True:
                    if not have_backslash:
                        char = str_list[i]
                        if char == "(":
                            paren_depth += 1
                        elif char == ")":
                            paren_depth -= 1
                        elif char == "\\":
                            have_backslash = True
                        if paren_depth == 0:
                            i = i+1
                            break
                    else:
                        have_backslash = False
                    i += 1
            except IndexError:
                raise ValueError("The string '{}' seems to be an improperly-formatted regex, with mismatched parens".format(regex_string))
                
            pattern_parts.append( regex_string[group_start:i] )
            named_group_positions[group_name] = len(pattern_parts)-1

        if i < len(str_list):
            pattern_parts.append( regex_string[i:len(str_list)] )

        return pattern_parts, named_group_positions


    def matches(self, string, **params):
        if self.isLiteral:
            return self.literals if self.value == string else None
        else:
            match = self.regex.match(string)
            if match is not None:
                groups = match.groupdict()
                groups.update(self.literals)
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
                        if isinstance(restriction, basestring):
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

    def __repr__(self):
        return 'Pattern("{}")'.format(self.value)


class Entry(object):

    # path: str
    # fields: {}
    # attrs for each field
    # ._join(path, dict of fields) -> new Entry with path joined to this and fields extended
    # ._exists()
    # ._listdir()

    # TODO: make Entry a fully-compatible Mapping type to allow ** expansion

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

    def iteritems(self):
        return iteritems(self.fields)

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
        mydir = dir(self.__class__)
        mydir.extend(self.fields.keys())
        mydir.append("path")
        return mydir

    def __eq__(self, other):
        if isinstance(other, Entry):
            return self.path == other.path
        elif isinstance(other, basestring):
            return other == self.path
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, Entry):
            return self.path < other.path
        elif isinstance(other, basestring):
            return other < self.path
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, Entry):
            return self.path > other.path
        elif isinstance(other, basestring):
            return other > self.path
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, Entry):
            return self.path >= other.path
        elif isinstance(other, basestring):
            return other >= self.path
        else:
            return False

    def __le__(self, other):
        if isinstance(other, Entry):
            return self.path <= other.path
        elif isinstance(other, basestring):
            return other <= self.path
        else:
            return False

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return self.path

    def __repr__(self):
        return "Entry('{}', fields= {})".format(self.path, self.fields)

