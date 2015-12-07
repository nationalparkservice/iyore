# iyore

Easing the thistly problem of accessing data stored in arbitrary, consistent directory structures.
![Eeyore consumes a thistle](https://s-media-cache-ak0.pinimg.com/236x/5e/57/a4/5e57a4b4ba63c43f5cd4c24509e1231e.jpg)

--------------------------------------------------------------------------

The most common database is not MySQL, Access, or Mongo: it's the filesystem.
It's familiar, user-friendly, and requires zero installation. Vast quantities of
data of any kind---particularly from less-technical users---are often stored in
nested folders. There's usually a pattern to the structure and the names of the
files and folders, but writing code to traverse every new directory structure
you come across gets tedious.

iyore is pronounced "EYE-or", like Eeyore, and I/O, but eaten by a Python. If
you write a file of regular expressions describing each level of your directory
structure, it gives you iterators over each distinct kind of data it contains,
plus lets you subset the data based on patterns in the file and folder names.

Say you have a folder structure like this:
```
Winnie The Pooh Data
    \- Chapters
        |- 01 In Which We Are Introduced
        |     |- pooh-quotes.txt
        |     \- first_page.png
        |- 02 In Which Pooh Goes Visiting and Gets into a Tight Place
        |     |- pooh-quotes.txt
        |     |- piglet-quotes.txt
        |     |- tigger-quotes.txt
        |     |- first_page.png
        |     \- stuck.png
        |- 03 In Which Pooh and Piglet Go Hunting and Nearly Catch a Woozle
        |     |- pooh-quotes.txt
        |     |- piglet-quotes.txt
        |     |- first_page.png
        |     \- woozle.png
                                         . . .
        |- 08 In Which Christopher Robin Leads an Expotition to the North Pole
        |     |- pooh-quotes.txt
        |     |- first_page.png
        |     \- over-the-river.png
        |- 09 In Which Piglet is Entirely Surrounded by Water
        |     |- piglet-quotes.txt
        |     |- first_page.png
        |     \- bucket.png
        \- 10 In Which Christopher Robin Gives Pooh a Party and We Say Goodbye
              |- pooh-quotes.txt
              |- piglet-quotes.txt
              |- tigger-quotes.txt
              \- first_page.png
```

The relevant data are quotes (by a certain character) and images from the
chapter. The names of the files and folders follow consistent patterns, but also
contain essential metadata (which character the quotes are for, the chapter
number, etc.).

To easily access this data with iyore, we'd first write a structure file describing the dataset:
```
Chapters
    (?P<chap_num>\d\d) (?P<chap_title>.+)
        quotes: (?P<character>\w+)-quotes.txt
        images: (?P<title>.*).png
```

Each line contains a regular expression that matches a file or folder name.
Notice the named capturing groups, like `(?P<chap_num>\d\d) (?P<chap_title>.+)`.
Labeling these fields in the name will allow us to subselect data from only
certain `chap_num`s or `chap_title`s. The indentation describes the folder
structure: each subfolder or file is indented one level further than its parent.
(Like Python, you can use tabs or spaces, so long as you're consistent with the
indentation character and width.)

The two kinds of data we actually want to access are `quotes` and `images`. We
refer to these as `Endpoint`s, which are specified by prefixing the regex
pattern for a file or folder with `<endpoint_name>` and a colon. (Note that
`Endpoint`s could be folders as well as files, and there can be more folders or
`Endpoint`s within them.)

This structure file should be saved in the root directory of your dataset---in
this case, as `Winnie The Pooh Data/.structure.txt`.

------------------------------------------------------------------

Now, to start accessing your data in Python:

```python
>>> import iyore
>>> ds = iyore.Dataset("~/fun/Winnie The Pooh Data/.structure.txt")
>>> ds
Dataset("~/fun/Winnie The Pooh Data/.structure.txt")
Endpoints:
  - quotes: Endpoint(['Chapters','(?P<chap_num>\\d\\d) (?P<chap_title>.+)','(?P<character>\\w+)-quotes.txt)']), fields: chap_num, chap_title, character
  - images: Endpoint(['Chapters','(?P<chap_num>\\d\\d) (?P<chap_title>.+)','(?P<title>.*).png']), fields: chap_num, chap_title, title
```

A `Dataset` is created with the path to a structure file, and just has
attributes for each of the `Endpoint`s in that structure file.

Let's look at all of the quotes in this dataset:

```python
>>> for entry in ds.quotes():
...     print(entry.path, ':::', entry.fields)
...
Chapters/01 In Which We Are Introduced/pooh-quotes.txt ::: {'chap_num': '01', 'chap_title': 'In Which We Are Introduced', 'character': 'pooh'}
Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/pooh-quotes.txt ::: {'chap_num': '02', 'chap_title': 'In Which Pooh Goes Visiting and Gets into a Tight Place', 'character': 'pooh'}
Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/piglet-quotes.txt ::: {'chap_num': '02', 'chap_title': 'In Which Pooh Goes Visiting and Gets into a Tight Place', 'character': 'piglet'}
Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/tigger-quotes.txt ::: {'chap_num': '02', 'chap_title': 'In Which Pooh Goes Visiting and Gets into a Tight Place', 'character': 'tigger'}
    ...
```

`ds.quotes is an Endpoint: one kind of data you want. Calling ds.quotes()
`returns an iterator through all quotes Entrys in the dataset.

An `Entry` (as in, a directory entry) is a single, concrete file or folder in a
dataset. Besides the `path` attribute, an `Entry` also has a dictionary of
`fields`. This contains the values matched by all the named capturing groups.
For convenience, you can also access particular fields using dot notation:

```python
>>> for entry in ds.quotes():
...     print(entry.chap_num, entry.character)
...
01 pooh
02 pooh
02 piglet
02 tigger
    ...
```

From here, you can use the `Entry`s for data processing:

```python
>>> for entry in ds.quotes():
...     quotes = open(str(entry)).readlines()   # note: str(entry) == entry.path
...     do_complex_sentiment_analysis_algorithm(quotes)
```

What if you don't want all quotes, but just quotes from Piglet from the first three chapters?

When calling an `Endpoint` to iterate through it, you can give keyword arguments
to restrict the values allowed in each field:

```python
>>> for entry in ds.quotes(character= "piglet", chap_num= ["01", "02", "03"]):
...     print(entry.chap_num, entry.character, ":", entry.path)
...
02 piglet : Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/piglet-quotes.txt
03 piglet : Chapters/03 In Which Pooh and Piglet Go Hunting and Nearly Catch a Woozle/piglet-quotes.txt
```

Here are the different types of arguments you can give to restrict the values for a field:

 Argument  |                                       Meaning
---------- | ---------------------------------------------------------------------------------------------
 `str`     |  value must equal this string
 number    |  value, parsed as a float, must equal this number
 `dict`    |  keys are values to *exclude*, must all map to `False`. Any values not in dict are accepted
 iterable  |  value must be in iterable
 callable  |  `callable(value)` must return True

------------

### Logistics

iyore is Python 2 and 3 cross-compatible, and depends only on the `future`
package (which allows the cross-compatibility)

To install iyore, clone this repository, `cd` into it, then run `pip install .`

If you want to run the tests (which are probably not complete), run `python
setup.py test`, which will also install `pytest` if you don't already have it.

Though all functionality should work, this library is still in its infancy and
subject to significant change. Plus, many planned features are still currently
missing.
