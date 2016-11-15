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

## Structuring

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

To easily access this data with iyore, we'd first write a **structure file** describing the dataset:
```
Chapters
    (?P<chap_num>\d\d) (?P<chap_title>.+)
        quotes: (?P<character>\w+)-quotes.txt
        images: (?P<title>.*).png
```

Each line contains a regular expression that matches a file or folder name.
Notice the named capturing groups, like `(?P<chap_num>\d\d) (?P<chap_title>.+)`.
Labeling these **fields** in the name will allow us to subselect data from only
certain `chap_num`s or `chap_title`s. The indentation describes the folder
structure: each subfolder or file is indented one level further than its parent.
(Like Python, you can use tabs or spaces, so long as you're consistent with the
indentation character and width.)

The two kinds of data we actually want to access are `quotes` and `images`. We
refer to these as **`Endpoint`**s, which are specified by prefixing the regex
pattern for a file or folder with `<endpoint_name>` and a colon. (Note that
`Endpoint`s could be folders as well as files, and there can be more folders or
`Endpoint`s within them.)

This structure file should be saved in the root directory of your dataset---in
this case, as `Winnie The Pooh Data/.structure.txt`.

## Iterating

Now, to start accessing your data in Python:

```pycon
>>> import iyore
>>> ds = iyore.Dataset("~/fun/Winnie The Pooh Data/.structure.txt")
>>> ds
Dataset("~/fun/Winnie The Pooh Data/.structure.txt")
Endpoints:
  - quotes: Endpoint(['Chapters','(?P<chap_num>\\d\\d) (?P<chap_title>.+)','(?P<character>\\w+)-quotes.txt)']), fields: chap_num, chap_title, character
  - images: Endpoint(['Chapters','(?P<chap_num>\\d\\d) (?P<chap_title>.+)','(?P<title>.*).png']), fields: chap_num, chap_title, title
```

A **`Dataset`** is created with the path to a structure file, and just has
attributes for each of the `Endpoint`s in that structure file.

Let's look at all of the quotes in this dataset:

```pycon
>>> for entry in ds.quotes():
...     print(entry.path, ':::', entry.fields)
...
Chapters/01 In Which We Are Introduced/pooh-quotes.txt ::: {'chap_num': '01', 'chap_title': 'In Which We Are Introduced', 'character': 'pooh'}
Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/pooh-quotes.txt ::: {'chap_num': '02', 'chap_title': 'In Which Pooh Goes Visiting and Gets into a Tight Place', 'character': 'pooh'}
Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/piglet-quotes.txt ::: {'chap_num': '02', 'chap_title': 'In Which Pooh Goes Visiting and Gets into a Tight Place', 'character': 'piglet'}
Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/tigger-quotes.txt ::: {'chap_num': '02', 'chap_title': 'In Which Pooh Goes Visiting and Gets into a Tight Place', 'character': 'tigger'}
    ...
```

`ds.quotes` is an Endpoint: one kind of data you want. Calling `ds.quotes()`
returns an iterator through all quotes Entrys in the dataset.

An **`Entry`** (as in, a directory entry) is a single, concrete file or folder in a
dataset. Besides the `path` attribute, an `Entry` also has a dictionary of
**`fields`**. This contains the values matched by all the named capturing groups.
For convenience, you can also access particular fields using dot notation:

```pycon
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

```pycon
>>> for entry in ds.quotes():
...     quotes = open(str(entry)).readlines()   # note: str(entry) == entry.path
...     do_complex_sentiment_analysis_algorithm(quotes)
```

## Filtering

What if you don't want all quotes, but just quotes from Piglet from the first three chapters?

When calling an `Endpoint` to iterate through it, you can give keyword arguments
to restrict the values allowed in each field:

```pycon
>>> for entry in ds.quotes(character= "piglet", chap_num= ["01", "02", "03"]):
...     print(entry.chap_num, entry.character, ":", entry.path)
...
02 piglet : Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/piglet-quotes.txt
03 piglet : Chapters/03 In Which Pooh and Piglet Go Hunting and Nearly Catch a Woozle/piglet-quotes.txt
```

Here are the different types of arguments you can give to restrict the values for a field.
These are referred to as **filters**:

 Argument          |                                   Meaning, for each Entry
------------------ | ---------------------------------------------------------------------------------------------------
 `str`             |  field's value must equal this string
 number            |  field's value, parsed as a float, must equal this number
 `dict`            |  keys are field values to *exclude*, must all map to `False`. Any values not in dict are accepted.
 iterable of `str` |  field's value must be in iterable
 callable          |  `callable(field's value)` must return True

## Sorting

To access your data in a particular order, use the `sort` keyword argument.

Argument type           |                     Meaning for `sort`
----------------------- | ---------------------------------------------------------------------------------------
field name (`str`)      | sort by that field
iterable of field names | sort by those fields: first field 1, then within same values for field 1, field 2, etc.
function                | key function which, given an Entry, returns a value to represent that Entry when sorting

For example, to iterate through all the quotes, but ordered (alphabetically) by character:

```pycon
>>> for entry in ds.quotes(sort= "character"):
...     print(entry.character, ":", entry.chap_title)
...
piglet : In Which Pooh Goes Visiting and Gets into a Tight Place
piglet : In Which Pooh and Piglet Go Hunting and Nearly Catch a Woozle
piglet : In Which Piglet is Entirely Surrounded by Water
piglet : In Which Christopher Robin Gives Pooh a Party and We Say Goodbye
pooh : In Which We Are Introduced
pooh : In Which Pooh Goes Visiting and Gets into a Tight Place
pooh : In Which Pooh and Piglet Go Hunting and Nearly Catch a Woozle
    ...
```

Unless you specify an ordering with `sort`, don't expect your results to always be alphabetical, or to appear in the
same order they do in your file browser.

## Accessing specific entries

Occasionally, you already know exactly which Entries you want.

Say you need Pooh quotes from Chapter 1, Piglet quotes from Chapter 2, and all quotes from Chapter 10.

`ds.quotes(character= ["pooh", "piglet"], chap_num= ["01", "02", "10"])` is *not* specific enough here:
that will give you quotes that match any combination of the specified characters and chapter numbers. For example, you'll
also get Pooh quotes from Chapter 2, along with just the Piglet quotes you wanted.

You *could* phrase this as four separate queries:

```pycon
>>> ds.quotes(character= "pooh", chap_num= 1)
>>> ds.quotes(character= "piglet", chap_num= 2)
>>> ds.quotes(chap_num= 10)
```

but it's easier to use the `items` keyword argument, which takes a list of `dict`s,
where each `dict` contains the keyword arguments you'd use for each of those queries.

```pycon
>>> specific_quotes = [
...     {
...         "character": "Pooh",
...         "chap_num": 1
...     },
...     {
...         "character": "Piglet",
...         "chap_num": 2
...     },
...     {
...         "chap_num": 10
...     }
... ]
>>> for entry in ds.quotes(items= specific_quotes):
...     print(entry.chap_num, entry.character, ":", entry.path)
...
01 pooh : Chapters/01 In Which We Are Introduced/pooh-quotes.txt
02 piglet : Chapters/02 In Which Pooh Goes Visiting and Gets into a Tight Place/piglet-quotes.txt
10 pooh : Chapters/10 In Which Christopher Robin Gives Pooh a Party and We Say Goodbye/pooh-quotes.txt
10 piglet : Chapters/10 In Which Christopher Robin Gives Pooh a Party and We Say Goodbye/piglet-quotes.txt
10 tigger : Chapters/10 In Which Christopher Robin Gives Pooh a Party and We Say Goodbye/tigger-quotes.txt
```

## Exploring

To quickly find out (or remind yourself) what sort of data you have, use the `info()` method of an Endpoint:

```pycon
>>> ds.quotes.info()
Fields:
    character: 3 values, ex. "pooh", "piglet"
    chap_num: 10 values, ex. "01", "08"
    chap_title: 10 values, ex. "In Which We Are Introduced", "In Which Piglet is Entirely Surrounded by Water"

21 Entries
```

Similarly, to get all the distinct values for a field, use the `Endpoint.values(field)` method, which returns a `set`:

```pycon
>>> ds.quotes.values("character")
{"pooh", "piglet", "tigger", "kanga", "owl", "roo", "christopher"}
>>> ds.quotes.values("chap_num")
{"01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}
```

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
 
### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.