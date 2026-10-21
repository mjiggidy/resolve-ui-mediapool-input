import enum

class MPILineEditCallbacks(enum.Enum):
	"""Available callbacks from Media Pool Input folder info"""

	CURRENT_FOLDER_CHANGED = enum.auto()
	"""The current folder has changed"""

	PATH_VALIDITY_CHANGED = enum.auto()
	"""The full path including subfolder is valid or not"""