#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Ilias Stamatis <stamatis.iliass@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __init__ import __version__

from PyQt4.QtCore import (PYQT_VERSION_STR, QLocale, QRegExp, QSettings, QSize,
                          QString, QTimer, QTranslator, QT_VERSION_STR)
from PyQt4.QtGui import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                         QDialog, QFileDialog, QFrame, QGridLayout,
                         QHBoxLayout, QIcon, QKeySequence, QLabel, QLineEdit,
                         QListWidget, QMainWindow, QMessageBox, QPushButton,
                         QRadioButton, QRegExpValidator, QSizePolicy,
                         QSpacerItem, QTabWidget, QToolButton, QVBoxLayout,
                         QWidget)

import os
import sys
import shutil
import subprocess
import shlex
import re
import glob
import platform
import logging

import progress
import pyqttools
import preferences_dlg
import presets_dlgs
import qrc_resources

try:
    import PythonMagick
except ImportError:
    pass


_format =  '%(asctime)s : %(levelname)s - %(type)s\nCommand: %(command)s\n'
_format += 'Return code: %(returncode)s\n%(message)s\n'

log_folder = os.path.join(os.getenv('HOME'), '.config/ffmulticonverter/logs')
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
log_file = os.path.join(log_folder, 'history.log')

logging.basicConfig(
    filename = log_file,
    level=logging.DEBUG,
    format=_format,
    datefmt='%Y-%m-%d %H:%M:%S'
)


class ValidationError(Exception): pass

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.home = os.getenv('HOME')
        self.fname = ''
        self.output = ''

        addButton = QPushButton('Add')
        delButton = QPushButton('Delete')
        clearButton = QPushButton('Clear')
        vlayout1 = pyqttools.add_to_layout(QVBoxLayout(), addButton, delButton,
                                           clearButton, None)

        self.fileList = QListWidget()
        hlayout1 = pyqttools.add_to_layout(QHBoxLayout(), self.fileList,
                                           vlayout1)


        output_label = QLabel(self.tr('Output folder:'))
        self.toLineEdit = QLineEdit()
        self.toLineEdit.setReadOnly(True)
        self.toToolButton = QToolButton()
        self.toToolButton.setText('...')
        hlayout2 = pyqttools.add_to_layout(QHBoxLayout(), output_label,
                                           self.toLineEdit, self.toToolButton)

        self.audiovideo_tab = AudioVideoTab(self)
        self.image_tab = ImageTab(self)
        self.document_tab = DocumentTab(self)

        self.tabs = [self.audiovideo_tab, self.image_tab, self.document_tab]
        tab_names = [self.tr('Audio/Video'), self.tr('Images'),
                                                          self.tr('Documents')]
        self.TabWidget = QTabWidget()
        for num, tab in enumerate(tab_names):
            self.TabWidget.addTab(self.tabs[num], tab)
        self.TabWidget.setCurrentIndex(0)


        self.origCheckBox = QCheckBox('Save each file in the same\n'
                                      'folder as input file')
        self.deleteCheckBox = QCheckBox(self.tr('Delete original'))
        self.convertPushButton = QPushButton(self.tr('&Convert'))

        hlayout3 = pyqttools.add_to_layout(QHBoxLayout(), self.origCheckBox,
                                           self.deleteCheckBox, None)
        hlayout4 = pyqttools.add_to_layout(QHBoxLayout(), None,
                                          self.convertPushButton)
        final_layout = pyqttools.add_to_layout(QVBoxLayout(), hlayout1,
                                        self.TabWidget, hlayout2, hlayout3,
                                        hlayout4)

        self.statusBar = self.statusBar()
        self.dependenciesLabel = QLabel()
        self.statusBar.addPermanentWidget(self.dependenciesLabel, stretch=1)

        Widget = QWidget()
        Widget.setLayout(final_layout)
        self.setCentralWidget(Widget)

        c_act = pyqttools.create_action
        openAction = c_act(self, self.tr('Open'), QKeySequence.Open, None,
                                        self.tr('Open a file'), self.open_file)
        convertAction = c_act(self, self.tr('Convert'), 'Ctrl+C', None,
                               self.tr('Convert files'), self.start_conversion)
        quitAction = c_act(self, self.tr('Quit'), 'Ctrl+Q', None, self.tr(
                                                           'Quit'), self.close)
        edit_presetsAction = c_act(self, self.tr('Edit Presets'), 'Ctrl+P',
                                   None, self.tr('Edit Presets'), self.presets)
        importAction = c_act(self, self.tr('Import'), None, None,
                                self.tr('Import presets'), self.import_presets)
        exportAction = c_act(self, self.tr('Export'), None, None,
                                self.tr('Export presets'), self.export_presets)
        resetAction = c_act(self, self.tr('Reset'), None, None,
                                  self.tr('Reset presets'), self.reset_presets)
        clearAction = c_act(self, self.tr('Clear'), None, None,
                                             self.tr('Clear form'), self.clear)
        preferencesAction = c_act(self, self.tr('Preferences'), 'Alt+Ctrl+P',
                                None, self.tr('Preferences'), self.preferences)
        aboutAction = c_act(self, self.tr('About'), 'Ctrl+?', None,
                                                  self.tr('About'), self.about)

        fileMenu = self.menuBar().addMenu(self.tr('File'))
        editMenu = self.menuBar().addMenu(self.tr('Edit'))
        presetsMenu = self.menuBar().addMenu(self.tr('Presets'))
        helpMenu = self.menuBar().addMenu(self.tr('Help'))
        pyqttools.add_actions(fileMenu, [openAction, convertAction, None,
                                                                   quitAction])
        pyqttools.add_actions(presetsMenu, [edit_presetsAction, importAction,
                                                    exportAction, resetAction])
        pyqttools.add_actions(editMenu, [clearAction, None, preferencesAction])
        pyqttools.add_actions(helpMenu, [aboutAction])


        self.TabWidget.currentChanged.connect(self.resize_window)
        self.TabWidget.currentChanged.connect(self.checkboxes_clicked)
        self.toToolButton.clicked.connect(self.open_dir)
        self.convertPushButton.clicked.connect(convertAction.triggered)


        self.resize(700, 500)
        self.setWindowTitle('FF Multi Converter')

        QTimer.singleShot(0, self.check_for_dependencies)
        QTimer.singleShot(0, self.set_settings)
        QTimer.singleShot(0, self.audiovideo_tab.set_default_command)

    def checkboxes_clicked(self, data=None):
        """Manages the behavior of checkboxes and radiobuttons.

        Keywords arguments:
        data -- a string to show from which CheckBox the signal emitted.
        """
        # data default value is None because the method can also be called
        # when TabWidget's tab change.
        if data == 'folder' and self.recursiveCheckBox.isChecked():
            self.recursiveCheckBox.setChecked(False)
        elif data == 'recursive' and self.folderCheckBox.isChecked():
            self.folderCheckBox.setChecked(False)

        enable = self.recursiveCheckBox.isChecked() or \
                                                self.folderCheckBox.isChecked()
        self.extRadioButton.setEnabled(enable)
        if enable and self.current_tab().name == 'Documents':
            # set typeRadioButton disabled when type == document files,
            # because it is not possible to convert every file format to any
            # other file format.
            self.typeRadioButton.setEnabled(False)
            self.extRadioButton.setChecked(True)
        else:
            self.typeRadioButton.setEnabled(enable)

    def clear(self):
        """Clears the form.

        Clears line edits and unchecks checkboxes and radio buttons.
        """
        self.fromLineEdit.clear()
        self.fname = ''
        if self.output is not None:
            self.toLineEdit.clear()
            self.output = ''
        boxes = [self.folderCheckBox, self.recursiveCheckBox,
                                                           self.deleteCheckBox]
        for box in boxes:
            box.setChecked(False)
        self.checkboxes_clicked()

        self.audiovideo_tab.clear()
        self.image_tab.clear()

    def resize_window(self):
        """Hides widgets of AudioVideo tab and resizes the window."""
        self.tabs[0].moreButton.setChecked(False)

    def current_tab(self):
        """Returns current tab."""
        for i in self.tabs:
            if self.tabs.index(i) == self.TabWidget.currentIndex():
                return i

    def set_settings(self):
        """Sets program settings"""
        settings = QSettings()
        self.saveto_output = settings.value('saveto_output').toBool()
        self.rebuild_structure = settings.value('rebuild_structure').toBool()
        self.overwrite_existing = settings.value('overwrite_existing').toBool()
        self.default_output = unicode(
                                   settings.value('default_output').toString())
        self.prefix = unicode(settings.value('prefix').toString())
        self.suffix = unicode(settings.value('suffix').toString())
        self.avconv_prefered = settings.value('avconv_prefered').toBool()
        self.default_command = unicode(
                                  settings.value('default_command').toString())
        if not self.default_command:
            self.default_command = '-ab 320k -ar 48000 -ac 2'

        if self.saveto_output:
            if self.output is None or self.toLineEdit.text() == '':
                self.output = self.default_output
                self.toLineEdit.setText(self.output)
            self.toLineEdit.setEnabled(True)
        else:
            self.toLineEdit.setEnabled(False)
            self.toLineEdit.setText(self.tr(
                                           'Each file to its original folder'))
            self.output = None

    def open_file(self):
        """Uses standard QtDialog to get file name."""
        all_files = '*'
        audiovideo_files = ' '.join(
                                 ['*.'+i for i in self.audiovideo_tab.formats])
        img_formats = self.image_tab.formats[:]
        img_formats.extend(self.image_tab.extra_img)
        image_files = ' '.join(['*.'+i for i in img_formats])
        document_files = ' '.join(['*.'+i for i in self.document_tab.formats])
        formats = [all_files, audiovideo_files, image_files, document_files]
        strings = [self.tr('All Files'), self.tr('Audio/Video Files'),
                   self.tr('Image Files'), self.tr('Document Files')]

        filters = ''
        for string, extensions in zip(strings, formats):
            filters += string + ' ({0});;'.format(extensions)
        filters = filters[:-2] # remove last ';;'

        fname = QFileDialog.getOpenFileName(self, 'FF Multi Converter - ' + \
                                    self.tr('Choose File'), self.home, filters)
        fname = unicode(fname)
        if fname:
            self.fname = fname
            self.fromLineEdit.setText(self.fname)

    def open_dir(self):
        """Uses standard QtDialog to get directory name."""
        if self.toLineEdit.isEnabled():
            output = QFileDialog.getExistingDirectory(self, 'FF Multi '
              'Converter - ' + self.tr('Choose output destination'), self.home)
            output = unicode(output)
            if output:
                self.output = output
                self.toLineEdit.setText(self.output)
        else:
            return QMessageBox.warning(self, 'FF Multi Converter - ' + \
                    self.tr('Save Location!'), self.tr(
                   'You have chosen to save every file to its original folder.'
                   '\nYou can change this from preferences.'))

    def preferences(self):
        """Opens the preferences dialog."""
        dialog = preferences_dlg.Preferences(self)
        if dialog.exec_():
            self.set_settings()

    def presets(self):
        """Opens the presets dialog."""
        dialog = presets_dlgs.ShowPresets()
        dialog.exec_()

    def import_presets(self):
        presets_dlgs.ShowPresets().import_presets()

    def export_presets(self):
        presets_dlgs.ShowPresets().export_presets()

    def reset_presets(self):
        presets_dlgs.ShowPresets().reset()

    def ok_to_continue(self):
        """Checks if everything is ok to continue with conversion.

        Checks if:
        - Theres is no given file or no given output destination
        - Given file exists and output destination exists

        Returns: boolean
        """
        try:
            if self.fname == '':
                raise ValidationError(self.tr(
                                         'You must choose a file to convert!'))
            elif not os.path.exists(self.fname):
                raise ValidationError(self.tr(
                                         'The selected file does not exists!'))
            elif self.output is not None and self.output == '':
                raise ValidationError(self.tr(
                                          'You must choose an output folder!'))
            elif self.output is not None and not os.path.exists(self.output):
                raise ValidationError(self.tr(
                                             'Output folder does not exists!'))
            if not self.current_tab().ok_to_continue():
                return False
            return True

        except ValidationError as e:
            QMessageBox.warning(self, 'FF Multi Converter - ' + \
                                                 self.tr('Error!'), unicode(e))
            return False

    def get_extension(self):
        tab = self.current_tab()
        if tab.name == 'AudioVideo':
            if self.audiovideo_tab.extLineEdit.isEnabled():
                ext_to = self.audiovideo_tab.extLineEdit.text()
            else:
                ext_to = self.audiovideo_tab.extComboBox.currentText()
        elif tab.name == 'Images':
            ext_to = tab.extComboBox.currentText()
        else:
            ext_to = str(tab.convertComboBox.currentText()).split()[-1]

        return str('.' + ext_to)

    def current_formats(self):
        """Returns the file formats of current tab.

        Returns: list
        """
        tab = self.current_tab()
        if tab.name == 'Documents':
            type_formats = tab.formats.keys()
        elif tab.name == 'Images':
            type_formats = tab.formats[:] + tab.extra_img
        else:
            type_formats = tab.formats[:] + tab.extra_formats
            if tab.extLineEdit.isEnabled():
                type_formats.append(str(tab.extLineEdit.text()))
        return ['.' + i for i in type_formats]

    def should_include(self, path, includes):
        """Returns True if the given path should be included."""
        ext = os.path.splitext(path)[-1]
        if not includes:
            return True
        else:
            return ext in includes

    def create_paths_list(self, path_pattern, recursive=True, includes=[]):
        """Creates a list of paths from a path pattern.

        Keyword arguments:
        path_pattern -- an str path using the '*' glob pattern
        recursive    -- if True, include files recursively
                        if False, include only files in the same folder
        includes     -- list of file patterns to include in recursive searches

        Returns: list
        """
        assert path_pattern.endswith('*'), 'path must end with an asterisk (*)'
        assert all(i.startswith('.') for i in includes), \
                                       'all includes must start with a dot (.)'

        paths_list = []
        paths = glob.glob(path_pattern)
        for path in paths:
            if not os.path.islink(path) and os.path.isdir(path) and recursive:
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in sorted(filenames):
                        f = os.path.join(dirpath, filename)
                        if self.should_include(f, includes):
                            paths_list.append(f)

            elif self.should_include(path, includes):
                paths_list.append(path)

        return paths_list

    def files_to_conv_list(self):
        """Generates paths of files to convert.

        Creates:
        1.files_to_conv -- list with files that must be converted
        The list will contain only the _file if conversion is no recursive

        Returns: list
        """
        _dir, file_name = os.path.split(self.fname)
        base, ext = os.path.splitext(file_name)
        _dir += '/*'
        formats = self.current_formats()

        if not (self.folderCheckBox.isChecked() or \
                                           self.recursiveCheckBox.isChecked()):
            files_to_conv = [self.fname]

        else:
            recursive = self.recursiveCheckBox.isChecked()
            includes = [ext] if self.extRadioButton.isChecked() else formats
            files_to_conv = self.create_paths_list(_dir, recursive,
                                                             includes=includes)

            # put given file first in list
            files_to_conv.remove(self.fname)
            files_to_conv.insert(0, self.fname)

        return files_to_conv

    def build_lists(self, files_list, ext_to, prefix, suffix, output,
                         saveto_output, rebuild_structure, overwrite_existing):
        """Creates two lists:

        1.conversion_list -- list with dicts to show where each file must be
                             saved
        Example:
        [{/foo/bar.png : "/foo/bar.png"}, {/f/bar2.png : "/foo2/bar.png"}]

        2.create_folders_list -- a list with folders that must be created

        Keyword arguments:
        files_list -- list with files to be converted
        ext_to     -- the extension to which each file must be converted to
        prefix     -- string that will be added as a prefix to all filenames
        suffix     -- string that will be added as a suffix to all filenames
        output     -- the output folder
        saveto_output -- if True, files will be saved at ouput
                       if False, each file will be saved at its original folder
        rebuild_structure  -- if True, file's structure will be rebuild
        overwrite_existing -- if False, a '~' will be added as prefix to
                              filenames

        Returns: two lists
        """
        assert ext_to.startswith('.'), 'ext_to must start with a dot (.)'

        rel_path_files_list = []
        folders = []
        create_folders_list = []
        conversion_list = []

        parent_file = files_list[0]
        parent_dir, parent_name = os.path.split(parent_file)
        parent_base, parent_ext = os.path.split(parent_name)
        parent_dir += '/'

        for _file in files_list:
            _dir, name = os.path.split(_file)
            base, ext = os.path.splitext(name)
            _dir += '/'
            y = _dir + prefix + base + suffix + ext_to

            if saveto_output:
                folder = output + '/'
                if rebuild_structure:
                    y = re.sub('^'+parent_dir, '', y)
                    y = folder + y
                    rel_path_files_list.append(y)
                    for z in rel_path_files_list:
                        folder_to_create = os.path.split(z)[0]
                        folders.append(folder_to_create)

                    # remove list from duplicates
                    for fol in folders:
                        if not fol in create_folders_list:
                            create_folders_list.append(fol)
                    create_folders_list.sort()
                    # remove first folder because it already exists.
                    create_folders_list.pop(0)
                else:
                    y = re.sub('^'+_dir, '', y)
                    y = folder + y

            if os.path.exists(y) and not overwrite_existing:
                _dir2, _name2 = os.path.split(y)
                y = _dir2 + '/~' + _name2
            # Add quotations to path in order to avoid error in special
            # cases such as spaces or special characters.
            _file = '"' + _file + '"'
            y = '"' + y + '"'

            _dict = {}
            _dict[_file] = y
            conversion_list.append(_dict)

        return conversion_list, create_folders_list

    def start_conversion(self):
        """Initialises the Progress dialog."""
        if not self.ok_to_continue():
            return

        ext_to = self.get_extension()
        files_to_conv = self.files_to_conv_list()
        conversion_list, create_folders_list = self.build_lists(
           files_to_conv, ext_to, self.prefix, self.suffix, self.output,
           self.saveto_output, self.rebuild_structure, self.overwrite_existing)

        if create_folders_list:
            for i in create_folders_list:
                try:
                    os.mkdir(i)
                except OSError:
                    pass

        delete = self.deleteCheckBox.isChecked()
        dialog = progress.Progress(self, conversion_list, delete)
        dialog.exec_()

    def is_installed(self, program):
        """Checks if program is installed."""
        for path in os.getenv('PATH').split(os.pathsep):
            fpath = os.path.join(path, program)
            if os.path.exists(fpath) and os.access(fpath, os.X_OK):
                return True
        return False

    def check_for_dependencies(self):
        """Checks if dependencies are installed and set dependenciesLabel
        status."""
        missing = []
        self.ffmpeg = self.is_installed('ffmpeg')
        self.avconv = self.is_installed('avconv')
        if not self.ffmpeg and not self.avconv:
            missing.append('FFmpeg/avconv')
        if self.is_installed('unoconv'):
            self.unoconv = True
        else:
            self.unoconv = False
            missing.append('unoconv')
        try:
            PythonMagick # PythonMagick has imported earlier
            self.pmagick = True
        except NameError:
            self.pmagick = False
            missing.append('PythonMagick')

        missing = ', '.join(missing) if missing else self.tr('None')
        status = self.tr('Missing dependencies:') + ' ' + missing
        self.dependenciesLabel.setText(status)

    def about(self):
        """Opens the about dialog."""
        link = 'http://sites.google.com/site/ffmulticonverter/'
        msg = self.tr('Convert among several file types to other extensions')
        if len(msg) > 54:
            # break line if msg is too long to fit the window
            nmsg = ''
            for n, w in enumerate(msg.split(' ')):
                if len(nmsg) > 54:
                    break
                nmsg += w + ' '
            nmsg += '<br>' + msg[len(nmsg):]
            msg = nmsg
        text = '''<b> FF Multi Converter {0} </b>
                 <p>{1}
                 <p><a href="{2}">FF Multi Converter - Home Page</a>
                 <p>Copyright &copy; 2011-2012 Ilias Stamatis
                 <br>License: GNU GPL3
                 <p>Python {3} - Qt {4} - PyQt {5} on {6}'''\
                 .format(__version__, msg, link, platform.python_version()[:5],
                         QT_VERSION_STR, PYQT_VERSION_STR, platform.system())
        image = ':/ffmulticonverter.png'
        authors  = 'Ilias Stamatis <stamatis.iliass@gmail.com>\n\n'
        authors += 'Contributors:\nPanagiotis Mavrogiorgos'
        transl_list = [['[cs] Czech', 'Petr Simacek'],
                       ['[de_DE] German (Germany)', 'Stefan Wilhelm'],
                       ['[el] Greek', 'Ilias Stamatis'],
                       ['[hu] Hungarian', 'Farkas Norbert'],
                       ['[pl_PL] Polish (Poland)', 'Lukasz Koszy'],
                       ['[pt] Portuguese', 'Sérgio Marques'],
                       ['[pt_BR] Portuguese (Brasil)', 'José Humberto A Melo'],
                       ['[ru] Russian', 'Andrew Lapshin'],
                       ['[tu] Turkish', 'Tayfun Kayha'],
                       ['[zh_CN] Chinese (China)', 'Dianjin Wang']]
        translators = ''
        for i in transl_list:
            translators += '{0}\n     {1}\n\n'.format(i[0], i[1])
        translators = translators[:-2]

        dialog = AboutDialog(text, image, authors, translators)
        dialog.exec_()


class AboutDialog(QDialog):
    def __init__(self, text, image, authors, translators, parent=None):
        super(AboutDialog, self).__init__(parent)
        self.parent = parent
        self.authors = authors
        self.translators = translators

        from PyQt4.QtGui import (QPushButton, QLabel, QPixmap, QVBoxLayout,
                                 QHBoxLayout)

        imageLabel = QLabel()
        imageLabel.setMaximumSize(QSize(63, 61))
        imageLabel.setPixmap(QPixmap(image))
        imageLabel.setScaledContents(True)
        textLabel = QLabel()
        textLabel.setText(text)
        textLabel.setOpenExternalLinks(True)
        creditsButton = QPushButton('Credits')
        closeButton = QPushButton('&Close')

        vlayout1 = pyqttools.add_to_layout(QVBoxLayout(), imageLabel, None)
        hlayout1 = pyqttools.add_to_layout(QHBoxLayout(), vlayout1, textLabel)
        hlayout2 = pyqttools.add_to_layout(QHBoxLayout(), creditsButton, None,
                                                                   closeButton)
        fin_layout = pyqttools.add_to_layout(QVBoxLayout(), hlayout1, hlayout2)

        self.setLayout(fin_layout)

        closeButton.clicked.connect(self.close)
        creditsButton.clicked.connect(self.show_credits)

        self.resize(455, 200)
        self.setWindowTitle(self.tr('About FF Multi Converter'))

    def show_credits(self):
        dialog = CreditsDialog(self.authors, self.translators)
        dialog.exec_()


class CreditsDialog(QDialog):
    def __init__(self, authors, translators, parent=None):
        super(CreditsDialog, self).__init__(parent)
        self.parent = parent

        from PyQt4.QtGui import (QPlainTextEdit, QTabWidget, QPushButton,
                                 QHBoxLayout, QVBoxLayout)

        authorsLabel = QPlainTextEdit(authors)
        authorsLabel.setReadOnly(True)
        translatorsLabel = QPlainTextEdit(translators)
        translatorsLabel.setReadOnly(True)
        TabWidget = QTabWidget()
        TabWidget.addTab(authorsLabel, 'Written by')
        TabWidget.addTab(translatorsLabel, 'Translated by')
        closeButton = QPushButton('&Close')

        hlayout = pyqttools.add_to_layout(QHBoxLayout(), None, closeButton)
        vlayout = pyqttools.add_to_layout(QVBoxLayout(), TabWidget, hlayout)

        self.setLayout(vlayout)
        closeButton.clicked.connect(self.close)

        self.setMinimumSize(QSize(335, 370))
        self.setMaximumSize(QSize(335, 370))
        self.setWindowTitle(self.tr('Credits'))


class AudioVideoTab(QWidget):
    def __init__(self, parent):
        super(AudioVideoTab, self).__init__(parent)
        self.parent = parent
        self.name = 'AudioVideo'
        self.formats = ['aac', 'ac3', 'afc', 'aiff', 'amr', 'asf', 'au',
                        'avi', 'dvd', 'flac', 'flv', 'mka',
                        'mkv', 'mmf', 'mov', 'mp3', 'mp4', 'mpg',
                        'ogg', 'ogv', 'psp', 'rm', 'spx', 'vob',
                        'wav', 'webm', 'wma', 'wmv']
        self.extra_formats = ['aifc', 'm2t', 'm4a', 'm4v', 'mp2', 'mpeg',
                              'ra', 'ts']

        nochange = self.tr('No Change')
        frequency_values = [nochange, '22050', '44100', '48000']
        bitrate_values = [nochange, '32', '96', '112', '128', '160', '192',
                                                              '256', '320']
        pattern = QRegExp(r'^[1-9]\d*')
        validator = QRegExpValidator(pattern, self)


        converttoLabel = QLabel(self.tr('Convert to:'))
        self.extComboBox = QComboBox()
        self.extComboBox.addItems(self.formats + [self.tr('Other')])
        self.extComboBox.setMinimumWidth(130)
        self.extLineEdit = QLineEdit()
        self.extLineEdit.setMaximumWidth(85)
        self.extLineEdit.setEnabled(False)
        hlayout1 = pyqttools.add_to_layout(QHBoxLayout(), converttoLabel,
                                      None, self.extComboBox, self.extLineEdit)
        commandLabel = QLabel(self.tr('Command:'))
        self.commandLineEdit = QLineEdit()
        self.presetButton = QPushButton(self.tr('Preset'))
        self.defaultButton = QPushButton(self.tr('Default'))
        hlayout2 = pyqttools.add_to_layout(QHBoxLayout(), commandLabel,
                   self.commandLineEdit, self.presetButton, self.defaultButton)

        sizeLabel = QLabel(self.tr('Video Size:'))
        aspectLabel = QLabel(self.tr('Aspect:'))
        frameLabel = QLabel(self.tr('Frame Rate (fps):'))
        bitrateLabel = QLabel(self.tr('Video Bitrate (kbps):'))

        self.widthLineEdit = pyqttools.create_LineEdit((50, 16777215),
                                                                  validator, 4)
        self.heightLineEdit = pyqttools.create_LineEdit((50, 16777215),
                                                                   validator,4)
        label = QLabel('x')
        layout1 = pyqttools.add_to_layout(QHBoxLayout(), self.widthLineEdit,
                                                    label, self.heightLineEdit)
        self.aspect1LineEdit = pyqttools.create_LineEdit((35, 16777215),
                                                                   validator,2)
        self.aspect2LineEdit = pyqttools.create_LineEdit((35, 16777215),
                                                                   validator,2)
        label = QLabel(':')
        layout2 = pyqttools.add_to_layout(QHBoxLayout(), self.aspect1LineEdit,
                                                   label, self.aspect2LineEdit)
        self.frameLineEdit = pyqttools.create_LineEdit(None, validator, 4)
        self.bitrateLineEdit = pyqttools.create_LineEdit(None, validator, 6)

        labels = [sizeLabel, aspectLabel, frameLabel, bitrateLabel]
        widgets = [layout1, layout2, self.frameLineEdit, self.bitrateLineEdit]

        videosettings_layout = QHBoxLayout()
        for a, b in zip(labels, widgets):
            text = a.text()
            a.setText('<html><p align="center">{0}</p></html>'.format(text))
            layout = pyqttools.add_to_layout(QVBoxLayout(), a, b)
            videosettings_layout.addLayout(layout)

        freqLabel = QLabel(self.tr('Frequency (Hz):'))
        chanLabel = QLabel(self.tr('Channels:'))
        bitrateLabel = QLabel(self.tr('Audio Bitrate (kbps):'))

        self.freqComboBox = QComboBox()
        self.freqComboBox.addItems(frequency_values)
        self.chan1RadioButton = QRadioButton('1')
        self.chan1RadioButton.setMaximumSize(QSize(51, 16777215))
        self.chan2RadioButton = QRadioButton('2')
        self.chan2RadioButton.setMaximumSize(QSize(51, 16777215))
        self.group = QButtonGroup()
        self.group.addButton(self.chan1RadioButton)
        self.group.addButton(self.chan2RadioButton)
        spcr1 = QSpacerItem(40, 20, QSizePolicy.Preferred, QSizePolicy.Minimum)
        spcr2 = QSpacerItem(40, 20, QSizePolicy.Preferred, QSizePolicy.Minimum)
        chanlayout = pyqttools.add_to_layout(QHBoxLayout(), spcr1,
                           self.chan1RadioButton, self.chan2RadioButton, spcr2)
        self.audio_bitrateComboBox = QComboBox()
        self.audio_bitrateComboBox.addItems(bitrate_values)

        labels = [freqLabel, chanLabel, bitrateLabel]
        widgets = [self.freqComboBox, chanlayout, self.audio_bitrateComboBox]

        audiosettings_layout = QHBoxLayout()
        for a, b in zip(labels, widgets):
            text = a.text()
            a.setText('<html><p align="center">{0}</p></html>'.format(text))
            layout = pyqttools.add_to_layout(QVBoxLayout(), a, b)
            audiosettings_layout.addLayout(layout)

        hidden_layout = pyqttools.add_to_layout(QVBoxLayout(),
                              videosettings_layout, audiosettings_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.moreButton = QPushButton(QApplication.translate('Tab', 'More'))
        self.moreButton.setSizePolicy(QSizePolicy(QSizePolicy.Fixed))
        self.moreButton.setCheckable(True)
        hlayout3 = pyqttools.add_to_layout(QHBoxLayout(), line,self.moreButton)

        self.frame = QFrame()
        self.frame.setLayout(hidden_layout)
        self.frame.hide()

        final_layout = pyqttools.add_to_layout(QVBoxLayout(), hlayout1,
                                                hlayout2, hlayout3, self.frame)
        self.setLayout(final_layout)


        self.extComboBox.currentIndexChanged.connect(self.set_line_enable)
        self.presetButton.clicked.connect(self.choose_preset)
        self.defaultButton.clicked.connect(self.set_default_command)
        self.moreButton.toggled.connect(self.frame.setVisible)
        self.moreButton.toggled.connect(self.resize_parent)
        self.widthLineEdit.textChanged.connect(
                                  lambda: self.command_elements_change('size'))
        self.heightLineEdit.textChanged.connect(
                                  lambda: self.command_elements_change('size'))
        self.aspect1LineEdit.textChanged.connect(
                                lambda: self.command_elements_change('aspect'))
        self.aspect2LineEdit.textChanged.connect(
                                lambda: self.command_elements_change('aspect'))
        self.frameLineEdit.textChanged.connect(
                                lambda: self.command_elements_change('frames'))
        self.bitrateLineEdit.textChanged.connect(
                         lambda: self.command_elements_change('video_bitrate'))
        self.freqComboBox.currentIndexChanged.connect(
                             lambda: self.command_elements_change('frequency'))
        self.audio_bitrateComboBox.currentIndexChanged.connect(
                         lambda: self.command_elements_change('audio_bitrate'))
        self.chan1RadioButton.clicked.connect(
                             lambda: self.command_elements_change('channels1'))
        self.chan2RadioButton.clicked.connect(
                             lambda: self.command_elements_change('channels2'))

    def resize_parent(self):
        """Resizes MainWindow"""
        height = 622 if self.frame.isVisible() else 500
        self.parent.setMinimumSize(700, height)
        self.parent.resize(700, height)

    def set_line_enable(self):
        """Enable or disable self.extLineEdit."""
        self.extLineEdit.setEnabled(
                          self.extComboBox.currentIndex() == len(self.formats))

    def clear(self):
        """Clear values."""
        lineEdits = [self.commandLineEdit, self.widthLineEdit,
            self.heightLineEdit, self.aspect1LineEdit, self.aspect2LineEdit,
            self.frameLineEdit, self.bitrateLineEdit, self.extLineEdit]
        for i in lineEdits:
            i.clear()

        self.freqComboBox.setCurrentIndex(0)
        self.audio_bitrateComboBox.setCurrentIndex(0)
        self.group.setExclusive(False)
        self.chan1RadioButton.setChecked(False)
        self.chan2RadioButton.setChecked(False)
        self.group.setExclusive(True)
        # setExclusive(False) in order to be able to uncheck checkboxes and
        # then setExclusive(True) so only one radio button can be set

    def ok_to_continue(self):
        """Checks if commanLineEdit is empty in order to continue to conversion

        Returns: boolean
        """
        if not self.parent.ffmpeg and not self.parent.avconv:
            QMessageBox.warning(self, 'FF Multi Converter - ' + self.tr(
                'Error!'), self.tr('Neither ffmpeg nor avconv are installed.'
                '\nYou will not be able to convert audio/video files until you'
                ' install one of them.'))
            return False
        if self.extLineEdit.isEnabled():
            text = str(self.extLineEdit.text()).strip()
            if len(text.split()) != 1 or text[0] == '.':
                QMessageBox.warning(self, 'FF Multi Converter - ' + self.tr(
                    'Error!'), self.tr('Extension must be one word and must '
                    'not start with a dot.'))
                self.extLineEdit.selectAll()
                self.extLineEdit.setFocus()
                return False
        if not self.commandLineEdit.text():
            QMessageBox.warning(self, 'FF Multi Converter - ' + self.tr(
                'Error!'), self.tr('The command LineEdit may not be empty.'))
            self.commandLineEdit.setFocus()
            return False
        return True

    def set_default_command(self):
        """Sets the default value to self.commandLineEdit"""
        self.clear()
        self.commandLineEdit.setText(self.parent.default_command)

    def choose_preset(self):
        """Opens the presets dialog and set the appropriate value to
           commandLineEdit.
        """
        dialog = presets_dlgs.ShowPresets()
        if dialog.exec_() and dialog.the_command is not None:
                self.commandLineEdit.setText(dialog.the_command)
                self.commandLineEdit.home(False)
                find = self.extComboBox.findText(dialog.the_extension)
                if find >= 0:
                    self.extComboBox.setCurrentIndex(find)
                else:
                    self.extComboBox.setCurrentIndex(len(self.formats))
                    self.extLineEdit.setText(dialog.the_extension)

    def remove_consecutive_spaces(self, string):
        """Removes any consecutive spaces from a string.

        Returns: String
        """
        temp = string
        string = ''
        for i in temp.split():
            if i:
                string += i + ' '
        return string[:-1]

    def command_elements_change(self, widget):
        """Fill commandLineEdit with the appropriate command parameters."""
        command = str(self.commandLineEdit.text())

        if widget == 'size':
            text1 = self.widthLineEdit.text()
            text2 = self.heightLineEdit.text()

            if (text1 or text2) and not (text1 and text2):
                return
            f = re.sub(r'^.*(-s\s+\d+x\d+).*$', r'\1', command)
            if re.match(r'^.*(-s\s+\d+x\d+).*$', f):
                command = command.replace(f, '').strip()
            if text1 and text2:
                command += ' -s {0}x{1}'.format(text1, text2)

        elif widget == 'aspect':
            text1 = self.aspect1LineEdit.text()
            text2 = self.aspect2LineEdit.text()

            if (text1 or text2) and not (text1 and text2):
                return
            f = re.sub(r'^.*(-aspect\s+\d+:\d+).*$', r'\1', command)
            if re.match(r'^.*(-aspect\s+\d+:\d+).*$', f):
                command = command.replace(f, '').strip()
            if text1 and text2:
                command += ' -aspect {0}:{1}'.format(text1, text2)

        elif widget == 'frames':
            text = self.frameLineEdit.text()
            f = re.sub(r'^.*(-r\s+\d+).*$', r'\1', command)
            if re.match(r'^.*(-r\s+\d+).*$', f):
                command = command.replace(f, '').strip()
            if text:
                command += ' -r {0}'.format(text)

        elif widget == 'video_bitrate':
            text = self.bitrateLineEdit.text()
            f = re.sub(r'^.*(-b\s+\d+k).*$', r'\1', command)
            if re.match(r'^.*(-b\s+\d+k).*$', f):
                command = command.replace(f, '')
            if text:
                command += ' -b {0}k'.format(text)
            command = command.replace('-sameq', '').strip()

        elif widget == 'frequency':
            text = self.freqComboBox.currentText()
            f = re.sub(r'^.*(-ar\s+\d+).*$', r'\1', command)
            if re.match(r'^.*(-ar\s+\d+).*$', f):
                command = command.replace(f, '').strip()
            if text != 'No Change':
                command += ' -ar {0}'.format(text)

        elif widget == 'audio_bitrate':
            text = self.audio_bitrateComboBox.currentText()
            f = re.sub(r'^.*(-ab\s+\d+k).*$', r'\1', command)
            if re.match(r'^.*(-ab\s+\d+k).*$', f):
                command = command.replace(f, '').strip()
            if text != 'No Change':
                command += ' -ab {0}k'.format(text)

        elif widget in ('channels1', 'channels2'):
            text = self.chan1RadioButton.text() if widget == 'channels1' \
                                            else self.chan2RadioButton.text()
            f = re.sub(r'^.*(-ac\s+\d+).*$', r'\1', command)
            if re.match(r'^.*(-ac\s+\d+).*$', f):
                command = command.replace(f, '').strip()
            command += ' -ac {0}'.format(text)

        self.commandLineEdit.clear()
        self.commandLineEdit.setText(self.remove_consecutive_spaces(command))

    def duration_in_seconds(self, duration):
        """Gets a time of type: hh:mm:ss.ts and return the number of seconds.

        Return: integer
        """
        duration = duration.split('.')[0]
        hours, mins, secs = duration.split(':')
        seconds = int(secs)
        seconds += (int(hours) * 3600) + (int(mins) * 60)
        return seconds

    def convert(self, parent, from_file, to_file, command, ffmpeg):
        """Converts an audio/video file and keep log of conversion.

        Returns: boolean
        """
        assert isinstance(from_file, unicode) and isinstance(to_file, unicode)
        assert from_file.startswith('"') and from_file.endswith('"')
        assert to_file.startswith('"') and to_file.endswith('"')

        converter = 'ffmpeg' if ffmpeg else 'avconv'
        convert_cmd = '{0} -y -i {1} {2} {3}'.format(converter, from_file,
                                                              command, to_file)
        convert_cmd = str(QString(convert_cmd).toUtf8())
        parent.update_text_edit_signal.emit(unicode(convert_cmd, 'utf-8')+'\n')

        self.process = subprocess.Popen(shlex.split(convert_cmd),
                              stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

        final_output = myline = str('')
        while True:
            out = str(QString(self.process.stdout.read(1)).toUtf8())
            if out == str('') and self.process.poll() != None:
                break

            myline += out
            if out in (str('\r'), str('\n')):
                m = re.search("Duration: ([0-9:.]+), start: [0-9.]+", myline)
                if m:
                    total = self.duration_in_seconds(m.group(1))
                n = re.search("time=([0-9:]+)", myline)
                #time can be of format 'time=hh:mm:ss.ts' or 'time=ss.ts'
                # depending on ffmpeg version
                if n:
                    time = n.group(1)
                    if ':' in time:
                        time = self.duration_in_seconds(time)
                    now_sec = int(float(time))
                    try:
                        parent.refr_bars_signal.emit(100 * now_sec / total)
                    except ZeroDivisionError:
                        pass
                parent.update_text_edit_signal.emit(myline)
                final_output += myline
                myline = str('')
        parent.update_text_edit_signal.emit('\n\n')

        return_code = self.process.poll()

        log_data = {'command' : unicode(convert_cmd, 'utf-8'),
                    'returncode' : return_code, 'type' : 'VIDEO'}
        log_lvl = logging.info if return_code == 0 else logging.error
        log_lvl(unicode(final_output, 'utf-8'), extra=log_data)

        return return_code == 0


class ImageTab(QWidget):
    def __init__(self, parent):
        super(ImageTab, self).__init__(parent)
        self.parent = parent
        self.name = 'Images'
        self.formats = ['bmp', 'cgm', 'dpx', 'emf', 'eps', 'fpx', 'gif',
                        'jbig', 'jng', 'jpeg', 'mrsid', 'p7', 'pdf', 'picon',
                        'png', 'ppm', 'psd', 'rad', 'tga', 'tif','webp', 'xpm']

        self.extra_img = ['bmp2', 'bmp3', 'dib', 'epdf', 'epi', 'eps2', 'eps3',
                          'epsf', 'epsi', 'icon', 'jpe', 'jpg', 'pgm', 'png24',
                          'png32', 'pnm', 'ps', 'ps2', 'ps3', 'sid', 'tiff']

        pattern = QRegExp(r'^[1-9]\d*')
        validator = QRegExpValidator(pattern, self)


        converttoLabel = QLabel(self.tr('Convert to:'))
        self.extComboBox = QComboBox()
        self.extComboBox.addItems(self.formats)

        hlayout1 = pyqttools.add_to_layout(QHBoxLayout(), converttoLabel,
                                                        self.extComboBox, None)

        sizeLabel = QLabel(self.tr('Image Size:'))
        self.widthLineEdit = pyqttools.create_LineEdit((50, 16777215),
                                                                  validator, 4)
        self.heightLineEdit = pyqttools.create_LineEdit((50, 16777215),
                                                                   validator,4)
        label = QLabel('x')
        label.setMaximumWidth(25)
        hlayout2 = pyqttools.add_to_layout(QHBoxLayout(), sizeLabel,
                          self.widthLineEdit, label, self.heightLineEdit, None)
        final_layout = pyqttools.add_to_layout(QVBoxLayout(),hlayout1,hlayout2)
        self.setLayout(final_layout)

    def clear(self):
        """Clear lineEdits"""
        self.widthLineEdit.clear()
        self.heightLineEdit.clear()

    def ok_to_continue(self):
        """Checks if everything is ok with imagetab to continue conversion

        Checks if:
        - There are missing dependencies
        - Given file can be converted
        - One lineEdit is active and its pair is empty

        Returns: boolean
        """
        file_ext = os.path.splitext(self.parent.fname)[-1][1:]
        width = self.widthLineEdit.text()
        height = self.heightLineEdit.text()

        if not self.parent.pmagick:
            QMessageBox.warning(self, 'FF Multi Converter - ' + self.tr(
                'Error!'), self.tr('PythonMagick is not installed.\nYou will '
                'not be able to convert image files until you install it.'))
            return False
        if not file_ext in self.formats and not file_ext in self.extra_img:
            QMessageBox.warning(self, 'FF Multi Converter - ' + self.tr(
                'Error!'), self.tr('Could not convert this file type!'))
            return False
        if (width and not height) or (not width and height):
            QMessageBox.warning(self, 'FF Multi Converter - ' + self.tr(
                'Error!'), self.tr('The size LineEdit may not be empty.'))
            self.heightLineEdit.setFocus() if width and not height else \
                                                  self.widthLineEdit.setFocus()
            return False
        return True

    def convert(self, parent, from_file, to_file):
        """Converts an image and keeps log of conversion.

        Returns: boolean
        """
        assert isinstance(from_file, unicode) and isinstance(to_file, unicode)
        assert from_file.startswith('"') and from_file.endswith('"')
        assert to_file.startswith('"') and to_file.endswith('"')

        if not self.widthLineEdit.text():
            size = ''
        else:
            width = self.widthLineEdit.text()
            height = self.heightLineEdit.text()
            size = str('{0}x{1}'.format(width, height))

        from_file = str(QString(from_file).toUtf8())[1:-1]
        to_file = str(QString(to_file).toUtf8())[1:-1]

        command = 'from {0} to {1}'.format(unicode(from_file, 'utf-8'),
                                           unicode(to_file, 'utf-8'))
        if size: command += ' -s ' + size
        parent.update_text_edit_signal.emit(command+'\n')
        final_output = ''

        try:
            if os.path.exists(to_file):
                os.remove(to_file)
            img = PythonMagick.Image(from_file)
            if size:
                img.transform(size)
            img.write(to_file)
            converted = True
        except (RuntimeError, OSError, Exception) as e:
            final_output = str(e)
            parent.update_text_edit_signal.emit(final_output)
            converted = False
        parent.update_text_edit_signal.emit('\n\n')

        log_data = {'command' : command, 'returncode' : int (not converted),
                    'type' : 'IMAGE'}
        log_lvl = logging.info if converted == 1 else logging.error
        log_lvl(final_output, extra=log_data)

        return converted


class DocumentTab(QWidget):
    def __init__(self, parent):
        self.parent = parent
        super(DocumentTab, self).__init__(parent)
        self.name = 'Documents'
        self.formats = { 'doc' : ['odt', 'pdf'],
                     'html' : ['odt'],
                     'odp' : ['pdf', 'ppt'],
                     'ods' : ['pdf'],
                     'odt' : ['doc', 'html', 'pdf', 'rtf', 'sxw', 'txt','xml'],
                     'ppt' : ['odp'],
                     'rtf' : ['odt'],
                     'sdw' : ['odt'],
                     'sxw' : ['odt'],
                     'txt' : ['odt'],
                     'xls' : ['ods'],
                     'xml' : ['doc', 'odt', 'pdf']
                    }

        flist = []
        for i in self.formats:
            for y in self.formats[i]:
                flist.append(i + ' to ' + y)
        flist.sort()

        convertLabel = QLabel(self.tr('Convert:'))
        self.convertComboBox = QComboBox()
        self.convertComboBox.addItems(flist)
        final_layout = pyqttools.add_to_layout(QHBoxLayout(), convertLabel,
                                                    self.convertComboBox, None)
        self.setLayout(final_layout)

    def ok_to_continue(self):
        """Checks if everything is ok with documenttab to continue conversion

        Checks if:
        - There are missing dependencies
        - Given file extension is same with the declared extension

        Returns: boolean
        """
        file_ext = os.path.splitext(self.parent.fname)[-1][1:]
        decl_ext = self.convertComboBox.currentText().split(' ')[0]

        try:
            if not self.parent.unoconv:
                raise ValidationError(self.tr(
                       'Unocov is not installed.\nYou will not be able '
                       'to convert document files until you install it.'))
            if file_ext != decl_ext:
                raise ValidationError(self.tr(
                                    'Given file is not %1!').arg(decl_ext))
            return True

        except ValidationError as e:
            QMessageBox.warning(self, 'FF Multi Converter - ' + \
                                                 self.tr('Error!'), unicode(e))
            return False

    def convert(self, parent, from_file, to_file):
        """Converts a document and keeps log of conversion.

        Returns: boolean
        """
        assert isinstance(from_file, unicode) and isinstance(to_file, unicode)

        from_file = from_file[1:-1]
        to_file = to_file[1:-1]
        _file, extension = os.path.splitext(to_file)
        moved_file = _file + os.path.splitext(from_file)[-1]
        if os.path.exists(moved_file):
            moved_file = _file + '~~' + os.path.splitext(from_file)[-1]
        shutil.copy(from_file, moved_file)

        command = 'unoconv --format={0} {1}'.format(
                                            extension[1:], '"'+moved_file+'"')
        command = str(QString(command).toUtf8())
        parent.update_text_edit_signal.emit(unicode(command, 'utf-8')+'\n')

        child = subprocess.Popen(shlex.split(command),
                             stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        child.wait()

        os.remove(moved_file)
        final_file = os.path.splitext(moved_file)[0] + extension
        shutil.move(final_file, to_file)

        final_output = unicode(child.stdout.read(), 'utf-8')
        parent.update_text_edit_signal.emit(final_output+'\n\n')

        return_code = child.poll()

        log_data = {'command' : unicode(command, 'utf-8'),
                    'returncode' : return_code, 'type' : 'DOCUMENT'}
        log_lvl = logging.info if return_code == 0 else logging.error
        log_lvl(final_output, extra=log_data)

        return return_code == 0


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName('ffmulticonverter')
    app.setOrganizationDomain('sites.google.com/site/ffmulticonverter/')
    app.setApplicationName('FF Muli Converter')
    app.setWindowIcon(QIcon(':/ffmulticonverter.png'))

    locale = QLocale.system().name()
    qtTranslator = QTranslator()
    if qtTranslator.load('qt_' + locale, ':/'):
        app.installTranslator(qtTranslator)
    appTranslator = QTranslator()
    if appTranslator.load('ffmulticonverter_' + locale, ':/'):
        app.installTranslator(appTranslator)

    converter = MainWindow()
    converter.show()
    app.exec_()

if __name__ == '__main__':
    main()
