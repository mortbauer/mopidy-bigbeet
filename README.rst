****************************
Mopidy-Bigbeet
****************************

.. image:: https://img.shields.io/pypi/v/Mopidy-Bigbeet.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Bigbeet/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/travis/rawdlite/mopidy-bigbeet/master.svg?style=flat
    :target: https://travis-ci.org/rawdlite/mopidy-bigbeet
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/rawdlite/mopidy-bigbeet/master.svg?style=flat
   :target: https://coveralls.io/r/rawdlite/mopidy-bigbeet
   :alt: Test coverage

Mopidy extension to manage big local music collections.


Installation
============

Install by running::

    pip install Mopidy-Bigbeet

Or, if available, install the Debian/Ubuntu package from `apt.mopidy.com
<http://apt.mopidy.com/>`_.


Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-Bigbeet to your Mopidy configuration file::

    [bigbeet]
    enabled = true
    beetslibrary = /data/music/beetslibrary.blb
    bb_data_dir = /data/music/music_var/bigbeet


Scan the Library
================

Initially the beets library needs to be scanned and translated into the bigbeet format.

mopidy bigbeet scan

A library DB File will be created in bb_data_dir 

Genres Tree
===========

The initial scan creates a genres-tree.yaml file.
This file defines how the hierarchical Genres Tree will be constructed.
You may want to edit the file. 



Project resources
=================

- `Source code <https://github.com/rawdlite/mopidy-bigbeet>`_
- `Issue tracker <https://github.com/rawdlite/mopidy-bigbeet/issues>`_


Credits
=======

- Original author: `tom roth <https://github.com/rawdlite>`_
- Current maintainer: `tom roth <https://github.com/rawdlite>`_
- `Contributors <https://github.com/rawdlite/mopidy-bigbeet/graphs/contributors>`_


Changelog
=========

v0.0.2 (UNRELEASED)
----------------------------------------

- Initial release.
