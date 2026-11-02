from __future__ import annotations
import logging, typing

from ._folderinfo import _MPIFolderInfo

if typing.TYPE_CHECKING:
	import DaVinciResolveScript as dvrtypes

_logger = logging.getLogger(__name__)

class MPILineEditController:
	"""Transforms a LineEdit into a Media Pool Input"""

	def __init__(self,
	    project_manager:dvrtypes.ProjectManager,
		line_edit:object,
#		/,
#		start_folder:dvrtypes.Folder|None=None
	):

		self._folder_tracker   = _MPIFolderInfo(project_manager)

		self._line_edit        = line_edit
		self._last_edit_length = 0

#		self.set_path_from_text(
#			self._line_edit.Text,
#			show_autocomplete=False,
#		)

	def register_window_handle(self, window_handle:object):
		"""Register `TextEdited` event with dispatcher window handle"""
		
		# TODO: Figure out how to set TextEdited event on the line edit in the constructor?

		window_handle.On[self._line_edit.ID].TextEdited       = self._on_user_modified_path
		window_handle.On[self._line_edit.ID].EditingFinished  = self._on_user_finished_path

	def current_folder_info(self) -> _MPIFolderInfo:
		"""Info about the current base folder"""

		return self._folder_tracker

	def set_path_from_folder(self, folder:object):
		"""Set the current path from a given media pool folder object"""

		self._folder_tracker._set_folder(folder)

		folder_path = self._folder_tracker.folder_path()

		self.set_path_from_text(folder_path)
		self._line_edit.SelectAll()

	def set_path_from_text(self, path_text:str, show_autocomplete:bool=True):
		"""Set the current path from text, and autocomplete with suggestion"""

		cursor_position = self._line_edit.CursorPosition

		# Prepend a slash to the root folder so that "first-level" folders become the partial folder name when split
		sanitized_text:str = "/" + path_text if not path_text.startswith("/") else path_text
		base_path, partial_folder_name = sanitized_text.rsplit("/", 1)

		try:
			self._folder_tracker._set_folder_path(base_path)
	
		except FileNotFoundError as e:
			
			_logger.error("Invalid media pool folder: %s", e)
			self._folder_tracker._clear_folder()

		# Determine autocomplete for a valid folder path
		if self._folder_tracker.folder_is_valid() and show_autocomplete:
		
			next_subfolder_name = next(
				filter(lambda f: f.startswith(partial_folder_name), self._folder_tracker.subfolder_names()),
				""
			)
			next_subfolder_autocomplete = next_subfolder_name[len(partial_folder_name):]
			
			self._folder_tracker._validate_subfolder_name(next_subfolder_name)

			self._line_edit.Text = path_text + next_subfolder_autocomplete
			self._line_edit.SetSelection(len(self._line_edit.Text), -len(next_subfolder_autocomplete))

		# Set text verbatim if the path is invalid, something other than the current input, or autocomplete is unwanted
		elif self._line_edit.Text != path_text:

			self._folder_tracker._validate_subfolder_name(partial_folder_name)

			self._line_edit.Text = path_text

		# Otherwise restore cursor position (can sometimes lose its offset when a combobox clears its items I guess)
		else:

			self._folder_tracker._validate_subfolder_name(partial_folder_name)
			self._line_edit.SetCursorPosition(cursor_position)

		self._last_edit_length = len(path_text)


		_logger.debug("Edit length set to %s", self._last_edit_length)
	
	def _on_user_finished_path(self, event:dict):
		"""Reformat/standardize user input"""

		self._line_edit.Text = self._line_edit.Text.strip("/")

	def _on_user_modified_path(self, event:dict):
		"""Test event for media pool browser thing"""

		current_edit_length = len(event["Text"])

		# If the user is editing text (either backspacin' or editing in the middle), don't autocomplete

		show_autocomplete = not any([
			current_edit_length <= self._last_edit_length,
			self._line_edit.CursorPosition < current_edit_length,
		])

		self.set_path_from_text(event["Text"], show_autocomplete)