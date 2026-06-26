import ctypes
import json
import os
import subprocess
import time

import Code
from Code import Util
from Code.QT import Iconos


# Install: Wbase #90
# Assign toolbar: Wbase #132


class Eboard:
    def __init__(self):
        self.name = Code.configuration.x_digital_board
        self.driver = None
        self.setup = False
        self.fen_eboard = None
        self.dispatch = None
        self.allowHumanTB = False
        self.working_time = None
        self.side_takeback = None
        self.dgt3000_clock_started = False
        self.dgt3000_clock_process = None
        self.dgt3000_clock_sequence = 0
        self.dgt3000_pending_move = None
        self.dgt3000_last_button_sequence = 0
        self.dgt3000_human_side = None
        self.dgt3000_seen_human_move = False

    def is_working(self):
        return self.working_time is not None and 1.0 > (time.time() - self.working_time)

    def set_working(self):
        self.working_time = time.time()

    def envia(self, quien, dato):
        # assert prln("envia", quien, dato, self.dispatch)
        return self.dispatch(quien, dato)

    def set_position(self, position):
        # assert prln("set position", position.fen())
        if self.driver:
            if (self.name == "DGT") or (
                    self.name == "Novag UCB" and Code.configuration.x_digital_board_version == 0
            ):
                self.write_position(position.fen_dgt())
            else:
                self.write_position(position.fen())

    @staticmethod
    def log(cad):
        import traceback

        with open("dgt.log", "at", encoding="utf-8", errors="ignore") as q:
            q.write("\n[%s] %s\n" % (Util.today(), cad))
            for line in traceback.format_stack():
                q.write("    %s\n" % line.strip())

    def registerStatusFunc(self, dato):
        # assert prln("registerStatusFunc", dato)
        self.envia("status", dato)
        return 1

    def registerScanFunc(self, dato):
        # assert prln("registerScanFunc", dato)
        self.envia("scan", self.dgt2fen(dato))
        return 1

    def registerStartSetupFunc(self):
        # assert prln("registerStartSetupFunc")
        self.setup = True
        return 1

    def registerStableBoardFunc(self, dato):
        # assert prln("registerStableBoardFunc", dato, self.setup)
        self.fen_eboard = self.dgt2fen(dato)
        if self.setup:
            self.envia("stableBoard", self.fen_eboard)
        return 1

    def registerStopSetupWTMFunc(self, dato):
        # assert prln("registerStopSetupWTMFunc", dato)
        if self.setup:
            self.envia("stopSetupWTM", self.dgt2fen(dato))
            self.setup = False
        return 1

    def registerStopSetupBTMFunc(self, dato):
        # assert prln("registerStopSetupBTMFunc", dato)
        if self.setup:
            self.envia("stopSetupBTM", self.dgt2fen(dato))
            self.setup = False
        return 1

    def registerWhiteMoveInputFunc(self, dato):
        # assert prln("registerWhiteMoveInputFunc", dato)
        if self.name == "Chessnut":
            pv = self.dgt2pv(dato)
            self.dgt3000_human_side = "white"
            self.dgt3000_seen_human_move = True
            self.dgt3000_pending_move = ("whiteMove", pv)
            self.log("DGT3000 pending human move: %s" % pv)
            return 1
        return self.envia("whiteMove", self.dgt2pv(dato))

    def registerBlackMoveInputFunc(self, dato):
        # assert prln("registerBlackMoveInputFunc", dato)
        pv = self.dgt2pv(dato)
        if self.name == "Chessnut":
            self.dgt3000_human_side = "black"
            self.dgt3000_seen_human_move = True
            self.dgt3000_pending_move = ("blackMove", pv)
            self.log("DGT3000 pending human move: %s" % pv)
            return 1
        return self.envia("blackMove", pv)

    def registerWhiteTakeBackFunc(self):
        # assert prln("registerWhiteTakeBackFunc")
        return self.envia("whiteTakeBack", True)

    def registerBlackTakeBackFunc(self):
        # assert prln("registerBlackTakeBackFunc")
        return self.envia("blackTakeBack", True)

    def activate(self, dispatch):
        # assert prln("activate")
        self.fen_eboard = None
        self.driver = driver = None
        self.side_takeback = None
        self.dispatch = dispatch
        self.dgt3000_human_side = None
        self.dgt3000_seen_human_move = False
        self.dgt3000_last_button_sequence = self.read_dgt3000_button_sequence()

        path_eboards = Util.opj(Code.folder_OS, "DigitalBoards")
        os.chdir(path_eboards)

        if Code.is_linux:
            functype = ctypes.CFUNCTYPE
            if self.name == "DGT-gon":
                path_so = Util.opj(path_eboards, "libdgt.so")
            elif self.name == "Certabo":
                path_so = Util.opj(path_eboards, "libcer.so")
            elif self.name == "Chessnut":
                path_so = Util.opj(path_eboards, "libnut.so")
            elif self.name == "Pegasus":
                path_so = Util.opj(path_eboards, "libpeg.so")
            elif self.name == "Millennium":
                path_so = Util.opj(path_eboards, "libmcl.so")
            elif self.name == "Citrine":
                path_so = Util.opj(path_eboards, "libcit.so")
            elif self.name == "Saitek":
                path_so = Util.opj(path_eboards, "libosa.so")
            elif self.name == "Square Off":
                path_so = Util.opj(path_eboards, "libsop.so")
            elif self.name == "Tabutronic":
                path_so = Util.opj(path_eboards, "libtab.so")
            elif self.name == "iChessOne":
                path_so = Util.opj(path_eboards, "libico.so")
            elif self.name == "Chessnut Evo":
                path_so = Util.opj(path_eboards, "libevo.so")
            elif self.name == "HOS Sensory":
                path_so = Util.opj(path_eboards, "libhos.so")
            elif self.name == "Chessnut Move":
                path_so = Util.opj(path_eboards, "libmov.so")
            elif self.name == "Cynus":
                path_so = Util.opj(path_eboards, "libcyn.so")
            else:
                path_so = Util.opj(path_eboards, "libucb.so")
            if os.path.isfile(path_so):
                try:
                    driver = ctypes.CDLL(path_so)
                except:
                    driver = None
                    from Code.QT import QTUtil2

                    if self.name.startswith("Chessnut"):
                        QTUtil2.message(
                            None,
                            """It is not possible to install the driver for the board, one way to solve the problem is to install the libraries:
    sudo apt install libqt5pas1
    sudo apt install libhidapi-dev
    or
    sudo dnf install qt5pas-devel
    sudo dnf install hidapi-devel""",
                        )
                    else:
                        QTUtil2.message(
                            None,
                            """It is not possible to install the driver for the board, one way to solve the problem is to install the libraries:
    sudo apt install libqt5pas1
    or
    sudo dnf install qt5pas-devel""",
                        )

        else:
            functype = ctypes.WINFUNCTYPE
            path_eboards = Util.opj(Code.folder_OS, "DigitalBoards")

            if self.name == "DGT":
                for folder_dll_dgt in (
                        "C:/Program Files (x86)/DGT/DGT e-Board drivers",
                        "C:/Program Files (x86)/DGT/DGT e-Board drivers/Applications/RabbitPlugin/32bit/Common Files",
                        "C:/Program Files (x86)/DGT Projects/",
                        "C:/Program Files (x86)/Common Files/DGT Projects/",
                        "C:/Program Files/DGT Projects/",
                        "C:/Program Files/Common Files/DGT Projects/",
                        "",
                        path_eboards):
                    path_dll = Util.opj(folder_dll_dgt, "DGTEBDLL.dll")
                    if os.path.isfile(path_dll):
                        try:
                            os.chdir(os.path.dirname(folder_dll_dgt))
                            driver = ctypes.WinDLL(path_dll)
                            break
                        except:
                            pass
            else:
                if self.name == "Certabo":
                    path_dll = Util.opj(path_eboards, "CER_DLL.dll")
                elif self.name == "Chessnut":
                    path_dll = Util.opj(path_eboards, "NUT_DLL.dll")
                elif self.name == "DGT-gon":
                    path_dll = Util.opj(path_eboards, "DGT_DLL.dll")
                elif self.name == "Pegasus":
                    path_dll = Util.opj(path_eboards, "PEG_DLL.dll")
                elif self.name == "Millennium":
                    path_dll = Util.opj(path_eboards, "MCL_DLL.dll")
                elif self.name == "Citrine":
                    path_dll = Util.opj(path_eboards, "CIT_DLL.dll")
                elif self.name == "Saitek":
                    path_dll = Util.opj(path_eboards, "OSA_DLL.dll")
                elif self.name == "Square Off":
                    path_dll = Util.opj(path_eboards, "SOP_DLL.dll")
                elif self.name == "Tabutronic":
                    path_dll = Util.opj(path_eboards, "TAB_DLL.dll")
                elif self.name == "iChessOne":
                    path_dll = Util.opj(path_eboards, "ICO_DLL.dll")
                elif self.name == "Chessnut Evo":
                    path_dll = Util.opj(path_eboards, "EVO_DLL.dll")
                elif self.name == "HOS Sensory":
                    path_dll = Util.opj(path_eboards, "HOS_DLL.dll")
                elif self.name == "Chessnut Move":
                    path_dll = Util.opj(path_eboards, "MOV_DLL.dll")
                elif self.name == "Cynus":
                    path_dll = Util.opj(path_eboards, "CYN_DLL.dll")
                else:
                    path_dll = Util.opj(path_eboards, "UCB_DLL.dll")
                if os.path.isfile(path_dll):
                    try:
                        driver = ctypes.WinDLL(path_dll)
                    except:
                        pass

        if driver is None:
            os.chdir(Code.current_dir)
            return False

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStatusFunc)
        driver._DGTDLL_RegisterStatusFunc.argtype = [st]
        driver._DGTDLL_RegisterStatusFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStatusFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerScanFunc)
        driver._DGTDLL_RegisterScanFunc.argtype = [st]
        driver._DGTDLL_RegisterScanFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterScanFunc(st)

        cmpfunc = functype(ctypes.c_int)
        st = cmpfunc(self.registerStartSetupFunc)
        driver._DGTDLL_RegisterStartSetupFunc.argtype = [st]
        driver._DGTDLL_RegisterStartSetupFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStartSetupFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStableBoardFunc)
        driver._DGTDLL_RegisterStableBoardFunc.argtype = [st]
        driver._DGTDLL_RegisterStableBoardFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStableBoardFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStopSetupWTMFunc)
        driver._DGTDLL_RegisterStopSetupWTMFunc.argtype = [st]
        driver._DGTDLL_RegisterStopSetupWTMFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStopSetupWTMFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStopSetupBTMFunc)
        driver._DGTDLL_RegisterStopSetupBTMFunc.argtype = [st]
        driver._DGTDLL_RegisterStopSetupBTMFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStopSetupBTMFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerWhiteMoveInputFunc)
        driver._DGTDLL_RegisterWhiteMoveInputFunc.argtype = [st]
        driver._DGTDLL_RegisterWhiteMoveInputFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterWhiteMoveInputFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerBlackMoveInputFunc)
        driver._DGTDLL_RegisterBlackMoveInputFunc.argtype = [st]
        driver._DGTDLL_RegisterBlackMoveInputFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterBlackMoveInputFunc(st)

        driver._DGTDLL_WritePosition.argtype = [ctypes.c_char_p]
        driver._DGTDLL_WritePosition.restype = ctypes.c_int

        driver._DGTDLL_ShowDialog.argtype = [ctypes.c_int]
        driver._DGTDLL_ShowDialog.restype = ctypes.c_int

        driver._DGTDLL_HideDialog.argtype = [ctypes.c_int]
        driver._DGTDLL_HideDialog.restype = ctypes.c_int

        driver._DGTDLL_WriteDebug.argtype = [ctypes.c_bool]
        driver._DGTDLL_WriteDebug.restype = ctypes.c_int

        driver._DGTDLL_SetNRun.argtype = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        driver._DGTDLL_SetNRun.restype = ctypes.c_int

        if self.name != "DGT":
            driver._DGTDLL_GetVersion.argtype = []
            driver._DGTDLL_GetVersion.restype = ctypes.c_int
            Code.configuration.x_digital_board_version = driver._DGTDLL_GetVersion()
            try:
                driver._DGTDLL_AllowTakebacks.argtype = [ctypes.c_bool]
                driver._DGTDLL_AllowTakebacks.restype = ctypes.c_int
                driver._DGTDLL_AllowTakebacks(ctypes.c_bool(True))
                cmpfunc = functype(ctypes.c_int)
                st = cmpfunc(self.registerWhiteTakeBackFunc)
                driver._DGTDLL_RegisterWhiteTakebackFunc.argtype = [st]
                driver._DGTDLL_RegisterWhiteTakebackFunc.restype = ctypes.c_int
                driver._DGTDLL_RegisterWhiteTakebackFunc(st)
                cmpfunc = functype(ctypes.c_int)
                st = cmpfunc(self.registerBlackTakeBackFunc)
                driver._DGTDLL_RegisterBlackTakebackFunc.argtype = [st]
                driver._DGTDLL_RegisterBlackTakebackFunc.restype = ctypes.c_int
                driver._DGTDLL_RegisterBlackTakebackFunc(st)
            except:
                pass

        driver._DGTDLL_ShowDialog(ctypes.c_int(1))

        os.chdir(Code.current_dir)
        self.driver = driver
        if self.name == "Chessnut":
            self.start_dgt3000_clock_sidecar()
        return True

    def deactivate(self):
        # assert prln("deactivate", self.driver)
        if self.dgt3000_clock_process is not None:
            try:
                self.dgt3000_clock_process.terminate()
            except Exception:
                pass
            self.dgt3000_clock_process = None
            self.dgt3000_clock_started = False

        if self.driver:
            self.driver._DGTDLL_HideDialog(ctypes.c_int(1))
            self.setup = False
            if Code.is_windows:
                handle = self.driver._handle
                ctypes.windll.kernel32.FreeLibrary(handle)

            del self.driver
            self.driver = None
            return True
        return False

    def show_dialog(self):
        # assert prln("showdialog")
        if self.driver:
            self.driver._DGTDLL_ShowDialog(ctypes.c_int(1))

    def write_debug(self, activar):
        # assert prln("writeDebug")
        if self.driver:
            self.driver._DGTDLL_WriteDebug(activar)

    def write_position(self, cposicion):
        # assert prln("write_position", cposicion, self.fen_eboard)
        if self.driver and cposicion != self.fen_eboard:
            # log( "Enviado a la DGT" + cposicion )
            self.driver._DGTDLL_WritePosition(cposicion.encode())
            self.fen_eboard = cposicion
            self.envia("stableBoard", cposicion.encode())
            Code.eboard.allowHumanTB = False
            if self.name == "Chessnut":
                self.write_dgt3000_position_event(cposicion)

    def writeClocks(self, wclock, bclock):
        # assert prln("writeclocks")
        if self.driver:
            if self.name in ("DGT", "DGT-gon"):
                # log( "WriteClocks: W-%s B-%s"%(str(wclock), str(bclock)) )
                self.driver._DGTDLL_SetNRun(wclock.encode(), bclock.encode(), 0)
            elif self.name == "Chessnut":
                self.poll_dgt3000_button()
                self.dgt3000_clock_started = self.write_dgt3000_clock_once(wclock, bclock)

    @staticmethod
    def clock_seconds(clock_text):
        parts = []
        current = ""
        for ch in str(clock_text):
            if ch.isdigit():
                current += ch
            elif current:
                parts.append(int(current))
                current = ""
        if current:
            parts.append(int(current))
        if len(parts) >= 3:
            # Lucas may append increment/move data after HH:MM:SS. Use the first
            # clock triplet, not the last three numbers.
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 1:
            return parts[0]
        return 0

    def write_dgt3000_clock_once(self, wclock, bclock):
        white = self.clock_seconds(wclock)
        black = self.clock_seconds(bclock)
        if white <= 0 and black <= 0:
            return False

        human_side = self.dgt3000_human_side or "white"
        if human_side == "black":
            left = white
            right = black
        else:
            left = black
            right = white

        def fields(seconds, prefix):
            return {
                prefix + "Mode": 1 if seconds > 0 else 0,
                prefix + "Hours": seconds // 3600,
                prefix + "Minutes": (seconds // 60) % 60,
                prefix + "Seconds": seconds % 60,
            }

        params = {}
        params.update(fields(left, "left"))
        params.update(fields(right, "right"))
        request = {
            "event": "clock",
            "setTime": True,
            "run": True,
            "params": params,
            "humanSide": human_side,
            "rawWhite": str(wclock),
            "rawBlack": str(bclock),
            "writtenAt": time.time(),
        }

        try:
            request_path, _stdout_path, _stderr_path, _button_path = self.dgt3000_clock_paths()
            with open(request_path, "wt", encoding="utf-8") as q:
                json.dump(request, q)

            self.start_dgt3000_clock_sidecar(request)
            return True
        except Exception as exc:
            self.log("DGT3000 clock sync failed: %s" % exc)
            return True

    def write_dgt3000_position_event(self, fen):
        try:
            if not self.dgt3000_seen_human_move and self.dgt3000_human_side is None:
                self.dgt3000_human_side = "black"
            request_path, _stdout_path, _stderr_path, _button_path = self.dgt3000_clock_paths()
            self.dgt3000_clock_sequence += 1
            request = {
                "event": "engine_position",
                "fen": fen,
                "humanSide": self.dgt3000_human_side or "white",
                "sequence": self.dgt3000_clock_sequence,
                "writtenAt": time.time(),
            }
            with open(request_path, "wt", encoding="utf-8") as q:
                json.dump(request, q)
            self.start_dgt3000_clock_sidecar()
        except Exception as exc:
            self.log("DGT3000 position event failed: %s" % exc)

    def dgt3000_clock_paths(self):
        local_app_data = os.environ.get("LOCALAPPDATA", Code.current_dir)
        folder = Util.opj(local_app_data, "LucasChessnutDGT3000Bridge")
        os.makedirs(folder, exist_ok=True)
        return (
            Util.opj(folder, "clock_request.json"),
            Util.opj(folder, "sidecar.stdout.log"),
            Util.opj(folder, "sidecar.stderr.log"),
            Util.opj(folder, "clock_button.json"),
        )

    def start_dgt3000_clock_sidecar(self, request=None):
        try:
            if self.dgt3000_clock_process is not None and self.dgt3000_clock_process.poll() is None:
                return True

            request_path, stdout_path, stderr_path, button_path = self.dgt3000_clock_paths()
            script = Util.opj(Code.folder_OS, "DigitalBoards", "dgt3000_ble_sidecar.py")
            if not os.path.isfile(script):
                self.log("DGT3000 sidecar not found: %s" % script)
                return False

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            stdout_file = open(stdout_path, "at", encoding="utf-8", errors="ignore")
            stderr_file = open(stderr_path, "at", encoding="utf-8", errors="ignore")
            self.dgt3000_clock_process = subprocess.Popen(
                ["python", script, "--watch-clock-file", request_path, "--button-file", button_path],
                stdout=stdout_file,
                stderr=stderr_file,
                creationflags=creationflags,
            )
            time.sleep(0.5)
            rc = self.dgt3000_clock_process.poll()
            if request is None:
                self.log("DGT3000 clock sidecar launched pid=%s rc=%s" % (self.dgt3000_clock_process.pid, rc))
            else:
                self.log("DGT3000 clock sidecar launched pid=%s rc=%s request=%s" % (
                    self.dgt3000_clock_process.pid, rc, json.dumps(request)
                ))
            return True
        except Exception as exc:
            self.log("DGT3000 sidecar launch failed: %s" % exc)
            return False

    def read_dgt3000_button_sequence(self):
        try:
            _request_path, _stdout_path, _stderr_path, button_path = self.dgt3000_clock_paths()
            if os.path.isfile(button_path):
                with open(button_path, "rt", encoding="utf-8") as q:
                    event = json.load(q)
                return int(event.get("sequence", 0))
        except Exception:
            pass
        return 0

    def poll_dgt3000_button(self):
        try:
            sequence = self.read_dgt3000_button_sequence()
            if sequence > self.dgt3000_last_button_sequence:
                self.dgt3000_last_button_sequence = sequence
                self.accept_dgt3000_pending_move(sequence)
        except Exception as exc:
            self.log("DGT3000 button poll failed: %s" % exc)

    def accept_dgt3000_pending_move(self, sequence):
        pending = self.dgt3000_pending_move
        if pending is None:
            self.log("DGT3000 lever_right without pending move sequence=%s" % sequence)
            return
        self.dgt3000_pending_move = None
        quien, pv = pending
        self.log("DGT3000 accepting pending move sequence=%s %s=%s" % (sequence, quien, pv))
        self.envia(quien, pv)

    @staticmethod
    def dgt2fen(datobyte):
        n = 0
        dato = datobyte.decode()
        ndato = len(dato)
        caja = [""] * 8
        ncaja = 0
        ntam = 0
        while True:
            if dato[n].isdigit():
                num = int(dato[n])
                if (n + 1 < ndato) and dato[n + 1].isdigit():
                    num = num * 10 + int(dato[n + 1])
                    n += 1
                while num:
                    pte = 8 - ntam
                    if num >= pte:
                        caja[ncaja] += str(pte)
                        ncaja += 1
                        ntam = 0
                        num -= pte
                    else:
                        caja[ncaja] += str(num)
                        ntam += num
                        break

            else:
                caja[ncaja] += dato[n]
                ntam += 1
            if ntam == 8:
                ncaja += 1
                ntam = 0
            n += 1
            if n == ndato:
                break
        if ncaja != 8:
            caja[7] += str(8 - ntam)
        return "/".join(caja)

    @staticmethod
    def dgt2pv(datobyte):
        dato = datobyte.decode()
        # Coronacion
        if dato[0] in "Pp" and dato[3].lower() != "p":
            return dato[1:3] + dato[4:6] + dato[3].lower()

        return dato[1:3] + dato[4:6]

    def icon_eboard(self):
        board = self.name
        if board == "DGT":
            return Iconos.DGT()
        elif board in ("DGT-gon", "Pegasus"):
            return Iconos.DGTB()
        elif board == "Certabo":
            return Iconos.Certabo()
        elif board == "Chessnut":
            return Iconos.Chessnut()
        elif board == "Chessnut Evo":
            return Iconos.Chessnut()
        elif board == "Chessnut Move":
            return Iconos.Chessnut()
        elif board == "Cynus":
            return Iconos.Manya()
        elif board == "HOS Sensory":
            return Iconos.HOS()
        elif board == "iChessOne":
            return Iconos.IChessOne()
        elif board == "Millennium":
            return Iconos.Millenium()
        elif board == "Saitek":
            return Iconos.Saitek()
        elif board == "Square Off":
            return Iconos.SquareOff()
        elif board == "Tabutronic":
            return Iconos.Tabutronic()
        else:
            return Iconos.Novag()


def version():
    path_version = Util.opj(Code.folder_OS, "DigitalBoards", "version")
    xversion = "0"
    if os.path.isfile(path_version):
        with open(path_version, "rt") as f:
            xversion = f.read().strip()
    return xversion
