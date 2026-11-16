from __future__ import annotations
import typing, logging
from resolvecommon import folders, formatting

from ._callbacks import MPILineEditCallbacks

if typing.TYPE_CHECKING:
	import DaVinciResolveScript as dvrtypes

_logger = logging.getLogger(__name__)

class _MPIFolderInfo:
	"""Current media pool folder and subfolder info for a given folder"""

	def __init__(self, project_manager:dvrtypes.ProjectManager):

		self._project_manager = project_manager

		self._base_folder_handle:dvrtypes.Folder|None = None
		self._base_folder_path:str = None # TODO: Think of a better way to keep folder_path in an invalid state until set

		self._sub_folder_is_valid = False

		self._callbacks:dict[MPILineEditCallbacks, list[typing.Callable]] = dict()

		# Register callback types
		for callback in MPILineEditCallbacks:
			self._callbacks[callback] = []

	# Callbacks
	
	def register_callback(self, callback:MPILineEditCallbacks, callback_function:typing.Callable):
		"""Register a callback function"""

		self._callbacks[callback].append(callback_function)

	def _send_callback(self, callback:MPILineEditCallbacks, args:typing.Any=None):

		for cb in self._callbacks[callback]:
			cb(args)

	def set_base_folder_handle(self, folder:dvrtypes.Folder) -> bool:
		"""Set the current folder.  Returns `True` if the folder changed since last."""

		if self._base_folder_handle and self._base_folder_handle.GetUniqueId() == folder.GetUniqueId():

			_logger.debug("Set current folder ignored because unchanged")
			return False

		try:
			root_folder = self._project_manager.GetCurrentProject().GetMediaPool().GetRootFolder()
		
		except Exception as e:
		
			_logger.error("Error getting media pool root folder: %s", e, exc_info=True)
			return self.clear_base_folder()
		
		self._base_folder_path   = self._format_folder_path(folders.get_path_from_folder(folder, relative_to=root_folder))
		self._base_folder_handle = folder

		self._send_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, folder)

		return True

	def set_base_folder_path(self, folder_path:str) -> bool:
		"""Set the current folder from a given path string.  Returns `True` if the folder changed since last."""

		if self._base_folder_path == folder_path:
			return False

		try:
			root_folder = self._project_manager.GetCurrentProject().GetMediaPool().GetRootFolder()
		
		except Exception as e:
		
			_logger.error("Error getting media pool root folder: %s", e, exc_info=True)
			return self.clear_base_folder()

		try:
			
			self._base_folder_handle = folders.get_folder_from_path(folder_path, root_folder)
			self._base_folder_path   = self._format_folder_path(folder_path)

		except FileNotFoundError:

			_logger.error("Invalid folder path: %s", folder_path)
			return self.clear_base_folder()

		self._send_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, self._base_folder_handle)

		return True

	def clear_base_folder(self) -> bool:
		"""Clear the current folder.  Returns `True` if this is a change."""

		if not self._base_folder_handle:
			return False

		self._base_folder_handle = None
		self._base_folder_path   = ""

		self._send_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, self._base_folder_handle)

		return True

	def _format_folder_path(self, folder_path_raw:str) -> str:
		"""Format folder string for display"""

		# NOTE: Deprecating?  Not needed after re-implementing `folders.get_path_from_folder`

		return folder_path_raw

	# Base folder getters

	def base_folder_handle(self) -> dvrtypes.Folder|None:
		"""The current folder handle"""

		return self._base_folder_handle

	def base_folder_path(self) -> str:
		"""The current folder"""

		return self._base_folder_path

	def base_folder_is_valid(self) -> bool:
		"""Pointing to a valid folder path"""

		return bool(self._base_folder_handle)

	# Sub folder getters

	def sub_folder_handles(self) -> list[dvrtypes.Folder]:
		"""List of available subfolder handles"""

		return sorted(
			self._base_folder_handle.GetSubFolderList(),
			key = lambda f: formatting.format_string_for_natural_sort(f.GetName())
		) if self.base_folder_is_valid() else []

	def sub_folder_names(self) -> list[str]:
		"""A list of all subfolder names, sorted naturally"""

		return [f.GetName() for f in self.sub_folder_handles()]

	def validate_sub_folder_name(self, subfolder_name:str) -> bool:
		"""Check a given subfolder name exists in the base folder"""

		path_was_valid = self._sub_folder_is_valid

		self._sub_folder_is_valid = subfolder_name in self.sub_folder_names()

		if path_was_valid is not self._sub_folder_is_valid:
			self._send_callback(MPILineEditCallbacks.PATH_VALIDITY_CHANGED, self._sub_folder_is_valid)

		return self._sub_folder_is_valid

	def sub_folder_paths(self) -> list[str]:
		"""List of available subfolder paths"""

		return [str(self.base_folder_path() + "/" + f.GetName()).lstrip("/") for f in self.sub_folder_handles()]

