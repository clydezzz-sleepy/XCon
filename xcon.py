import os
import subprocess
import shutil # To remove directories with files in case there are files or subfolders inside of the parent folder.
import sys
import time
import ast # For safer eval() inputs.
import ctypes
import json
import types
import re
MODULES = {}

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
YELLOW = '\033[33m'
ORANGE = '\033[38;2;255;165;0m'
PINK = '\033[38;2;255;182;193m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
COMMENT = '\033[90m'
UNDERLINE = '\033[4m'

PROTECTED_NAMES = ["downloads", "documents", "pictures", "videos", "music", "contacts", "desktop", "appdata", "onedrive"]
CURRENT_DIR = os.path.abspath(os.getcwd())
SYSTEM_DIRS = [os.path.normcase(os.path.normpath(os.path.abspath(p))) for p in ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",os.path.expanduser("~"), os.getenv("USERPROFILE")] if p]

APPDATA = os.getenv('APPDATA')
XCON_DATA_DIR = os.path.join(APPDATA, "XCon")
os.makedirs(XCON_DATA_DIR, exist_ok=True)
VARS_FILE = os.path.join(XCON_DATA_DIR, "vardecl.json")

LAST = None
DECLARELIST: dict = {}
DECLARELIST = {k: v for k, v in DECLARELIST.items() if not isinstance(v, types.ModuleType)}
PACKAGELIST: list = []
COMMAND_HISTORY = []

def __save_vars():
    print(f"{WARNING}Attempting to save variables inside of {OKCYAN}vardecl.json{WARNING}...{ENDC}")
    try:
        if DECLARELIST == {}:
            if os.path.exists(VARS_FILE):
                os.remove(VARS_FILE)
            print(f"{WARNING}No variables found to save.{ENDC}")
            return
        with open(VARS_FILE, "w") as f:
            json.dump(DECLARELIST, f, indent=2)
        print(f"{OKGREEN}Successfully saved variables inside of {OKCYAN}vardecl.json{OKGREEN}.{ENDC}")
        return
    except Exception as e:
        print(f"{FAIL}An exception has occurred while trying to save variables. Reason:\n\n{ENDC}{e}")
        return

def __load_vars():
    global DECLARELIST
    try:
        if not os.path.exists(VARS_FILE) or os.path.getsize(VARS_FILE) == 0:
            DECLARELIST = {}
            print(f"{WARNING}No variables found to load.{ENDC}")
            return
        with open(VARS_FILE, "r") as f:
            DECLARELIST = json.load(f)
            VARS = ', '.join(f"{OKCYAN}{varname} {OKGREEN}({varval!r})" for varname, varval in DECLARELIST.items())
            print(f"{OKGREEN}{'Variables' if len(DECLARELIST) > 1 else 'Variable'} {VARS} successfully loaded from {OKCYAN}vardecl.json {OKGREEN}at {OKCYAN}{XCON_DATA_DIR}{OKGREEN}.{ENDC}")
            return
    except Exception as e:
        print(f"{FAIL}Failed to load variables from previous session. Reason:\n\n{ENDC}{e}")
        return
    
def __set_volume(LEVEL):
    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume # type: ignore
        DEVICES = AudioUtilities.GetSpeakers()
        INTERFACE = DEVICES.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        VOL = cast(INTERFACE, POINTER(IAudioEndpointVolume))
        LEVEL = max(0, min(100, int(LEVEL)))
        VOL.SetMasterVolumeLevelScalar(LEVEL / 100.0, None)
        print(f"{OKGREEN}System volume successfully set to {ORANGE}{LEVEL}%{OKGREEN}.{ENDC}")
        return
    except Exception as e:
        print(f"{FAIL}Failed to set volume. Reason:\n\n{ENDC}{e}")
        return
    
PYTHON_CONTEXT = {**globals(), **DECLARELIST, **MODULES}
        
def __run_python_block(PROMPT, _BLOCK, *args, **kwargs):
    if PROMPT.startswith("python block !x "):
        _BLOCK = PROMPT.removeprefix("python block !x ").strip()
        COMMAND = []
        if not _BLOCK.endswith(":"):
            print(f"{WARNING}Block must start with a line ending in ':', not '{_BLOCK[-1]}'.{ENDC}")
            return
        COMMAND.append(_BLOCK)
        INDENT = 4
        CURRENT_INDENT = INDENT
        SHOW_COUNTER = 0
        while True:
            line = input(f"{_BLOCK}\n" + " " * CURRENT_INDENT if SHOW_COUNTER == 0 else " " * CURRENT_INDENT).strip()
            SHOW_COUNTER = 1
            if line == "!end":
                break
            COMMAND.append(" " * CURRENT_INDENT + line)
            if line.endswith(":"):
                CURRENT_INDENT += INDENT
            elif (len(line) - len(line.lstrip())) < CURRENT_INDENT - INDENT:
                CURRENT_INDENT = max(INDENT, CURRENT_INDENT - INDENT)
        try:
            CODE = "\n".join(COMMAND)
            print(f"\n{OKBLUE}Executing block:\n{COMMENT}{CODE}{ENDC}")
            exec(CODE, PYTHON_CONTEXT)
            if _BLOCK.startswith("def "):
                FUNCTION = _BLOCK.removeprefix("def ").removesuffix(":")
                print(f"{OKGREEN}Function {FUNCTION} has successfully been defined.{ENDC}") 
            print(f"{OKGREEN}Block finished executing.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}Execution of block failed. Reason:\n\n{e}{ENDC}")
            return

def __empty_bin():
    if os.name != "nt":
        print(f"{WARNING}Emptying the recycle bin is only supported on Windows machines in the console.{ENDC}")
        return
    FLAGS = 0x00000001 | 0x00000002 | 0x00000004
    try:
        print(f"{WARNING}Attempting to clear recycle bin...")
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, FLAGS)
        if result == 0:
            print(f"{OKGREEN}Recycle bin has been cleared successfully.{ENDC}")
        elif result == 1:
            print(f"{OKCYAN}Recycle bin not cleared, as the recycle bin has already been emptied.{ENDC}")
        else:
            print(f"{FAIL}Recycle bin could not be cleared. Error code:\n{result}")
            return
    except Exception as e:
        print(f"{FAIL}An exception has occurred while trying to empty recycle bin. Reason:\n\n{ENDC}{e}")
        return
    return True

def __is_protected(path, msg=True) -> bool:
    NORM = os.path.normcase(os.path.normpath(os.path.abspath(path)))
    path = os.path.abspath(path)
    display_path = os.path.basename(path)
    if msg:
        print(f"{WARNING}Note: {OKCYAN}{display_path} {FAIL}cannot {WARNING}contain a protected system folder inside of it.")
        print(f"{WARNING}[XCON_SECURITY] Checking path: {OKCYAN}{path}{ENDC}")
    if os.path.basename(NORM).lower() in PROTECTED_NAMES:
        return True
    for dir in SYSTEM_DIRS:
        if NORM == dir or NORM.startswith(dir + os.sep):
            return True
    return False

def __is_sensitive(path, msg=True) -> bool:
    NORM = os.path.normcase(os.path.normpath(os.path.abspath(path)))
    path = os.path.abspath(path)
    display_path = os.path.basename(path)
    if msg:
        print(f"{WARNING}Note: {OKCYAN}{display_path} {FAIL}cannot {WARNING}have a protected path affix in it.")
        print(f"{WARNING}[XCON_SECURITY] Checking directory: {OKCYAN}{path}{ENDC}")
    for protected in SYSTEM_DIRS:
        if NORM == protected or NORM.startswith(protected + os.sep):
            return True
    if __is_protected(NORM, False):
        return True
    return False

def __sanitize_context(context):
    SAFE_TYPES = (int, float, str, bool, list, dict, tuple, set, types.ModuleType)
    sanitized = {}
    for k, v in context.items():
        if isinstance(v, SAFE_TYPES):
            sanitized[k] = v
    return sanitized

def __safe_eval(expr, context=None):
    if context is None:
        context = {}
    context = __sanitize_context(context)  # Filter out functions/modules
    GLOBALS = {
        "__builtins__": {
            "True": True,
            "False": False,
            "None": None,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "any": any,
            "all": all,
            "round": round,
        }
    }
    try:
        return eval(expr, GLOBALS, context)
    except Exception as e:
        raise RuntimeError(f"{WARNING}Evaluation failed for expression {OKCYAN}{expr!r}{ENDC}. Reason:\n\n{ENDC}{e}")
        return

PROMPT = ""
RESERVED = {
    "chgpath", 
    "inspect folder", "inspect file", 
    "access module", "module", "install", "uninstall",
    "process", "mute volume", "set volume",
    "fmake", "dirmake", "fdel", "fcopy", "dirdel", "dircopy",
    "varmake", "vardel", "see", "save vars", "load vars",  
    "xcon script", "python script", "run python", "python block", "path help", "inspect help", 
    "check",
    "modules help", "internal help", "io help", "script help", "variable help", "condition help", 
    "utilities help", "$", "info", "version", "close", "wipe", "python"
}

def __handle_prompt(prompt: str):
    global MODULES, CURRENT_DIR, RESERVED, LAST, DECLARELIST, PACKAGELIST
    prompt = prompt.strip()
    if "$" in prompt:
        if "$$" in prompt:
            prompt = prompt.replace("$$", "$")
        else:
            prompt = prompt.split("$", 1)[0].strip()
    if prompt.startswith("#") or "#" in prompt:
        print(f"{WARNING}Please use $ for comments instead.{ENDC}")
        return
    if not prompt:
        return
    if "@" in prompt:
        VARS = re.findall(r"@(\w+)", prompt)
        for var in VARS:
            try:
                if var in DECLARELIST:
                    VARVAL = str(DECLARELIST[var])
                elif var in globals():
                    VARVAL = str(globals()[var])
                else:
                    print(f"{WARNING}The {'variables' if len(VARS) > 1 else 'variable'} {', '.join(VARS)} could not be found associated with a value in the current context.\nDefaulting to string literal.{ENDC}")
                    VARVAL = var
                prompt = prompt.replace(f"@{var}", VARVAL)
            except Exception as e:
                print(f"{FAIL}The {'variables' if len(VARS) > 1 else 'variable'} {OKCYAN}{', '.join(VARS)} {FAIL}could not be evaluated, as {OKCYAN}{', '.join(VARS)} {FAIL}{'do' if len(VARS) > 1 else 'does'} have a value in the current context, or the {'variables' if len(VARS) > 1 else 'variable'} could not be accessed.{ENDC}")
                return
    if prompt.startswith("chgpath "):
        path = prompt.removeprefix("chgpath ").strip()
        path = os.path.normpath(path) 
        if path == "last":
            if LAST is None:
                print(f"{WARNING}No previous folder path available yet.{ENDC}")
                return
            path, LAST = LAST, os.getcwd()
            os.chdir(path)
            return
        elif path == "up":
            CURRENT = os.getcwd()
            PARENT = os.path.dirname(CURRENT)
            if CURRENT == PARENT:
                print(f"{OKBLUE}You are already in the root directory ({CURRENT}).{ENDC}")
            else:
                LAST = CURRENT
                os.chdir(PARENT)
            return
        elif path == "root":
            CURRENT = os.getcwd()
            ROOT = f"{CURRENT[0]}:\\"
            os.chdir(ROOT)
            return
        if not os.path.exists(path):
            if path == "":
                print(f"{FAIL}Expected path, got {repr(path)} (Please input a valid path).{ENDC}")
            else:
                print(f"{WARNING}Directory {repr(path)} is not available.\n{ENDC}")
                return
        elif not os.access(path, os.F_OK):
            print(f"{WARNING}{path}: Access denied.\n{ENDC}")
            return
        else:
            LAST = os.getcwd()
            os.chdir(path)
            return
    if prompt.startswith("access module "):
        MODULE = prompt.removeprefix("access module ").strip()
        if MODULE == "":
            print(f"{WARNING}Please input a valid module to access.{ENDC}")
            return
        try:
            MODULES[MODULE] = __import__(MODULE)
            globals()[MODULE] = MODULES[MODULE]
            PYTHON_CONTEXT[MODULE] = MODULES[MODULE]
            print(f"{OKGREEN}Module {MODULE} accessed successfully.{ENDC}")
            return
        except (ImportError, ModuleNotFoundError) as e:
            print(f"{FAIL}Accessing module {MODULE} failed. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("module "):
        MODULE = prompt.removeprefix("module ")
        mod = __safe_eval(MODULE, PYTHON_CONTEXT)
        try:
            print(f"{OKCYAN}The type of module {MODULE} is: {type(__safe_eval(MODULE, PYTHON_CONTEXT))}.\n(Origin is {mod.__file__}.)")
            return
        except Exception as e:
            print(f"{FAIL}Checking the type of the module {MODULE} failed (did you access it first? Does the module exist?). Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("install "):
        PACKAGE = prompt.removeprefix("install ")
        if PACKAGE == "":
            print(f"{WARNING}Package name is empty, please input a package name.{ENDC}")
            return
        try:
            if len(PACKAGE.split(" ")) > 1:
                print(f"{WARNING}Uninstalling packages {', '.join(PACKAGE.split())}...{ENDC}")
            else:
                print(f"{WARNING}Uninstalling package {PACKAGE}...{ENDC}")
            result = subprocess.run(f"pip install {PACKAGE}")
            if result.returncode == 0:
                list_package = PACKAGE.split()
                for p in list_package:
                    PACKAGELIST.append(p)
                print(f"{OKGREEN}Successfully installed {'packages' if len(list_package) > 1 else 'package'} {', '.join(PACKAGELIST)}.{ENDC}")
                return
            else:
                print(f"{FAIL}Package {PACKAGE} could not be installed. Please try again.{ENDC}")
                return
        except Exception as e:
            print(f"{FAIL}An exception occurred while trying to install package {PACKAGE}. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("uninstall "):
        PACKAGE = prompt.removeprefix("uninstall ")
        if PACKAGE == "":
            print(f"{WARNING}Package name is empty, please input a package name.{ENDC}")
            return
        try:
            if len(PACKAGE.split()) > 1:
                print(f"{WARNING}Uninstalling packages {', '.join(PACKAGE.split())}...{ENDC}")
            else:
                print(f"{WARNING}Uninstalling package {PACKAGE}...{ENDC}")
            result = subprocess.run(f"pip uninstall {PACKAGE}")
            if result.returncode == 0:
                list_package = PACKAGE.split()
                for p in list_package:
                    PACKAGELIST.remove(p)
                print(f"{OKGREEN}Successfully uninstalled {'packages' if len(list_package) > 1 else 'package'} {', '.join(PACKAGELIST)}.{ENDC}")
                return
            else:
                print(f"{FAIL}Package {PACKAGE} could not be uninstalled. Please try again.{ENDC}")
                return
        except Exception as e:
            print(f"{FAIL}An exception occurred while trying to uninstall package {PACKAGE}. Reason:\n\n{ENDC}{e}")
            return
    if prompt == "installer upgrade":
        print(f"{WARNING}Attempting to upgrade installer...{ENDC}")
        try:
            PY = sys.executable
            subprocess.run([PY, "-m", "pip", "install", "--upgrade", "pip"])
            result = subprocess.run([PY, "-m", "pip", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.split()[1]
            else:
                version = "unknown (version not found)"
            print(f"{OKGREEN}Installer successfully upgraded to version {version}.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while attempting to upgrade installer. Reason:\n\n{e}")
            return
    if prompt.endswith(" info"):
        PACKAGE = prompt.removesuffix(" info")
        if PACKAGE == "":
            print(f"{WARNING}Please input a valid package name.{ENDC}")
            return
        try:
            print(f"{OKCYAN}Getting info about package {OKCYAN}{PACKAGE}{OKCYAN}...{ENDC}")
            result = subprocess.run(f"pip show {PACKAGE}", capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                info = result.stdout
            else:
                info = "(No information found)"
            print(f"{OKGREEN}Information gathered. Information:{ENDC}\n\n{info}")
            return
        except Exception as e:
            print(f"{FAIL}Something went wrong while trying to check package info {OKCYAN}{PACKAGE}{FAIL}. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("echo "):
        STRING = prompt.removeprefix("echo ")
        if STRING == "":
            print("\n")
            return
        if STRING in DECLARELIST:
            result = DECLARELIST[STRING]
            print(result)
            return
        else:
            try:
                if isinstance(STRING, str):
                    result = __safe_eval(STRING, PYTHON_CONTEXT)
                else:
                    result = __safe_eval(f'"{STRING}"', PYTHON_CONTEXT)
                print(result)
                return
            except Exception:
                try:
                    print(STRING)
                    return
                except Exception as e:
                    print(f"{FAIL}Could not return object {STRING}. Reason:\n\n{ENDC}{e}")
                return
    if prompt.startswith("inspect folder "):
        FOLDER = prompt.removeprefix("inspect folder ").strip()
        EXTENSION = None
        if " all " in FOLDER:
            FOLDER, EXTENSION = FOLDER.split(" all ", 1)
            EXTENSION = EXTENSION.strip()
        if FOLDER == "":
            print(f"{WARNING}Folder name is empty, please specify a folder.{ENDC}")
            return
        elif FOLDER == "current":
            FOLDER = os.getcwd()
        elif FOLDER == "root":
            if os.path.exists(FOLDER):
                pass
            else:
                FOLDER = f"{os.getcwd()[0]}:\\"
        elif FOLDER == "last":
            if LAST is None:
                print(f"{WARNING}No previous folder path available.{ENDC}")
            FOLDER = LAST
        if not os.path.exists(FOLDER):
            print(f"{WARNING}Please specify a valid folder (did you forget to change the console path to the root folder of the folder {OKCYAN}{FOLDER}{WARNING}?).{ENDC}")
            return
        try:
            SUBFOLDERS = [d for d in os.listdir(FOLDER) if os.path.isdir(os.path.join(FOLDER, d))]
            FILES = [f for f in os.listdir(FOLDER) if os.path.isfile(os.path.join(FOLDER, f))]
            if EXTENSION:
                RAW = FOLDER
                EXTENSIONS = tuple(EXTENSION.split())
                FILES = [f for f in os.listdir(RAW) if os.path.isfile(os.path.join(RAW, f)) and f.endswith(EXTENSIONS)]
                if not FILES:
                    print(f"{WARNING}No files with file {'extension' if len(EXTENSIONS) == 1 else 'extensions'} {', '.join(EXTENSIONS)} found.{ENDC}")
                    return
                else:
                    files = ', '.join(FILES)
                    print(f"{OKCYAN}Folder {FOLDER} contains:\n\nFolders: {', '.join(SUBFOLDERS)}\nFiles: {files}{ENDC}")
            else:
                print(f"{OKCYAN}Folder {FOLDER} contains:\n\nFolders: {', '.join(SUBFOLDERS)}\nFiles: {', '.join(FILES)}{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}Folder {FOLDER} could not be inspected. Reason:\n\n{ENDC} {e}")
        return
    if prompt.startswith("inspect file "):
        FILE = prompt.removeprefix("inspect file ")
        if FILE.startswith("text "):
            PARAMS = FILE.removeprefix("text ").strip().split(" ", 1)
            if len(PARAMS) < 2:
                print(f"{WARNING}Please execute the command in this order: inspect file text 'x' file.txt{ENDC}")
                return
            TEXT, FILE = PARAMS
            PATH = os.path.join(os.getcwd(), FILE)
            if TEXT.startswith(("'", '"')) and TEXT.endswith(("'", '"')):
                TEXT = TEXT[1:-1]
            if not os.path.exists(PATH):
                print(f"{WARNING}File {FILE} cannot be read, because it does not exist in the current context. Please try again.{ENDC}")
                return
            with open(PATH, "r") as f:
                lines = f.read()
                count = lines.count(TEXT)
                if count == 0:
                    print(f"{WARNING}There aren't any lines with text {TEXT} in the file {FILE}.{ENDC}")
                    return
                else:
                    print(f"{OKCYAN}The amount of times {TEXT} has been counted {count} times in the file {FILE}.{ENDC}")
                return
            if not os.path.exists(PATH):
                print(f"{WARNING}File {FILE} does not exist in the current context.{ENDC}")
                return
        PATH = os.path.join(os.getcwd(), FILE)
        if not os.path.exists(PATH):
            print(f"{WARNING}File {FILE} does not exist in the current context.{ENDC}")
            return
        try:
            with open(FILE, "r+") as f:
                CONTENT = f.read()
                print(f"\n{CONTENT}")
            return
        except (Exception, UnicodeDecodeError, UnicodeError) as e:
            print(f"{FAIL}File {FILE} could not be inspected. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("check "):
        CONDITION = prompt.removeprefix("check ")
        if CONDITION in RESERVED:
            print(f"{FAIL}XCon commands are not checkable.{ENDC}")
            return
        CONTEXT = dict(globals())
        CONTEXT.update(DECLARELIST)
        if CONDITION.startswith("type "):
            TYPECONDITION = __safe_eval(CONDITION.removeprefix("type "), CONTEXT)
            try:    
                print(f"{OKCYAN}{TYPECONDITION} has the type {type(TYPECONDITION).__name__}.")
                return
            except Exception as e:
                print(f"{FAIL}Could not check condition {TYPECONDITION}. Reason:\n\n{ENDC}{e}")
                return
        try:
            if CONDITION.endswith(" exists"):
                OBJECT = CONDITION.removesuffix(" exists")
                PATH = os.path.join(os.getcwd(), OBJECT)
                short = 'File' if os.path.isfile(OBJECT) else 'Directory'
                print(f"{WARNING}Checking if {short.lower()} {OBJECT} exists...{ENDC}")
                if os.path.exists(PATH):
                    print(f"{OKGREEN}{short} {OBJECT} exists in the current context.{ENDC}")
                    return
                else:
                    print(f"{FAIL}{short} {OBJECT} does not exist in the current context. Please try again.{ENDC}")
                    return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while checking existence of {short.lower()} {OBJECT}. Reason:\n\n{ENDC}{e}")
            return   
        RESULT = __safe_eval(CONDITION, CONTEXT)
        if RESULT is True: 
            print(f"{OKGREEN}Condition \"{CONDITION}\" is true.{ENDC}")
            return
        elif RESULT is False:
            print(f"{FAIL}Condition \"{CONDITION}\" is false.{ENDC}")
            return
        else:
            print(f"{OKCYAN}Condition \"{CONDITION}\" has been evaluated to: {RESULT}{ENDC}")
            return
    if prompt.startswith("xcon script "):
        SCRIPT = prompt.removeprefix("xcon script ").strip()
        if not SCRIPT:
            print("{WARNING}Please provide a script file to run.{ENDC}")
            return
        if not os.path.exists(SCRIPT):
            print(f"{WARNING}Script file '{SCRIPT}' not found.{ENDC}")
            return
        if not SCRIPT.endswith(".xcon"):
            print(f"{WARNING}Please run a script file with a .xcon file extension.{ENDC}")
            return
        try: 
            with open(SCRIPT, "r+") as f:
                RAWL = f.readlines()
            if not RAWL:
                print(f"{FAIL}The script file '{OKCYAN}{SCRIPT}{FAIL}' is empty, please provide a script with a valid (set of) commands.{ENDC}")
                return
            logiclines = []
            buf = ""
            for raw in RAWL:
                line = raw.strip()
                if not line:
                    continue
                if line.endswith(">"):
                    buf += line[:-1].rstrip() + " "
                    continue
                else:
                    buf += line
                    logiclines.append(buf)
                    buf = ""
            if buf:
                logiclines.append(buf)
            for rawline in logiclines:
                line = rawline.split("$", 1)[0].strip()
                for varname, varval in DECLARELIST.items():
                    line = line.replace(f"see {varname}", str(varval))
                if not line:
                    continue
                print(f"{OKCYAN}[.xcon script] {line}{ENDC}")
                __handle_prompt(line)
            print(f"{OKGREEN}Execution of script '{OKCYAN}{SCRIPT}{OKGREEN}' done.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}Could not run script '{OKCYAN}{SCRIPT}{FAIL}'. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("python script"):
        SCRIPT = prompt.removeprefix("python script ")
        if not SCRIPT:
            print(f"{WARNING}Please provide a script file to run.{ENDC}")
            return
        if not os.path.exists(SCRIPT):
            print(f"{WARNING}Script file {SCRIPT} not found.{ENDC}")
            return
        if not SCRIPT.endswith(".py"):
            print(f"{WARNING}Please run a script file with a .py file extension.{ENDC}")
            return
        try:
            with open(SCRIPT, "r") as f:
                lines = f.read()
                exec(lines, {"__name__": "__main__"})
                print(f"{OKGREEN}Execution of script file {SCRIPT} succeeded.{ENDC}")
                return
        except Exception as e:
            print(f"{FAIL}Could not run script {SCRIPT}. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("python run "):
        COMMAND = prompt.removeprefix("python run ")
        if COMMAND == "":
            print(f"{WARNING}Please run a valid command.{ENDC}")
            return
        try:
            print(f"{BOLD}Executing command '{COMMAND}'...{ENDC}")
            exec(COMMAND, PYTHON_CONTEXT)
            print(f"{OKGREEN}Execution of command {COMMAND} succeeded.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while executing command '{COMMAND}.' Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("python block !x "):
        BLOCK = prompt.startswith("python block !x ")
        __run_python_block(prompt, BLOCK)
        return
    if prompt == "cd" or prompt.startswith("cd "):
        print(f"{OKCYAN}Please use {OKBLUE}chgpath {OKCYAN}<path_name> {ENDC}instead.")
        return
    if prompt == "cls":
        print(f"{OKCYAN}Please use {OKBLUE}wipe {ENDC}instead.")
        return
    if prompt == "exit":
        print(f"{OKCYAN}Please use {OKBLUE}close {ENDC}instead.")
        return
    if prompt.startswith("process "):
        if prompt == "process shutdown":
            print(f"{WARNING}The process command may be empty or incomplete. Try again.\n{ENDC}")
            return
        if "shutdown" in prompt:
            cmd = ["shutdown"]
            if "!r" in prompt:
                cmd.append("/r")
            elif "!s" in prompt:
                cmd.append("/s")
            elif "!h" in prompt:
                cmd.append("/h")
            if "!f" in prompt:
                cmd.append("/f")
            if "!fw" in prompt:
                cmd.append("/fw")
            if "!o" in prompt:
                cmd.append("/o")
            if "!i" in prompt:
                cmd.append("/i")
            if "!sf" in prompt:
                cmd.append("/soft")
            if "!e" in prompt:
                cmd.append("/e")
            if "!l" in prompt and "!h" in prompt:
                cmd.append("/l")
            if "!t" in prompt:
                parts = prompt.split()
                if "!t" in parts:
                    t_index = parts.index("!t")
                    if t_index + 1 < len(parts):
                        seconds = parts[t_index + 1]
                        cmd += ["/t", str(seconds)]
            full_cmd = " ".join(cmd)
            result = subprocess.run(full_cmd, shell=True, text=True, capture_output=True)
            output = result.stdout.strip() + result.stderr.strip()
            if output.startswith("Usage:"):
                output = f"{YELLOW}This command didn't seem to work, please try again.{ENDC}"
            print(output)
            return
        elif "sleep" in prompt:
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return
    if prompt.startswith("set volume "):
        VOLUME = prompt.removeprefix("set volume ")
        try:
            __set_volume(VOLUME)
            return
        except Exception as e:
            print(f"{FAIL}An exception occurred while attempting to set current volume to {VOLUME}. Reason:\n\n{ENDC}{e}")
            return
    if prompt == "mute volume":
        try:
            __set_volume(0)
            return
        except Exception as e:
            print(f"{FAIL}An exception occurred while attempting to mute volume. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("console "):
        CMD = prompt.removeprefix("console ").strip()
        try:
            print(f"{WARNING}Attempting to execute console command {OKCYAN}'{CMD}'{WARNING}...{ENDC}")
            result = subprocess.run(CMD, shell=True, text=True, capture_output=True)
            if result.returncode == 0:
                print(result.stdout)
                print(f"{OKGREEN}Successfully ran console command {OKCYAN}'{CMD}'{OKGREEN}.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}An exception occurred while attempting to execute console command {OKCYAN}'{CMD}'{FAIL}. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("fmake "):
        FILE = prompt.removeprefix("fmake ").strip()
        WRITE = "^ "
        if WRITE in FILE:
            path_part, CONTENT = FILE.split(WRITE, 1)
            path_part = path_part.strip()
            CONTENT = CONTENT.strip()
        else:
            path_part = FILE
            CONTENT = ""
        append = False
        if CONTENT.endswith("| !append"):
            append = True
            CONTENT = CONTENT[:-len("| !append")].rstrip()
        elif CONTENT.endswith("!append"):
            append = True
            CONTENT = CONTENT[:-len("!append")].rstrip()
        if not prompt.endswith(" !nodef"):
            print(f"{WARNING}No file extension given, defaulting to .txt file extension.{ENDC}")
            if not path_part.endswith(".txt"):
                path_part += ".txt"
            else:
                pass
        else:
            path_part = path_part.removesuffix(" !nodef")
            pass
        if CONTENT.endswith("!nodef"):
                CONTENT = CONTENT[:-len("!nodef")].rstrip()
        elif CONTENT.endswith("| !nodef"):
            CONTENT = CONTENT[:-len("| !nodef")].rstrip()
        PATH = os.path.join(os.getcwd(), path_part)
        mode = "a" if append else "w"
        try:
            with open(PATH, mode, encoding="utf-8") as f:
                if CONTENT:
                    PLACEHOLDER = "__PIPE__"
                    temp_content = CONTENT.replace("||", PLACEHOLDER)
                    lines = temp_content.split("|")
                    lines = [line.replace(PLACEHOLDER, "|").strip() for line in lines]
                    for line in lines:
                        f.write(line + "\n" if CONTENT else "")
            ACTION = "appended to" if append else "written to"
            print(f"{OKGREEN}File {os.path.basename(PATH)} successfully {ACTION} at {PATH}.")
            return
        except Exception as e:
            print(f"{FAIL}Failed to write file {PATH}. Reason:\n\n{ENDC}{e}")
        return
    if prompt.startswith("fdel "):
        FILE = prompt.removeprefix("fdel ")
        if not prompt.endswith(" !nodef"):
            if not os.path.splitext(FILE)[1]:
                print(f"{WARNING}No file extension given, defaulting to .txt file extension.{ENDC}")
                FILE += ".txt"
            else:
                pass
        else:
            FILE = FILE.removesuffix(" !nodef").strip()
        PATH = os.path.join(os.getcwd(), FILE)
        try:
            if not os.path.exists(PATH):
                print(f"{WARNING}File {FILE} does not exist or is not accessible.{ENDC}")
                return
            if __is_protected(FILE):
                print(f"{FAIL}Tried to delete a file in a sensitive directory, as {OKCYAN}{FILE} {FAIL}in {OKCYAN}{PATH} {FAIL}is a Windows and/or critical program file. Exiting XCon console for optimal safety.{ENDC}")
                time.sleep(2.0)
                sys.exit(-1)
            else:
                CONFIRM = input(f"{OKCYAN}Are you sure you want to remove file {FILE}? {OKGREEN}[y]{COMMENT}/{FAIL}[n]{ENDC} ").strip()
                if CONFIRM.lower() == "y":
                    try:
                        os.remove(PATH)
                        print(f"{OKGREEN}File {FILE} at {PATH} successfully removed.{ENDC}")
                    except Exception as e:
                        print(f"{FAIL}File {FILE} could not be removed. Reason:\n\n{ENDC}{e}")
                    return
                elif CONFIRM.lower() == "n":
                    print(f"{OKCYAN}Deletion of file {FILE} stopped.{ENDC}")
                    return
                else:
                    print(f"{WARNING}{CONFIRM} is not a valid answer, defaulting to deletion stop.{ENDC}")
                    return
        except Exception as e:
            print(f"{FAIL}File {FILE} could not be removed. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("fcopy "):
        ARGS = prompt.removeprefix("fcopy ").strip().split()
        if len(ARGS) < 1:
            print(f"{WARNING}Please setup the command properly. Usage: {OKBLUE}fcopy {OKCYAN}source_file dest_file{ENDC}")
            return
        FILE = ARGS[0]
        NEWDIR = os.path.join(os.getcwd(), "copy") if not len(ARGS) < 2 else ARGS[1]
        if len(ARGS) > 1 and ARGS[1]:
            NEWDIR = ARGS[1]
        if not prompt.endswith(" !nodef"):
            if not os.path.splitext(FILE)[1]:
                print(f"{WARNING}!nodef not included and no file extension has been given, defaulting to .txt file extension.{ENDC}")
                FILE += ".txt"
        if not os.path.exists(FILE):
            print(f"{WARNING}File {FILE} does not exist.{ENDC}")
            return
        try:
            if os.path.exists(NEWDIR):
                print(f"{WARNING}{NEWDIR} already exists, choosing other generated directory name.{ENDC}")
                for i in range(1, 21):
                    NEWDIR_ITER = f"{NEWDIR}_{i}"
                    if not os.path.exists(NEWDIR_ITER):
                        os.makedirs(NEWDIR_ITER)
                        NEWDIR = NEWDIR_ITER
                        break
                    else:
                        print(f"{WARNING}New directory {NEWDIR_ITER} already exists, choosing other directory name.")
                    if i == 21:
                        print(f"{FAIL}Creating non-existing directory failed, as all the directory names generated were already existing.\nPlease try again.{ENDC}")
                        return
            else:
                os.makedirs(NEWDIR)
            DST_PATH = os.path.join(NEWDIR, FILE)
            with open(FILE, "rb") as srcf:
                data = srcf.read()
            with open(DST_PATH, "wb") as dstf:
                dstf.write(data)
            if "/" in DST_PATH:
                READ_DST = DST_PATH.replace("/", "\\")
            else:
                READ_DST = DST_PATH
            print(f"{OKGREEN}File successfully {FILE} copied to directory {READ_DST}.{ENDC}")
        except Exception as e:
            print(f"{FAIL}An error has occurred while trying to copy file {FILE} to directory {READ_DST}. Reason:\n\n{ENDC}{e}")
        return
    if prompt.startswith("dirmake "):
        DIR = prompt.removeprefix("dirmake ").strip()
        PATH = os.path.join(os.getcwd(), DIR)
        if not DIR:
            print(f"{WARNING}Please input a valid directory name.{ENDC}")
            return
        if os.path.exists(DIR):
            print(f"{OKCYAN}Directory {DIR} already exists at {PATH}. Overwriting directory {DIR}.{ENDC}")
        try:
            os.makedirs(PATH, exist_ok=True)
            print(f"{OKGREEN}Directory '{DIR}' created successfully at {PATH}.{ENDC}")
        except Exception as e:
            print(f"{FAIL}Failed to create directory '{DIR}'. Reason:\n\n{ENDC}{e}")
        return
    if prompt.startswith("dirdel "):
        DIR = prompt.removeprefix("dirdel ").strip()
        if not DIR:
            print(f"{WARNING}Please input a valid directory name.{ENDC}")
            return
        try:
            if DIR == "current":
                TARGET_PATH = os.getcwd()
                last_dirname = os.path.basename(TARGET_PATH)
                if __is_sensitive(TARGET_PATH, True):
                    print(f"{FAIL}ACCESS DENIED: Tried to remove sensitive or protected directory, as the sensitive directory {OKCYAN}{TARGET_PATH} {FAIL}was targeted for deletion.\nExiting XCon Console for optimal safety.{ENDC}")
                    time.sleep(1.5)
                    sys.exit(-1)
                if TARGET_PATH == os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__):
                    print(f"{FAIL}ACCESS DENIED: Tried to self destruct distribution folder where program is running.\nExiting XCon Console for optimal safety.{ENDC}")
                    time.sleep(1.5)
                    sys.exit(-1)
                CONFIRM = input(f"{OKCYAN}Are you sure you want to remove the current directory {last_dirname}? {OKGREEN}[y]{COMMENT}/{FAIL}[n]{ENDC} ").strip()
                if CONFIRM.lower() == "y":
                    print(f"{WARNING}Removing current directory {TARGET_PATH}...{ENDC}")
                    shutil.rmtree(TARGET_PATH)
                    print(f"{OKGREEN}Directory {last_dirname} removed successfully.{ENDC}")
                    return
                elif CONFIRM.lower() == "n":
                    print(f"{OKCYAN}Deletion of directory {last_dirname} stopped.{ENDC}")
                    return
                else:
                    print(f"{WARNING}{CONFIRM} is not a valid answer, defaulting to deletion stop.{ENDC}")
                    return
            else:
                TARGET_PATH = os.path.join(os.getcwd(), DIR)
                if not os.path.exists(TARGET_PATH):
                    print(f"{WARNING}Directory {DIR} does not exist. Please try again.{ENDC}")
                    return
                if __is_sensitive(TARGET_PATH, True):
                    print(f"{FAIL}ACCESS DENIED: Tried to remove sensitive or protected directory, as the sensitive directory {OKCYAN}{TARGET_PATH} {FAIL}was targeted for deletion.\nExiting XCon Console for optimal safety.{ENDC}")
                    time.sleep(1.5)
                    sys.exit(-1)
                CONFIRM = input(f"{OKCYAN}Are you sure you want to remove the directory {DIR}? {OKGREEN}[y]{COMMENT}/{FAIL}[n]{ENDC} ").strip()
                if CONFIRM.lower() == "y":
                    print(f"{WARNING}Removing directory {TARGET_PATH}...{ENDC}")
                    shutil.rmtree(TARGET_PATH)
                    print(f"{OKGREEN}Directory {DIR} at {TARGET_PATH} removed successfully.{ENDC}")
                    return
                elif CONFIRM.lower() == "n":
                    print(f"{OKCYAN}Deletion of directory {DIR} stopped.{ENDC}")
                    return
                else:
                    print(f"{WARNING}{CONFIRM} is not a valid answer, defaulting to deletion stop.{ENDC}")
                    return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while removing directory '{DIR}'. Reason:\n\n{ENDC}{e}")
        return
    if prompt.startswith("dircopy "):
        DIRS = prompt.removeprefix("dircopy ")
        DIR = DIRS.split(maxsplit=1)
        SRC = DIR[0]
        if len(DIR) < 2:
            DEST = f"{SRC}_dir"
            print(f"{WARNING}No second directory given, using alternative destination folder: {OKCYAN}{DEST}{WARNING}.{ENDC}")
        else:
            DEST = DIR[1]
        DST_CHILD = os.path.join(DEST, os.path.basename(SRC))
        for d in DIR:
            if not os.path.exists(d):
                if d == DST_CHILD:
                    print(f"{WARNING}Directory {OKCYAN}{d} {WARNING}does not exist, creating folder {OKCYAN}{d}{WARNING}...{ENDC}")
                    os.makedirs(d)
                    print(f"{OKGREEN}Directory {OKCYAN}{d} {OKGREEN}successfully created.{ENDC}")
                    continue
                else:
                    print(f"{WARNING}Directory {OKCYAN}{d} {WARNING}does not exist, Please input a valid directory name.{ENDC}")
                return
        if os.path.abspath(SRC) == os.path.abspath(DST_CHILD):
            print(f"{WARNING}You cannot copy the same directory into itself.{ENDC}")
            return
        if not SRC or not DST_CHILD:
            print(f"{WARNING}Setup failed. Please input 2 different directories, for example: dircopy folder1 folder2{ENDC}")
            return
        try:
            shutil.copytree(SRC, DST_CHILD, dirs_exist_ok=True)
            print(f"{OKGREEN}{OKCYAN}{SRC} {OKGREEN}has successfully been copied into {OKCYAN}{DEST} {OKGREEN}as {OKCYAN}{os.path.basename(SRC)}{OKGREEN}.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while copying directory {OKCYAN}{SRC} into {DEST}. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("varmake "):
        VARDECL = prompt.removeprefix("varmake ").strip()
        try:
            if "set" not in VARDECL:
                print(f"{WARNING}Invalid variable setup. Example: varmake x set 1{ENDC}")
                return
            split_VARDECL = VARDECL.split("set", 1)
            if len(split_VARDECL) != 2:
                print(f"{WARNING}Please put the keyword {OKCYAN}set {WARNING}in the right position: {OKBLUE}varmake {OKCYAN}x {YELLOW}set {OKCYAN}1{WARNING}, not {OKBLUE}varmake {YELLOW}set {OKCYAN}x {YELLOW}1 or {OKBLUE}varmake {OKCYAN}x {YELLOW}1 {OKBLUE}set or {OKBLUE}varmake {OKCYAN}1 {YELLOW}x {OKCYAN}set {WARNING}(or any other way).{ENDC}")
                return
            VARVAL_RAW = split_VARDECL[1].strip()
            VARNAME = split_VARDECL[0].strip()
            try:
                VARVAL = ast.literal_eval(VARVAL_RAW)
            except Exception:
                try:
                    VARVAL = __safe_eval(VARVAL_RAW, PYTHON_CONTEXT)
                except Exception as e:
                    if VARVAL_RAW in DECLARELIST:
                        VARVAL = DECLARELIST[VARVAL_RAW]
                    else:
                        print(f"{FAIL}Failed to initialize variable {OKCYAN}{VARNAME}{FAIL}, because it contains a invalid value: {OKCYAN}{VARVAL_RAW}{FAIL}. Error:\n\n{ENDC}{e}")
                        result = input(f"{WARNING}Would you like to convert it to a string instead? {OKGREEN}[y]{COMMENT}/{FAIL}[n]{ENDC} ").strip()
                        if result == "y":
                            VARVAL = VARVAL_RAW
                        elif result == "n":
                            print(f"{WARNING}Variable {OKCYAN}{VARNAME} {WARNING}has not been announced has declared.{ENDC}")
                            return
            if VARNAME in globals():
                print(f"{WARNING}Variable {VARNAME} already exists. Overwriting {VARNAME} with value {VARVAL}.{ENDC}")
            if VARNAME in RESERVED:
                print(f"{FAIL}You cannot overwrite a XCon command.{ENDC}")
                return
            globals()[VARNAME] = VARVAL
            DECLARELIST[VARNAME] = VARVAL
            print(f"{OKGREEN}Declared variable {VARNAME} at address {id(VARVAL)} with value {VARVAL}.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}Variable not created, reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("vardel "):
        VAR = prompt.removeprefix("vardel ").strip()
        try:
            if VAR == "all":
                if not DECLARELIST:
                    print(f"{WARNING}Please declare variables before removing any.{ENDC}")
                    return
                TEMPLIST = DECLARELIST.copy()
                DELVARS = ', '.join(f"{OKCYAN}{varname} {OKGREEN}({varval!r})" for varname, varval in TEMPLIST.items())
                for name in TEMPLIST:
                    globals().pop(name, None)
                    DECLARELIST.pop(name, None)
                    print(f"{WARNING}Removing variable {name} in variable list...{ENDC}")
                __save_vars()
                print(f"{OKGREEN}Successfully removed all variables. (Deleted {'variables' if len(TEMPLIST) > 1 else 'variable'} {DELVARS}.){ENDC}")
                del TEMPLIST
                return
            if VAR in globals() or VAR in DECLARELIST:
                del globals()[VAR]
                del DECLARELIST[VAR]
                __save_vars()
                print(f"{OKGREEN}Variable {VAR} has been removed successfully.{ENDC}")
                return
            else:
                print(f"{WARNING}Variable {VAR} does not exist in the current context. Please try again.{ENDC}")
                return
        except Exception as e:
            target = f'variable {VAR}' if VAR != "all" else "all variables"
            print(f"{FAIL}Something went wrong while removing {target}. Reason:\n\n{ENDC}{e}")
            return
    if prompt == "save vars":
        VARS = ', '.join(f"{OKCYAN}{varname} {OKGREEN}({varval!r})" for varname, varval in DECLARELIST.items())
        print(f"{WARNING}Attempting to force save variables {VARS}...")
        try:
            __save_vars()
            print(f"{OKGREEN}Variables {VARS} successfully saved inside of variable declaration file {OKCYAN}vardecl.json{OKGREEN}.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while trying to save variables {VARS}. Reason:\n\n{ENDC}{e}")
            return
    if prompt == "load vars":
        VARS = ', '.join(f"{OKCYAN}{varname} {OKGREEN}({varval!r})" for varname, varval in DECLARELIST.items())
        print(f"{WARNING}Attempting to force load variables {VARS}...")
        try:
            __save_vars()
            print(f"{OKGREEN}Variables {VARS} successfully loaded from variable declaration file {OKCYAN}vardecl.json{OKGREEN}.{ENDC}")
            return
        except Exception as e:
            print(f"{FAIL}An exception has occurred while trying to load variables {VARS}. Reason:\n\n{ENDC}{e}")
            return
    if prompt.startswith("see "):
        VAR = prompt.removeprefix("see ").strip()
        if VAR == "globals":
            print(f"{OKCYAN}Global variables:\n{', '.join([var for var in globals() if var not in RESERVED])}{ENDC}")
            return
        if VAR == "declared":
            if DECLARELIST == {}:
                print(f"{WARNING}You haven't declared any variables yet. Please try again.{ENDC}")
                return
            else:
                DECLVARS = ', '.join(f"{varname} ({varval!r})" for varname, varval in DECLARELIST.items())
                print(f"{OKCYAN}Declared: {DECLVARS}{ENDC}")
                return
        if VAR == "packages":
            print(f"{OKCYAN}The packages in the current context installed: {', '.join(PACKAGELIST)}")
            return
        if VAR == "":
            print(f"{WARNING}Please specify a variable name.{ENDC}")
            return
        if VAR in RESERVED:
            print(f"{FAIL}You cannot access an XCon variable. (Tried to access variable {VAR}){ENDC}")
            return
        if VAR in globals():
            print(globals()[VAR])
        else:
            print(f"{WARNING}Variable {ORANGE}'{VAR}' {WARNING}not found. Make sure to define your variable {VAR} before using {OKBLUE}see {OKCYAN}{VAR}{WARNING}.{ENDC}")
        return
    if prompt.startswith("command "):
            global COMMAND_HISTORY
            COMMAND_HISTORY = COMMAND_HISTORY[-100:]
            flag = prompt.removeprefix("command ").strip()
            if not COMMAND_HISTORY:
                print(f"{WARNING}You haven't inputted any commands into the XCon console prompt yet, please prompt a command first before running the {OKBLUE}command history{WARNING} command.{ENDC}")
                return
            else:    
                if flag == "history !r":
                    print(f"{WARNING}Recent command history (reversed with {OKCYAN}!r{WARNING}):\n\n{ENDC}")
                    for i, CMD in enumerate(reversed(COMMAND_HISTORY), start=1):
                        print(f'{OKBLUE}{i}{ENDC}: {OKGREEN}{CMD}{ENDC}')
                    return
                elif flag == "history":
                    print(f"{WARNING}Recent command history:\n\n{ENDC}")
                    for i, CMD in enumerate(COMMAND_HISTORY, start=1):
                        print(f'{OKBLUE}{i}{ENDC}: {OKGREEN}{CMD}{ENDC}')
                    return
                elif flag.startswith("search "):
                    term = flag.removeprefix("search ").lower()
                    matches = [(i+1, cmd) for i, cmd in enumerate(COMMAND_HISTORY) if term == cmd.lower()]
                    print(f"{WARNING}Searching command in command history: {OKBLUE}{term}\n{ENDC}")
                    if matches:
                        for i, cmd in matches:
                            print(f'{OKBLUE}{i}{ENDC}: {OKGREEN}{cmd}{ENDC}')
                            return
                    else:
                        print(f"{WARNING}No commands matching {OKBLUE}{term} {WARNING}found.{ENDC}")
                        return
    match prompt:
        case "info":
            print(f"{OKCYAN}XCon 2025 Ltd.\n\nUses: {YELLOW}Python\n{OKCYAN}A testing console.{ENDC}")
        case "close":
            print(f"{OKGREEN}Thank you for using the XCon Console!\n{OKCYAN}XCon Console 2025 Ltd.{ENDC}")
            __save_vars()
            sys.exit(0)
        case "wipe":
            subprocess.run("cls" if os.name == "nt" else "clear", shell=True)
        case "no color":
            subprocess.run("color 8", shell=True)
        case "empty bin":
            CONFIRM = input(f"{WARNING}Are you sure you want to empty the recycle bin? {OKGREEN}[y]{COMMENT}/{FAIL}[n]{ENDC} ").strip()
            if CONFIRM.lower() == "y":
                __empty_bin()
            elif CONFIRM.lower() == "n":
                print(f"{OKCYAN}Recycle bin emptying stopped.{ENDC}")
            else:
                print(f"{WARNING}{CONFIRM} is not a valid answer, defaulting to emptying stop.{ENDC}")
                return
        case "python":
            print(f"You are already running Python, well, XCon Console code, silly. Try something else.\n") 
        case "version":
            print(f"You are running XCon Console {OKCYAN}v0.1.{ENDC}")
        case "meow":
            print(f"ฅ^•ﻌ•^ฅ {PINK}meow!{ENDC}")
        case "nya":
            print(f"/ᐠ˵- ⩊ -˵マ {PINK}nya~!{ENDC}")
        case "malak":
            print(f"""
                  Oh, you want to know about Malak, the creator of the console's true love?\nWell, that's pretty simple, but pretty complicated to explain at the same time, ahaha...
                  Long story short, she is the most perfect girl and the creator of the console is truly so happy\nin life with this girl. Every time he sees her in his presence, his lips don't just smile - His heart does as well.
                  His heart flutters upon her interacting with her and it feels like heaven...
                  Well, can't tell you too much here. Don't want to run low on resources here.
                  Thanks for taking interest into it!
                  {PINK}If possible, make her feel happy as much as you can, I know she likes being appreciated <3!{ENDC}
                  """)
        case "what is reality":
            print(fr"""
                  {WARNING}The lyrics are on-beat depending on how fast the link opens for you, so please be cautious! :(""")
            print(fr"""
                  {OKCYAN}-- Sing along!""")
            link = subprocess.run("start https://www.youtube.com/watch?v=CAL4WMpBNs0", shell=True)
            result = input(f"Press any key to start the lyrics when the song starts!\nIf you want to exit, type {ORANGE}'exit'{OKCYAN}.")
            if result == "exit":
                return
            if link.returncode == 0:
                for i in range(10, 0, -1):
                    print(f"Lyrics start in {i}...", end="\r", flush=True)
                    time.sleep(1.0)
                print(" " * 30, end='\r')
                print(fr"""
                      {PINK}Every day, I imagine a future where I can be with you""")
                time.sleep(8.0)
                print(fr"""
                      In my hand is a pen that will write a poem of me and you""")
                time.sleep(9.25)
                print(fr"""
                      The ink flows down into a dark puddle""")
                time.sleep(4.75)
                print(fr"""
                      Just move your hand, write the way into his heart""")
                time.sleep(5.25)
                print(fr"""
                      But in this world of infinite choices""")
                time.sleep(4.25)
                print(fr"""
                      What will it take just to find that special day?""")
                time.sleep(4.25)
                print(fr"""
                      What will it take just to find that special day?""")
                time.sleep(13.75)
                print(fr"""
                      Have I found everybody a fun assignment to do today?""")
                time.sleep(9.25)
                print(fr"""
                      When you're here, everything that we do is fun for them anyway""")
                time.sleep(9.5)
                print(fr"""
                      When I can't even read my own feelings""")
                time.sleep(4.25)
                print(fr"""
                      What good are words when a smile says it all?""")
                time.sleep(4.25)
                print(fr"""
                      And if this world won't write me an ending""")
                time.sleep(5.0)
                print(fr"""
                      What will it take just for me to have it all?""")
                time.sleep(23.25)
                print(fr"""
                      Does my pen only write bitter words for those who are dear to me?""")
                time.sleep(10.0)
                print(fr"""
                      Is it love if I take you, or is it love if I set you free?""")
                time.sleep(12.75)
                print(fr"""
                      The ink flows down into a dark puddle""")
                time.sleep(4.75)
                print(fr"""
                      How can I write love into reality?""")
                time.sleep(5.25)
                print(fr"""
                      If I can't hear the sound of your heartbeat""")
                time.sleep(5.25)
                print(fr"""
                      What do you call love in your reality?""")
                time.sleep(4.25)
                print(fr"""
                      And in your reality, if I don't know how to love you""")
                time.sleep(12.25)
                print(fr"""
                      I'll leave you be{ENDC} 
                """)
            else:
                print(f"{FAIL}Monika did not want to sing for you... :({ENDC}")
        case "path help":
            print(fr"""
                -- Path
                {OKBLUE}chgpath {OKCYAN}<path>{ENDC}                : Change the current path to execute commands from.
                {OKBLUE}chgpath {OKCYAN}root{ENDC}                  : Change path to root directory (usually {OKCYAN}C:\{ENDC}).
                {OKBLUE}chgpath {OKCYAN}up{ENDC}                    : Change to the parent folder of the current path.""")
        case "inspect help":
            print(fr"""
                -- Inspection
                {OKBLUE}inspect folder {OKCYAN}<folder_name>{ENDC}  : Inspects all items in folder_name.
                {OKBLUE}inspect folder {OKCYAN}<folder_name> {YELLOW}all {OKCYAN}<file_extension>{ENDC}           : Get all files in {OKCYAN}folder_name{ENDC}
                                                                              that have the file extension 
                                                                              {OKCYAN}file_extension{ENDC}.
                {OKBLUE}inspect file {OKCYAN}<file_name>{ENDC}      : Reads all lines from a file (if possible).
                {OKBLUE}inspect file text {WARNING}<text> {OKCYAN}<file_name>{ENDC}       : Reads a specific piece of text from the file
                                                             and returns the amount of times the text 
                                                             has been repeated inside of {OKCYAN}file_name.""")
        case "modules help":
            print(fr"""
                -- Modules
                {OKBLUE}access module {OKCYAN}<module_name>{ENDC}   : Access (or simpler, import) the module {OKCYAN}module_name{ENDC}.
                {OKBLUE}module {OKCYAN}<module_name>{ENDC}          : Returns the type of {OKCYAN}module_name{ENDC}.
                {OKBLUE}install {OKCYAN}<package_name>{ENDC}        : Attempts to install the global package {OKCYAN}package_name{ENDC}.
                {OKCYAN}<package_name> {OKBLUE}info{ENDC}           : Gathers information about the package {OKCYAN}package_name{ENDC}.
                {OKBLUE}installer {OKCYAN}upgrade{ENDC}             : Attempts to upgrade/update the installer to the latest version.""")
        case "internal help":
            print(fr"""
                -- Internal
                {OKBLUE}process shutdown {ORANGE}!r{ENDC}           : Restart the computer.
                Options: {ORANGE}[!f: close files] [!fw: firmware]
                         [!o: advanced boot options] [!i: show remote shutdown]
                         [!sf: soft close programs] [!e: enable shutdown docs]
                         [!t {OKCYAN}<seconds>{ORANGE}: restart in {OKCYAN}<seconds> {ORANGE}seconds]{ENDC}

                {OKBLUE}process shutdown {ORANGE}!s{ENDC}           : Shut down the computer (same options as above).
                Options: {ORANGE}[!f: close files] [!fw: firmware]
                         [!o: advanced boot options] [!i: show remote shutdown]
                         [!sf: soft close programs] [!e: enable shutdown docs]
                         [!t {OKCYAN}<seconds>{ORANGE}: shutdown in {OKCYAN}<seconds> {ORANGE}seconds]{ENDC}
                {OKBLUE}process shutdown {ORANGE}!h{ENDC}           : Hibernate the computer (use {ORANGE}!f{ENDC} to close files).
                Options: {ORANGE}[!f: close files] [!l: sign out]{ENDC}
                {OKBLUE}process {ORANGE}sleep{ENDC}                 : Put the computer to sleep.
                Options: {ORANGE}[none]{ENDC}
                -- You may need to download packages manually or with {OKBLUE}install {OKCYAN}<package>{ENDC} with the following:
                {OKBLUE}set volume {OKCYAN}<volume_value>{ENDC}     : Sets the current volume to {OKCYAN}volume_value{ENDC}.
                {OKBLUE}mute volume{ENDC}                   : Mutes the volume.
                {OKBLUE}console {OKCYAN}<command>{ENDC}             : Runs a command directly through the console. 
                                                {WARNING}Note: Not all commands will run as expected through XCon.{ENDC}""")
        case "io help":
            print(fr"""
                -- File I/O
                {OKBLUE}fmake {OKCYAN}<file_name> {ORANGE}[{OKCYAN}^ {WARNING}<content> {YELLOW}[{OKBLUE}| {YELLOW}<- multiline indc.]{ORANGE}] [{OKCYAN}!append {ORANGE}or {OKCYAN}| !append{ORANGE}] [{OKCYAN}!nodef{ORANGE}]{ENDC}   : Create 
                                                                         a file, optionally write content 
                                                                         with the {OKCYAN}^{ENDC} indicator.
                                                                         With the {OKCYAN}!append{ENDC} indicator, 
                                                                         you tell the console you don't want to 
                                                                         overwrite anything, 
                                                                         just add text to it.
                                                                         The file automatically defaults to a .txt
                                                                         file, so you'd have to put {OKCYAN}!nodef{ENDC}
                                                                         in the end if you'd want a file without a
                                                                         file extension.
                {OKBLUE}fdel {OKCYAN}<file_name> {ORANGE}[{OKCYAN}!nodef{ORANGE}]{ENDC}     : Delete a file in the current path. 
                                                The file automatically defaults to a .txt
                                                file, so you'd have to put {OKCYAN}!nodef{ENDC}
                                                in the end if you'd want a file without a
                                                file extension.
                                                (You need to confirm in order to delete the file first.)
                {OKBLUE}fcopy {OKCYAN}<file_name> {YELLOW}<dir_name> {ORANGE}[{OKCYAN}!nodef{ORANGE}]{ENDC}     : Copy the file {OKCYAN}file_name{ENDC} into
                                                            the directory {OKCYAN}dir_name{ENDC}.
                                                            If there is no directory name specified,
                                                            there will be an automatically generated directory
                                                            that the file gets copied into. {OKCYAN}!nodef
                                                            {ENDC}assures that the file name doesn't include
                                                            a file extension. If the directory {OKCYAN}dir_name 
                                                            {ENDC}already exists, it will check for available directory names.
                {OKBLUE}dirmake {OKCYAN}<dir_name>{ENDC}            : Create a directory in the current path.
                {OKBLUE}dirdel {OKCYAN}<dir_name>{ENDC}             : Delete a directory in the current path.
                                                If a directory is protected (for example, {OKCYAN}C:\Users\user1\Documents{ENDC}), 
                                                this will not run and will quit the console instead.
                {OKBLUE}dirdel {OKCYAN}current{ENDC}                : Delete the current console path.
                {OKBLUE}<file_name>{ENDC}                   : Opens the file {OKCYAN}file_name{ENDC}.""")
        case "script help":
            print(fr"""
                -- Script
                {OKBLUE}xcon script {OKCYAN}<script_file>{ENDC}     : Runs a XCon script from a file inside the console. 
                                                (Make sure your file is a {YELLOW}.xcon{ENDC} file!)
                {OKBLUE}python script {OKCYAN}<script_file>{ENDC}   : Runs a Python script from a file inside the console. 
                                                (Make sure your file is a {YELLOW}.py{ENDC} file!)
                {OKBLUE}python run {OKCYAN}<python_command>{ENDC}   : Runs a Python command through the console.
                                                                      This can also run a function, but make sure to
                                                                      define the function first with the command
                                                                      {OKBLUE}'python block {YELLOW}!x {ORANGE} {OKCYAN}<func>:'{ENDC}.
                {OKBLUE}python block {OKCYAN}!x <block>{ENDC}       : Runs a Python block, automatically indenting for you.
                                                                      To make your code block run, type {OKCYAN}!end{ENDC}
                                                                      at the end of your code block.""")
        case "variables help":
            print(fr"""
                -- Variables
                {OKBLUE}varmake {OKCYAN}<var_name> {YELLOW}set {OKCYAN}<var_value>{ENDC}   : Declare a variable with a value. 
                                                       (You can also set an existing variable to an other value.)
                                                       XCon Console commands are an exception, you cannot 
                                                       overwrite those.
                                                       Also, be cautious about data types. If declared a variable
                                                       'x', {OKBLUE}varmake {OKCYAN}y {YELLOW}set {OKCYAN}x{ENDC} will make y hold the value of x.
                                                       {OKBLUE}varmake {OKCYAN}y {WARNING}set {ORANGE}"x"{ENDC} will make y hold the {OKBLUE}*string*{ENDC} {ORANGE}"x"{ENDC}.
                {OKBLUE}vardel {OKCYAN}<var_name>{ENDC}             : Removes a variable from the current scope.
                {OKBLUE}vardel {ORANGE}all{ENDC}                    : Removes all variable from the current scope.
                {OKBLUE}save {OKCYAN}vars{ENDC}                     : Attempts to save all variables defined in the
                                                                      current context.
                {OKBLUE}load {OKCYAN}vars{ENDC}                     : Attempts to load all variables saved in the
                                                                      current context.
                {OKBLUE}see {OKCYAN}<var_name>{ENDC}                : Displays the value of a variable.
                {OKBLUE}see {OKCYAN}globals{ENDC}                   : Displays all the global values in the current context.
                {OKBLUE}see {OKCYAN}declared{ENDC}                  : Displays all defined variables in the current context. 
                                                This will only display something if you have any variables declared.
                {OKBLUE}see {OKCYAN}packages{ENDC}                  : Displays all packages manually installed with 
                                                                      {OKBLUE}install {OKCYAN}<package_name>{ENDC}.
                {HEADER}@variable{ENDC}                     : Gets evaluated as a variable. You won't need this with
                                                commands like {OKBLUE}see {OKCYAN}<var_name>{ENDC}, but you
                                                can use this for other commands that don't support it.""")
        case "conditions help":
            print(fr"""
                -- Conditions
                {OKBLUE}check {OKCYAN}<condition>{ENDC}             : Checks if a certain condition is true or not.
                {OKBLUE}check {OKCYAN}<any>{ENDC}                   : This can be anything, for example, this can check the
                                                value of the hexadecimal digit {OKCYAN}0x8c{ENDC}, and this is made
                                                to get a certain value that hasn't been paired with a 
                                                variable yet.
                {OKBLUE}check type {OKCYAN}<var_name>{ENDC}             : Checks what type {OKCYAN}var_name{ENDC} is.
                {OKBLUE}check {OKCYAN}<file_name> {WARNING}exists{ENDC}      : Checks if a certain file exists in the current context.
                {OKBLUE}check {OKCYAN}<dir_name> {WARNING}exists{ENDC}       : Checks if a certain directory exists in the current context.""")
        case "utilities help":
            print(fr"""
                -- Utilities & Extra's
                {OKBLUE}echo {OKCYAN}<text>{ENDC}                   : Prints out text to the stream. 
                                                For variables, you might just want to use {OKBLUE}see {OKCYAN}<var_name>{ENDC},
                                                but {OKBLUE}echo {OKCYAN}<var_name>{ENDC} is possible as well.
                {OKBLUE}command {OKCYAN}history {ORANGE}[{OKCYAN}!r{ORANGE}]{ENDC}          : Shows the command history in the current context.
                                                The {OKCYAN}!r{ENDC} indicator at the end reverses the command
                                                history, showing the oldest commands first, building
                                                up to the most recent commands.
                {OKBLUE}command {OKCYAN}search {WARNING}<command_name>{ENDC} : Searches for appearances of the command {OKCYAN}<command_name> {ENDC}in the 
                                                current context.
                {COMMENT}$ Some comment here{ENDC}           : Makes a comment. Comments are ignored in code and input.
                                                In order to escape comments and make a genuine dollar sign ($),
                                                you'll need to use the escape sequence instead of a single $,
                                                {OKBLUE}$${ENDC}.
                {OKBLUE}info{ENDC}                          : Show console information.
                {OKBLUE}version{ENDC}                       : Show the current version.
                {OKBLUE}wipe{ENDC}                          : Clears everything off the console screen.
                {OKBLUE}no color{ENDC}                          : Clears all the vivid colors off the console window.
                {OKBLUE}empty bin{ENDC}                     : Clears the recycle bin. (Only supported on Windows.)
                {OKBLUE}close{ENDC}                         : Close the program.
                {OKBLUE}python{ENDC}                        : (Easter egg - try it.)
                {OKBLUE}meow{ENDC}                          : Cat says meow back!
                {OKBLUE}nya{ENDC}                           : {PINK}Nya~!{ENDC}
                {OKBLUE}what is reality{ENDC}               : What {BOLD}is{ENDC} reality? What's your reality?""")
        case "help":
            print(fr"""
            {OKCYAN}XCon Console Help:{ENDC}
                ------------------

                -- Path
                {OKBLUE}chgpath {OKCYAN}<path>{ENDC}                : Change the current path to execute commands from.
                {OKBLUE}chgpath {OKCYAN}root{ENDC}                  : Change path to root directory (usually {OKCYAN}C:\{ENDC}).
                {OKBLUE}chgpath {OKCYAN}up{ENDC}                    : Change to the parent folder of the current path.
                
                -- Inspection
                {OKBLUE}inspect folder {OKCYAN}<folder_name>{ENDC}  : Inspects all items in folder_name.
                {OKBLUE}inspect folder {OKCYAN}<folder_name> {YELLOW}all {OKCYAN}<file_extension>{ENDC}           : Get all files in {OKCYAN}folder_name{ENDC}
                                                                              that have the file extension 
                                                                              {OKCYAN}file_extension{ENDC}.
                {OKBLUE}inspect file {OKCYAN}<file_name>{ENDC}      : Reads all lines from a file (if possible).
                {OKBLUE}inspect file text {WARNING}<text> {OKCYAN}<file_name>{ENDC}       : Reads a specific piece of text from the file
                                                             and returns the amount of times the text 
                                                             has been repeated inside of {OKCYAN}file_name.

                -- Modules
                {OKBLUE}access module {OKCYAN}<module_name>{ENDC}   : Access (or simpler, import) the module {OKCYAN}module_name{ENDC}.
                {OKBLUE}module {OKCYAN}<module_name>{ENDC}          : Returns the type of {OKCYAN}module_name{ENDC}.
                {OKBLUE}install {OKCYAN}<package_name>{ENDC}        : Attempts to install the global package {OKCYAN}package_name{ENDC}.
                {OKCYAN}<package_name> {OKBLUE}info{ENDC}           : Gathers information about the package {OKCYAN}package_name{ENDC}.
                {OKBLUE}installer {OKCYAN}upgrade{ENDC}             : Attempts to upgrade/update the installer to the latest version.
                
                -- Internal
                {OKBLUE}process shutdown {ORANGE}!r{ENDC}           : Restart the computer.
                Options: {ORANGE}[!f: close files] [!fw: firmware]
                         [!o: advanced boot options] [!i: show remote shutdown]
                         [!sf: soft close programs] [!e: enable shutdown docs]
                         [!t {OKCYAN}<seconds>{ORANGE}: restart in {OKCYAN}<seconds> {ORANGE}seconds]{ENDC}

                {OKBLUE}process shutdown {ORANGE}!s{ENDC}           : Shut down the computer (same options as above).
                Options: {ORANGE}[!f: close files] [!fw: firmware]
                         [!o: advanced boot options] [!i: show remote shutdown]
                         [!sf: soft close programs] [!e: enable shutdown docs]
                         [!t {OKCYAN}<seconds>{ORANGE}: shutdown in {OKCYAN}<seconds> {ORANGE}seconds]{ENDC}
                {OKBLUE}process shutdown {ORANGE}!h{ENDC}           : Hibernate the computer (use {ORANGE}!f{ENDC} to close files).
                Options: {ORANGE}[!f: close files] [!l: sign out]{ENDC}
                {OKBLUE}process {ORANGE}sleep{ENDC}                 : Put the computer to sleep.
                Options: {ORANGE}[none]{ENDC}
                -- You may need to download packages manually or with {OKBLUE}install {OKCYAN}<package>{ENDC} with the following:
                {OKBLUE}set volume {OKCYAN}<volume_value>{ENDC}     : Sets the current volume to {OKCYAN}volume_value{ENDC}.
                {OKBLUE}mute volume{ENDC}                   : Mutes the volume.
                {OKBLUE}console {OKCYAN}<command>{ENDC}             : Runs a command directly through the console. 
                                                {WARNING}Note: Not all commands will run as expected through XCon.{ENDC}

                -- File I/O
                {OKBLUE}fmake {OKCYAN}<file_name> {ORANGE}[{OKCYAN}^ {WARNING}<content> {YELLOW}[{OKBLUE}| {YELLOW}<- multiline indc.]{ORANGE}] [{OKCYAN}!append {ORANGE}or {OKCYAN}| !append{ORANGE}] [{OKCYAN}!nodef{ORANGE}]{ENDC}   : Create 
                                                                         a file,  optionally write content 
                                                                         with the {OKCYAN}^{ENDC} indicator.
                                                                         With the {OKCYAN}!append{ENDC} indicator, 
                                                                         you tell the console you don't want to 
                                                                         overwrite anything, 
                                                                         just add text to it.
                                                                         The file automatically defaults to a .txt
                                                                         file, so you'd have to put {OKCYAN}!nodef{ENDC}
                                                                         in the end if you'd want a file without a
                                                                         file extension.
                {OKBLUE}fdel {OKCYAN}<file_name> {ORANGE}[{OKCYAN}!nodef{ORANGE}]{ENDC}     : Delete a file in the current path. 
                                                The file automatically defaults to a .txt
                                                file, so you'd have to put {OKCYAN}!nodef{ENDC}
                                                in the end if you'd want a file without a
                                                file extension.
                                                (You need to confirm in order to delete the file first.)
                {OKBLUE}fcopy {OKCYAN}<file_name> {YELLOW}<dir_name> {ORANGE}[{OKCYAN}!nodef{ORANGE}]{ENDC}     : Copy the file {OKCYAN}file_name{ENDC} into
                                                            the directory {OKCYAN}dir_name{ENDC}.
                                                            If there is no directory name specified,
                                                            there will be an automatically generated directory
                                                            that the file gets copied into. {OKCYAN}!nodef
                                                            {ENDC}assures that the file name doesn't include
                                                            a file extension. If the directory {OKCYAN}dir_name 
                                                            {ENDC}already exists, it will check for available directory names.
                {OKBLUE}dirmake {OKCYAN}<dir_name>{ENDC}            : Create a directory in the current path.
                {OKBLUE}dirdel {OKCYAN}<dir_name>{ENDC}             : Delete a directory in the current path.
                                                If a directory is protected (for example, {OKCYAN}C:\Users\user1\Documents{ENDC}), 
                                                this will not run and will quit the console instead.
                {OKBLUE}dirdel {OKCYAN}current{ENDC}                : Delete the current console path.
                {OKBLUE}<file_name>{ENDC}                   : Opens the file {OKCYAN}file_name{ENDC}.
                
                -- Script
                {OKBLUE}xcon script {OKCYAN}<script_file>{ENDC}     : Runs a XCon script from a file inside the console. 
                                                (Make sure your file is a {YELLOW}.xcon{ENDC} file!)
                {OKBLUE}python script {OKCYAN}<script_file>{ENDC}   : Runs a Python script from a file inside the console. 
                                                (Make sure your file is a {YELLOW}.py{ENDC} file!)
                {OKBLUE}python run {OKCYAN}<python_command>{ENDC}   : Runs a Python command through the console.
                                                                      This can also run a function, but make sure to
                                                                      define the function first with the command
                                                                      {OKBLUE}'python block {YELLOW}!x {ORANGE} {OKCYAN}<func>:'{ENDC}.
                {OKBLUE}python block {OKCYAN}!x <block>{ENDC}       : Runs a Python block, automatically indenting for you.
                                                                      To make your code block run, type {OKCYAN}!end{ENDC}
                                                                      at the end of your code block.

                -- Variables
                {OKCYAN}Note: Variables get saved and loaded back in every session. There is no need to redefine them.{ENDC} 
                {OKBLUE}varmake {OKCYAN}<var_name> {WARNING}set {OKCYAN}<var_value>{ENDC}   : Declare a variable with a value. 
                                                       (You can also set an existing variable to an other value.)
                                                       XCon Console commands are an exception, you cannot 
                                                       overwrite those.
                                                       Also, be cautious about data types. If declared a variable
                                                       'x', {OKBLUE}varmake {OKCYAN}y {WARNING}set {OKCYAN}x{ENDC} will make y hold the value of x.
                                                       {OKBLUE}varmake {OKCYAN}y {WARNING}set {ORANGE}"x"{ENDC} will make y hold the {OKBLUE}*string*{ENDC} {ORANGE}"x"{ENDC}.
                {OKBLUE}vardel {OKCYAN}<var_name>{ENDC}             : Removes a variable from the current scope.
                {OKBLUE}load {OKCYAN}vars{ENDC}                     : Attempts to load all variables saved in the
                                                                      current context.
                {OKBLUE}see {OKCYAN}<var_name>{ENDC}                : Displays the value of a variable.
                {OKBLUE}see {OKCYAN}<var_name>{ENDC}                : Display the value of a variable.
                {OKBLUE}see {OKCYAN}globals{ENDC}                   : Display all the global values in the current context.
                {OKBLUE}see {OKCYAN}declared{ENDC}                  : Displays all defined variables in the current context. 
                                                This will only display something if you have any variables declared.
                {HEADER}@variable{ENDC}                     : Gets evaluated as a variable. You won't need this with
                                                commands like {OKBLUE}see {OKCYAN}<var_name>{ENDC}, but you
                                                can use this for other commands that don't support it.
                -- Conditions
                {OKBLUE}check {OKCYAN}<condition>{ENDC}             : Checks if a certain condition is true or not.
                {OKBLUE}check {OKCYAN}<any>{ENDC}                   : This can be anything, for example, this can check the
                                                value of the hexadecimal digit {OKCYAN}0x8c{ENDC}, and this is made
                                                to get a certain value that hasn't been paired with a 
                                                variable yet.
                {OKBLUE}check type {OKCYAN}<var_name>{ENDC}         : Checks what type {OKCYAN}var_name{ENDC} is.
                {OKBLUE}check {OKCYAN}<file_name> {WARNING}exists{ENDC}      : Checks if a certain file exists in the current context.
                {OKBLUE}check {OKCYAN}<dir_name> {WARNING}exists{ENDC}       : Checks if a certain directory exists in the current context.

                -- Utilities & Extra's
                {OKBLUE}echo {OKCYAN}<text>{ENDC}                   : Prints out text to the stream. 
                                                For variables, you might just want to use {OKBLUE}see {OKCYAN}<var_name>{ENDC},
                                                but {OKBLUE}echo {OKCYAN}<var_name>{ENDC} is possible as well.
                {OKBLUE}command {OKCYAN}history {ORANGE}[{OKCYAN}!r{ORANGE}]{ENDC}          : Shows the command history in the current context.
                                                The {OKCYAN}!r{ENDC} indicator at the end reverses the command
                                                history, showing the oldest commands first, building
                                                up to the most recent commands.
                {OKBLUE}command {OKCYAN}search {WARNING}<command_name>{ENDC} : Searches for appearances of the command {OKCYAN}<command_name> {ENDC}in the 
                                                current context.
                {COMMENT}$ Some comment here{ENDC}           : Makes a comment. Comments are ignored in code and input.
                                                In order to escape comments and make a genuine dollar sign ($),
                                                you'll need to use the escape sequence instead of a single $,
                                                {OKBLUE}$${ENDC}.
                {OKBLUE}info{ENDC}                          : Show console information.
                {OKBLUE}version{ENDC}                       : Show the current version.
                {OKBLUE}wipe{ENDC}                          : Clears everything off the console screen.
                {OKBLUE}no color{ENDC}                      : Clears all the vivid colors off the console window.
                {OKBLUE}empty bin{ENDC}                     : Clears the recycle bin. (Only supported on Windows.)
                {OKBLUE}close{ENDC}                         : Close the program.
                {OKBLUE}python{ENDC}                        : (Easter egg - try it.)
                {OKBLUE}meow{ENDC}                          : Cat says meow back!
                {OKBLUE}nya{ENDC}                           : {PINK}Nya~!{ENDC}
                {OKBLUE}what is reality{ENDC}               : What {BOLD}is{ENDC} reality? What's your reality?
                
                -- Shortcuts
                {OKBLUE}path {OKCYAN}help{ENDC}                     : Shows information only about the path section to avoid clutter.
                {OKBLUE}inspect {OKCYAN}help{ENDC}                  : Shows information only about file or directory inspection to
                                                avoid clutter.
                {OKBLUE}modules {OKCYAN}help{ENDC}                  : Shows information only about modules to avoid clutter.
                {OKBLUE}internal {OKCYAN}help{ENDC}                 : Shows information only about internal commands to
                                                avoid clutter.
                {OKBLUE}io {OKCYAN}help{ENDC}                       : Shows information only about file I/O to avoid clutter.
                {OKBLUE}script {OKCYAN}help{ENDC}                   : Shows information only about script commands to avoid clutter.
                {OKBLUE}variables {OKCYAN}help{ENDC}                : Shows information only about variables to avoid clutter.
                {OKBLUE}conditions {OKCYAN}help{ENDC}               : Shows information only about conditions to avoid clutter.
                {OKBLUE}utilities {OKCYAN}help{ENDC}                : Shows information only about utilities and extra's to avoid
                                                clutter.

                XCon 2025 Ltd.
                """)
        case _:
            if prompt:
                try:
                    result = subprocess.run(prompt, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"{prompt} is not recognized by the XCon Console.")
                    else:
                        pass
                except Exception as e:
                    print(f"An exception occurred while trying to run command. Cause:\n\n{e}")
    
def __console():
    global LAST
    global RESERVED
    __load_vars()
    print(f"{OKCYAN}>>>>> {HEADER}XCon Console Ltd. 2025\nUse for educational purposes.")
    while True:
        try:
            PROMPT = input(f"{ENDC}{os.getcwd()} >{OKBLUE} ").strip()
            if PROMPT:
                if not PROMPT.startswith("command history"):
                    COMMAND_HISTORY.append(PROMPT)
                __handle_prompt(PROMPT)
        except Exception as e:
            print(f"{FAIL}Preventing shutdown by error:\n\n{ENDC}{e}")
            
if __name__ == "__main__":
    __console()
