from __future__ import unicode_literals
import os.path
from shutil import copyfile
from yaml import load


class GenreTree():

    def __init__(self,data_dir):
       c14n_filename = os.path.join(data_dir, 'genres-tree.yaml')
       if not os.path.isfile(c14n_filename):
           copyfile(os.path.join(os.path.dirname(__file__), 'genres-tree.yaml'), c14n_filename)
       self.genres_missing = []
       self.genres_tree = load(open(c14n_filename, 'r'))
       self.branches = []
       self._flatten_tree(self.genres_tree, [], self.branches)	
 
    def _flatten_tree(self, elem, path, branches):
        """Flatten nested lists/dictionaries into lists of strings
        (branches).
        """
        if not path:
            path = []

        if isinstance(elem, dict):
            for (k, v) in elem.items():
                self._flatten_tree(v, path + [k], branches)
        elif isinstance(elem, list):
            for sub in elem:
                self._flatten_tree(sub, path, branches)
        else:
            branches.append(path + [unicode(elem)])

    def find_missing(self, candidate):
	if candidate.lower() not in [item for sublist in self.branches for item in sublist]:
            self.genres_missing.append(candidate.lower()) 

    def find_parents(self, candidate):
        """Find parents genre of a given genre, ordered from the closest to
        the further parent.
        """
        for branch in self.branches:
            try:
                idx = branch.index(candidate.lower())
                return branch[:idx + 1][::-1]
            except ValueError:
                continue
        return [candidate]

