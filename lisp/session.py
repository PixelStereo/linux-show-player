# -*- coding: utf-8 -*-
#
# This file is part of Linux Show Player
#
# Copyright 2012-2017 Francesco Ceruti <ceppofrancy@gmail.com>
#
# Linux Show Player is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linux Show Player is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linux Show Player.  If not, see <http://www.gnu.org/licenses/>.

import os

from os import path

from lisp.core.has_properties import HasProperties, Property
from lisp.core.memento_model import AdapterMementoModel


def Session(layout, session_file=''):
    class PublicSession(PrivateSession):
        pass

    return PublicSession(layout, session_file)


class PrivateSession(HasProperties):
    layout_name = Property(default='')
    session_file = Property(default='')

    def __init__(self, layout, session_file=''):
        """
        :type layout: lisp.layouts.cue_layout.CueLayout
        """
        super().__init__()

        self.__layout = layout
        self.__cue_model = layout.cue_model
        self.__memento_model = AdapterMementoModel(layout.model_adapter)

        self.layout_name = layout.NAME
        self.session_file = session_file

    @property
    def cue_model(self):
        return self.__cue_model

    @property
    def layout(self):
        return self.__layout

    def name(self):
        if self.session_file:
            return os.path.splitext(os.path.basename(self.session_file))[0]
        else:
            return 'Untitled'

    def path(self):
        if self.session_file:
            return path.dirname(self.session_file)
        else:
            return path.expanduser('~')

    def abs_path(self, rel_path):
        if not path.isabs(rel_path):
            return path.normpath(path.join(self.path(), rel_path))

        return rel_path

    def rel_path(self, abs_path):
        return path.relpath(abs_path, start=self.path())

    def destroy(self):
        self.__layout.finalize()
        self.__cue_model.reset()
