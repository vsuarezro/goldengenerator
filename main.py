import datetime
import json
from copy import deepcopy
from pathlib import Path
import pprint
from difflib import Differ

import PySimpleGUI as sg
import mailmerge

import utils

sg.set_options(font=('Consolas', 12))
sg.SetOptions(element_padding=(0, 0))

settings = utils.load_settings()

golden_layout = [
    [sg.Text("Select golden:"),
     sg.Combo(utils.GOLDEN_TYPES, size=(20, 10), pad=((0, 20), (0, 0)), enable_events=True,
              tooltip="Select golden to be used", key="-GOLDENSELECT-"),
     sg.Button("Generate golden", button_color=("black", "yellow"), key="-GENERATE-"),
     sg.Button("?", button_color=("black", "yellow"), key="-HELP-"),
     sg.Input(key="-SAVEGOLDENDATA-", visible=False, enable_events=True),
     sg.FileSaveAs("Save data as ...", initial_folder=".", tooltip="Save data in this screen to a file",
                   file_types=(("Normal text file", "*.txt"),), ),
     sg.Input(key="-LOADGOLDENDATA-", visible=False, enable_events=True),
     sg.FileBrowse("Load Golden data", initial_folder="."),
     ],
    [sg.Button("", key="-RETRIEVE-", image_filename=r"./icons/twotone_download_for_offline_black_20.png",
               tooltip="Download latest golden template"), ],
    [sg.InputText("", size=(100, 1), readonly=True, key="-HASH-")],
    [sg.Multiline(size=(100, 30), text_color="black", background_color="lightgray", key="-INPUT-")]
]

mop_layout = [
    [sg.Input(key="-GETMOP-", visible=False, enable_events=True),
     sg.FileBrowse("Get MOP template",
                   initial_folder="./templates/",
                   file_types=(("Microsoft Word files", "*.docx"), ("All files", "*.*")),
                   ),
     sg.Button("", image_subsample=11, image_filename=r"./icons/generateword.png", tooltip="Generate integration MOP",
               key="-GENERATEMOP-")
     ],
    [sg.Multiline("", size=(100, 30), key="-TEMPLATEVARS-")],
]

layout = [
    [sg.Button("", key="-SETTINGS-", image_filename=r"./icons/preferences.png", image_subsample=3,
               tooltip="User settings and variables"), ],
    [sg.TabGroup([[sg.Tab('Golden', golden_layout), sg.Tab('MOP', mop_layout)]])],
    [sg.StatusBar("Ready", size=(20, 1), key="-OUTPUT-")]
]


def open_settings():
    global settings
    vars_settings = deepcopy(settings)
    repository = vars_settings.pop("repository", "")
    github_base = vars_settings.pop("github_base", "")
    token = vars_settings.pop("token", "")
    fill_secrets = vars_settings.pop("fill_secrets", False)
    vars_settings.pop("hash_NETSIMP_ASR920", "")
    vars_settings.pop("hash_NETSIMP_NCS560", "")
    vars_settings.pop("hash_IPBH_NCS540", "")
    vars_settings = utils.dict_to_text(vars_settings)

    layout = [
        [sg.Text("Repository:", size=(12, 1)), sg.InputText(repository, size=(60, 1), key="-REPOSITORY-")],
        [sg.Text("Github base:", size=(12, 1)), sg.InputText(github_base, size=(60, 1), key="-GITHUBBASE-")],
        [sg.Text("Token:", size=(12, 1)), sg.InputText(token, size=(60, 1), key="-TOKEN-")],
        [sg.Text("Fill secrets", size=(12, 1)), sg.Checkbox("", default=fill_secrets, key="-FILLSECRETS-")],
        [sg.Text("Vars:", size=(12, 1)), sg.Multiline(vars_settings, size=(60, 10), key="-SETTINGSTEXT-")],
        [sg.Button("Save settings", tooltip="Save settings", enable_events=True, key="-SAVESETTINGS-", ), ]
    ]
    window_settings = sg.Window("Settings", layout, modal=True)
    while True:
        event, values = window_settings.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        if event == "-SAVESETTINGS-":
            hash_dict = dict()
            for k, v in settings.items():
                if "hash" in k:
                    hash_dict[k] = v

            settings = utils.text_to_dict(values["-SETTINGSTEXT-"])
            settings["repository"] = values.get("-REPOSITORY-").strip()
            settings["github_base"] = values.get("-GITHUBBASE-").strip()
            settings["token"] = values.get("-TOKEN-").strip()
            settings["fill_secrets"] = values.get("-FILLSECRETS-")
            settings.update(hash_dict)
            with open("settings.json", "w", encoding="utf-8") as file:
                json.dump(settings, file)
        sg.popup_quick_message("Settings saved", keep_on_top=True)

    window_settings.close()


def open_generation(golden_text: str, fill_secrets: bool, golden_dict: dict):
    golden_text_with_secrets = utils.golden_with_secrets(deepcopy(golden_text), settings)
    text_to_show = golden_text_with_secrets if fill_secrets else golden_text

    layout = [
        [sg.Multiline(text_to_show, size=(100, 30), key="-GOLDENTEXT-")],
        [sg.Input(key="-SAVEGOLDEN-", visible=False, enable_events=True),
         sg.FileSaveAs("Save golden",
                       initial_folder=".",
                       default_extension="txt",
                       enable_events=True,
                       file_types=(("Normal text file", "*.txt"),),
                       ),
         sg.Checkbox("Fill secrets", default=settings.get("fill_secrets"), enable_events=True, key="-FILLSECRETS-"),
         sg.Button("", image_filename=r"./icons/icons8-comparing-50.png", tooltip="Compare two configurations",
                   key="-COMPARE-")]
    ]
    window_golden = sg.Window("Golden", layout, modal=True)
    while True:
        event, values = window_golden.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        if event == "-SAVEGOLDEN-":
            filename = values["-SAVEGOLDEN-"]
            if filename:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(values.get("-GOLDENTEXT-"))
                sg.popup_quick_message("Saved golden to {}".format(filename), keep_on_top=True, auto_close_duration=3)

        if event == "-FILLSECRETS-":
            if values.get("-FILLSECRETS-"):
                window_golden["-GOLDENTEXT-"].update(golden_text_with_secrets)
            else:
                window_golden["-GOLDENTEXT-"].update(golden_text)

        if event == "-COMPARE-":
            text_to_compare = open_window_gettext()
            if text_to_compare is not None:
                a_text = values.get("-GOLDENTEXT-").splitlines(keepends=True)
                b_text = text_to_compare.splitlines(keepends=True)
                diff = Differ(linejunk=lambda x: x.strip() == "")
                comparison = list(diff.compare(a_text, b_text))
                window_golden["-GOLDENTEXT-"].update("".join(comparison))
                # pprint.pprint(comparison)

        if event == "-MOP-":
            p = Path("./templates/template_integration_netsimp.docx")
            document = mailmerge.MailMerge(p)
            merge_dict = deepcopy(golden_dict)
            merge_dict["GOLDEN_CONFIG"] = golden_text
            document.merge(**merge_dict)
            try:
                document.write("output.docx")
            except PermissionError:
                sg.popup_quick_message("Permission denied to file", keep_on_top=True)
                return
            sg.popup_quick_message("MOP draft created", keep_on_top=True)

    window_golden.close()


def open_window_gettext() -> str:
    layout = [
        [sg.Multiline("", size=(100, 30), key="-TEXT-")],
        [sg.Button("OK", key="-OK-"), sg.Button("Cancel", key="-CANCEL-")]]

    window_text = sg.Window("Text to compare", layout, modal=True)
    text = None
    while True:
        event, values = window_text.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        if event == "-OK-":
            text = values.get("-TEXT-")
            break

        if event == "-CANCEL-":
            text = None
            break

    window_text.close()
    return text


# Create the window
window = sg.Window("Golden generator", layout, modal=True)
render_vars = dict()
golden_dict = None
mop_dict = None
golden_text = None

# Create an event loop
while True:
    event, values = window.read()
    # End program if user closes window or
    # presses the OK button
    if event == sg.WIN_CLOSED:
        break
    if event == "-GOLDENSELECT-":
        vars_golden = utils.load_golden(values["-GOLDENSELECT-"])
        window["-OUTPUT-"].update(values["-GOLDENSELECT-"])
        window["-INPUT-"].update(vars_golden)
        filehash = settings.get("hash_{}".format(values.get("-GOLDENSELECT-")))
        window["-HASH-"].update(filehash)

    if event == "-GENERATE-":
        if values["-GOLDENSELECT-"] == '':
            pass
        else:
            golden_dict = utils.generate_goldendict(values["-INPUT-"])
            msg = utils.validate_golden_dict(values["-GOLDENSELECT-"], golden_dict)
            if msg is not None:
                sg.ScrolledTextBox(msg, title="Error in vars")
                continue
            golden_dict = utils.complete_golden_dict(values["-GOLDENSELECT-"], golden_dict)
            print(golden_dict)
            filehash = settings.get("hash_{}".format(values["-GOLDENSELECT-"]))
            golden_text = utils.generate_golden(values["-GOLDENSELECT-"], golden_dict)
            golden_text = utils.remove_blanks(golden_text)
            hash_and_golden_text = "!{}\n!Generated {}\n\n".format(filehash, datetime.datetime.now()) + golden_text
            open_generation(hash_and_golden_text, settings.get("fill_secrets"), golden_dict)

    if event == "-HELP-":
        if values["-GOLDENSELECT-"] == '':
            pass
        else:
            vars_help = utils.load_golden(values["-GOLDENSELECT-"])
            render_vars = utils.render_vars_default_help(vars_help)
            sg.ScrolledTextBox(render_vars, title="Help on variables for {}".format(values["-GOLDENSELECT-"]),
                               size=(150, 40))

    if event == "-SAVEGOLDENDATA-":
        input_multiline = values.get("-INPUT-")
        if values.get("-SAVEGOLDENDATA-") and input_multiline:
            if input_multiline.strip() == "":
                continue
            filename = values.get("-SAVEGOLDENDATA-")
            if filename:
                window["-OUTPUT-"].update("Saving data to {}".format(filename))
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(input_multiline)

    if event == "-LOADGOLDENDATA-":
        filename = values.get("-LOADGOLDENDATA-")
        if filename:
            window["-OUTPUT-"].update("Loading data from {}".format(filename))
            with open(filename, "r", encoding="utf-8") as file:
                golden_data = file.read()
            window["-INPUT-"].update(golden_data)

    if event == "-RETRIEVE-":
        if values.get("-GOLDENSELECT-"):
            golden_file = values.get("-GOLDENSELECT-") + ".j2.golden"
            text, filehash, err = utils.retrieve(golden_file, settings)
            if err:
                window["-OUTPUT-"].update(err)
                continue
            window["-OUTPUT-"].update("Golden {} fetched from repository".format(golden_file))
            window["-HASH-"].update(filehash)
            settings["hash_{}".format(values.get("-GOLDENSELECT-"))] = filehash
            utils.save_settings(settings)
            with open(golden_file, "w", encoding="utf-8") as file:
                file.write(text)

    if event == "-GETMOP-":
        filename = values.get("-GETMOP-")
        try:
            document = mailmerge.MailMerge(filename)
        except FileNotFoundError as e:
            window["-OUTPUT-"].update("File '{}' was not found".format(filename))
            continue

        field_values = list(document.get_merge_fields())
        field_values.sort()
        document.close()
        if vars is None:
            continue
        mop_dict = dict.fromkeys(field_values, "")
        if golden_dict:
            for k in mop_dict.keys():
                mop_dict[k] = golden_dict.get(k) or ""
        mop_dict = utils.complete_mop_dict(values["-GOLDENSELECT-"], mop_dict)
        text = utils.dict_to_text(mop_dict)
        window["-TEMPLATEVARS-"].update(text)

    if event == "-GENERATEMOP-":
        if values.get("-TEMPLATEVARS-") == "":
            continue
        if mop_dict is None:
            continue
        filename = values.get("-GETMOP-")
        if filename is None or filename == "":
            continue
        try:
            document = mailmerge.MailMerge(filename)
        except FileNotFoundError as e:
            window["-OUTPUT-"].update("File '{}' was not found".format(filename))
            continue
        else:
            window["-OUTPUT-"].update("File '{}' opened for MOP generation".format(filename))
        mop_dict = utils.text_to_dict(values.get("-TEMPLATEVARS-"))
        mop_dict = utils.complete_mop_dict_code(mop_dict)
        pprint.pprint(mop_dict)
        if mop_dict.get("GOLDEN_CONFIG") is None and golden_text is not None:
            mop_dict["GOLDEN_CONFIG"] = golden_text
        document.merge(**mop_dict)

        try:
            document.write("output.docx")
        except PermissionError as e:
            sg.popup_quick_message("Permission denied to file", keep_on_top=True)
            window["-OUTPUT-"].update("Permission denied to {}".format(filename))
        else:
            window["-OUTPUT-"].update("MOP generated to {}".format("output.docx"))
        finally:
            document.close()

    if event == "-SETTINGS-":
        open_settings()

window.close()
