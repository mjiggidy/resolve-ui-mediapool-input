import DaVinciResolveScript as bmd
from mediapoolinput import MPILineEditController, MPILineEditCallbacks

fusion  = bmd.scriptapp("fusion")
resolve = bmd.scriptapp("resolve")

ui         = fusion.UIManager
dispatcher = bmd.UIDispatcher(ui)

win_test = dispatcher.AddWindow({
	"ID": "com.glowingpixel.mediapoolinput-test",
	"FixedSize": [500, 42],
}, [
	ui.LineEdit({
		"ID": "test-linedit",
		"Events": {"TextEdited":True, "EditingFinished":True}
	})
])

mpi_controller = MPILineEditController(
	resolve.GetProjectManager(),
	win_test.Find("test-linedit"),
#	start_folder=resolve.GetProjectManager().GetCurrentProject().GetMediaPool().GetCurrentFolder()
)

mpi_controller.current_folder_info().register_callback(MPILineEditCallbacks.CURRENT_FOLDER_CHANGED, lambda e: print(f"Current folder changed; {e.GetName()}"))
mpi_controller.current_folder_info().register_callback(MPILineEditCallbacks.PATH_VALIDITY_CHANGED,  lambda e: print(f"Path validity changed;  {e}"))

mpi_controller.register_window_handle(win_test)

win_test.On[win_test.ID].Close = lambda e: dispatcher.ExitLoop(0)

win_test.Show()

dispatcher.RunLoop()