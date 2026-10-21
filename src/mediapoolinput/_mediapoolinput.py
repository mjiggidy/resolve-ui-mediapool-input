from __future__ import annotations
import logging, typing

from resolvecommon import folders, formatting

from ._callbacks import MPILineEditCallbacks

if typing.TYPE_CHECKING:
	import DaVinciResolveScript as dvrtypes

_logger = logging.getLogger(__name__)

class _MPIFolderInfo:
	"""Path and subfolder info for a given folder"""

	EXCLUDE_MASTER = True

	def __init__(self, project_manager:dvrtypes.ProjectManager):

		self._project_manager = project_manager
		
		self._folder_handle:dvrtypes.Folder|None = None
		self._folder_path:str   = ""
		
		self._subfolder_is_valid = False

		self._callbacks:dict[MPILineEditCallbacks, list[typing.Callable]] = dict()

		# Register callback types
		for callback in MPILineEditCallbacks:
			self._callbacks[callback] = []

	def _set_folder(self, folder:dvrtypes.Folder) -> bool:
		"""Set the current folder.  Returns `True` if the folder changed since last."""

		if self._folder_handle and self._folder_handle.GetUniqueId() == folder.GetUniqueId():

			_logger.debug("Set current folder ignored because unchanged")
			return False

		self._folder_path   = self._format_folder_path(folders.get_path_from_folder(folder))
		self._folder_handle = folder

		self._send_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, folder)

		return True

	def _format_folder_path(self, folder_path_raw:str) -> str:
		"""Format folder string for display"""

		if self.EXCLUDE_MASTER and folder_path_raw.startswith("/Master"):
			return folder_path_raw[len("/Master/"):]

		else:
			return folder_path_raw

	def _set_folder_path(self, folder_path:str) -> bool:
		"""Set the current folder from a given path string.  Returns `True` if the folder changed since last."""

		if self._folder_path == folder_path:
			return False
		
		root_folder = self._project_manager.GetCurrentProject().GetMediaPool().GetRootFolder()
		
		self._folder_handle = folders.get_folder_from_path(folder_path, root_folder)
		self._folder_path   = self._format_folder_path(folder_path)

		self._send_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, self._folder_handle)

		return True

	def _validate_subfolder_name(self, subfolder_name:str) -> bool:
		"""Check the full path, including subfolder, for validity"""

		path_was_valid = self._subfolder_is_valid

		self._subfolder_is_valid = subfolder_name in self.subfolder_names()

		if path_was_valid is not self._subfolder_is_valid:
			self._send_callback(MPILineEditCallbacks.PATH_VALIDITY_CHANGED, self._subfolder_is_valid)

		return self._subfolder_is_valid

	def _clear_folder(self) -> bool:
		"""Clear the current folder.  Returns `True` if this is a change."""

		if not self._folder_handle:
			return False

		self._folder_handle = None
		self._folder_path   = ""

		self._send_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, self._folder_handle)

		return True

	def folder_handle(self) -> dvrtypes.Folder|None:
		"""The current folder handle"""

		return self._folder_handle

	def folder_path(self) -> str:
		"""The current folder"""

		return self._folder_path

	def folder_is_valid(self) -> bool:
		"""Pointing to a valid folder path"""

		return bool(self._folder_handle)

	def subfolder_handles(self) -> list[dvrtypes.Folder]:
		"""List of available subfolder handles"""

		return sorted(
			self._folder_handle.GetSubFolderList(),
			key = lambda f: formatting.format_string_for_natural_sort(f.GetName())
		) if self.folder_is_valid() else []

	def subfolder_names(self) -> list[str]:
		"""A list of all subfolder names, sorted naturally"""

		return [f.GetName() for f in self.subfolder_handles()]

	def subfolder_paths(self) -> list[str]:
		"""List of available subfolder paths"""

#		print("Folder path is ", self.folder_path(), "For base folder", self.folder_handle().GetName())

		print("Folder path:", self.folder_path())

		return [str(self.folder_path() + "/" + f.GetName()).lstrip("/") for f in self.subfolder_handles()]

	def register_callback(self, callback:MPILineEditCallbacks, callback_function:typing.Callable):
		"""Register a callback function"""

		self._callbacks[callback].append(callback_function)

	def _send_callback(self, callback:MPILineEditCallbacks, args:typing.Any=None):

		for cb in self._callbacks[callback]:
			cb(args)
		

class MPILineEditController:
	"""Transforms a LineEdit into a Media Pool Input"""

	def __init__(self, project_manager:dvrtypes.ProjectManager, line_edit:object):

		self._folder_tracker   = _MPIFolderInfo(project_manager)

		self._line_edit        = line_edit
		self._last_edit_length = len(self._line_edit.Text)

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