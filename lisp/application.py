# -*- coding: utf-8 -*-
#
# This file is part of Linux Show Player
#
# Copyright 2012-2016 Francesco Ceruti <ceppofrancy@gmail.com>
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

import json
from os.path import exists

from PyQt5.QtWidgets import QDialog, qApp

from lisp import layouts
from lisp import plugins
from lisp.core.actions_handler import MainActionsHandler
from lisp.core.configuration import config
from lisp.core.singleton import Singleton
from lisp.cues.cue import Cue
from lisp.cues.cue_factory import CueFactory
from lisp.cues.cue_model import CueModel
from lisp.cues.media_cue import MediaCue
from lisp.session import Session
from lisp.ui import elogging
from lisp.ui.layoutselect import LayoutSelect
from lisp.ui.mainwindow import MainWindow
from lisp.ui.settings.app_settings import AppSettings
from lisp.ui.settings.cue_settings import CueSettingsRegistry
from lisp.ui.settings.pages.app_general import AppGeneral
from lisp.ui.settings.pages.cue_app_settings import CueAppSettings
from lisp.ui.settings.pages.cue_appearance import Appearance
from lisp.ui.settings.pages.cue_general import CueGeneralSettings
from lisp.ui.settings.pages.media_cue_settings import MediaCueSettings


class Application(metaclass=Singleton):
    def __init__(self):
        self.__main_window = MainWindow()
        self.__cue_model = CueModel()
        self.__session = None

        # Register general settings widget
        AppSettings.register_settings_widget(AppGeneral)
        AppSettings.register_settings_widget(CueAppSettings)
        # Register common cue-settings widgets
        CueSettingsRegistry().add_item(CueGeneralSettings, Cue)
        CueSettingsRegistry().add_item(MediaCueSettings, MediaCue)
        CueSettingsRegistry().add_item(Appearance)

        # Connect mainWindow actions
        self.__main_window.new_session.connect(self._new_session_dialog)
        self.__main_window.save_session.connect(self._save_to_file)
        self.__main_window.open_session.connect(self._load_from_file)
        # Show the mainWindow maximized
        self.__main_window.showMaximized()

    @property
    def session(self):
        """:rtype: lisp.session.PrivateSession"""
        return self.__session

    @property
    def cue_model(self):
        """:rtype: lisp.cues.cue_model.CueModel"""
        return self.__cue_model

    def start(self, session_file=''):
        if exists(session_file):
            self._load_from_file(session_file)
        elif config['Layout']['Default'].lower() != 'nodefault':
            self._new_session(layouts.get_layout(config['Layout']['Default']))
        else:
            self._new_session_dialog()

    def finalize(self):
        self._delete_session()

        self.__main_window = None
        self.__cue_model = None

    def _new_session_dialog(self):
        """Show the layout-selection dialog"""
        try:
            # Prompt the user for a new layout
            dialog = LayoutSelect()
            if dialog.exec_() == QDialog.Accepted:
                # If a valid file is selected load it, otherwise load the layout
                if exists(dialog.filepath):
                    self._load_from_file(dialog.filepath)
                else:
                    self._new_session(dialog.selected())
            else:
                if self.__session is None:
                    # If the user close the dialog, and no layout exists
                    # the application is closed
                    self.finalize()
                    qApp.quit()
                    exit(0)
        except Exception as e:
            elogging.exception('Startup error', e)
            qApp.quit()
            exit(-1)

    def _new_session(self, layout):
        self._delete_session()

        self.__session = Session(layout(self.__cue_model))
        self.__main_window.set_session(self.__session)

        plugins.init_plugins()

    def _delete_session(self):
        if self.__session is not None:
            MainActionsHandler.clear()
            plugins.reset_plugins()

            self.__session.destroy()
            self.__session = None

    def _save_to_file(self, session_file):
        """Save the current session into a file."""
        self.session.session_file = session_file

        # Add the cues
        session_dict = {"cues": []}

        for cue in self.__cue_model:
            session_dict['cues'].append(cue.properties(only_changed=True))
        # Sort cues by index, allow sorted-models to load properly
        session_dict['cues'].sort(key=lambda cue: cue['index'])

        # Get session settings
        session_dict['session'] = self.__session.properties()
        # Remove "session_file"
        session_dict['session'].pop('session_file', None)

        # Write to a file the json-encoded dictionary
        with open(session_file, mode='w', encoding='utf-8') as file:
            file.write(json.dumps(session_dict, sort_keys=True, indent=4))

        MainActionsHandler.set_saved()
        self.__main_window.update_window_title()

    def _load_from_file(self, session_file):
        """ Load a saved session from file """
        try:
            with open(session_file, mode='r', encoding='utf-8') as file:
                session_dict = json.load(file)

            # New session
            self._new_session(
                layouts.get_layout(session_dict['session']['layout_name']))
            self.__session.update_properties(session_dict['session'])
            self.__session.session_file = session_file

            # Load cues
            for cues_dict in session_dict.get('cues', {}):
                cue_type = cues_dict.pop('_type_', 'Undefined')
                cue_id = cues_dict.pop('id')
                try:
                    cue = CueFactory.create_cue(cue_type, cue_id=cue_id)
                    cue.update_properties(cues_dict)
                    self.__cue_model.add(cue)
                except Exception as e:
                    elogging.exception('Unable to create the cue', e)

            MainActionsHandler.set_saved()
            self.__main_window.update_window_title()

            # Update the main-window
            #self.__main_window.update()
        except Exception as e:
            elogging.exception('Error during file reading', e)
            self._new_session_dialog()
