import datetime
from pathlib import Path
import ipaddress
import json

import yaml
from jinja2 import Environment, FileSystemLoader, meta
from schema import Schema, Or, And, Optional, Regex, Use
import requests
import github

import jinja2utils

env = Environment(loader=FileSystemLoader("."))
env.filters["prefix"] = jinja2utils.do_prefix
env.filters["rstrip"] = jinja2utils.do_rstrip
env.filters["metric"] = jinja2utils.do_metric
env.filters["module"] = jinja2utils.do_module
env.filters["sid"] = jinja2utils.do_ip_to_sid
env.tests["blue"] = jinja2utils.template_test_is_ip_blue

SEPARATOR = "\t"
LINESEP = "\n"
GOLDEN_TYPES = ["NETSIMP_ASR920", "IPBH_NCS540", "NETSIMP_NCS560"]
integration_data_file = (
    Path(__file__).absolute().parent / Path("integration.yaml")
)
file = integration_data_file.open("rb")
integration_yaml = yaml.safe_load(file)
file.close()

default_settings = (
    ("epnm community", ""), ("nagios community", ""), ("orion community", ""),
    ("netcool community", ""), ("netview community", ""), ("password BGP", ""), ("password ISIS", ""),
    ("tacacs+ secret", ""),
    ("repository", ""), ("github_base", ""), ("token", ""),
    ("hash_NETSIMP_ASR920", ""), ("hash_NETSIMP_NCS560", ""), ("hash_IPBH_NCS540", ""),
)

help_render_dict = {
    "ADDRESS_P2P_TO_AGG1": "{REQUIRED} Address from router to AGG1",
    "ADDRESS_P2P_TO_AGG2": "{REQUIRED} Address from router to second aggregator AGG2",
    "AGG1_HOSTNAME": "{REQUIRED} AGG1 Aggregation router hostname",
    "AGG2_HOSTNAME": "{REQUIRED} AGG2 Aggregation router hostname",
    "AGG1_LOOPBACK0": "[OPTIONAL] AGG1 Loopback0 IPv4 Address without mask. If not filled it's derived from "
                      "management IP address",
    "AGG2_LOOPBACK0": "[OPTIONAL] AGG2 Loopback0 IPv4 Address without mask. If not filled it's derived from management IP address",
    "AGG1_LOOPBACK_MANAGEMENT": "{REQUIRED} AGG1 router management IPv4 interface address",
    "AGG2_LOOPBACK_MANAGEMENT": "{REQUIRED} AGG2 router management IPv4 interface address",
    "AGG1_PORT": "{REQUIRED} Aggregator Router AGG1 interface. Type, if available, and ID required",
    "AGG2_PORT": "{REQUIRED} Aggregator Router AGG2 interface. Type, if available, and ID required",
    "AGGREGATION_RING": "[OPTIONAL] Aggregation ring number for CDMX or Monterrey",
    "BLUEDOMAIN": "[OPTIONAL] Do not fill unless overriding default action. Values are True or False, indicates the router has at least one connection to the Blue domain",
    "BORDER_REGION": "[OPTIONAL] True or False, indicates the router is installed in the north border region",
    "BUNDLE_UPLINK": "[OPTIONAL] True or False, indicates the router uses a bundle configuration for the uplink",
    "CITY_CODE": "[OPTIONAL] Two or four digits for BGP City code. If not filled, it's derived from SNMP_LOCATION",
    "DALIA": "[OPTIONAL] LTE route target for import and export",
    "HOSTNAME": "{REQUIRED} Hostname of the router",
    "INTERFACE_TO_AGG1": "{REQUIRED} Router connection",
    "INTERFACE_TO_AGG2": "{REQUIRED} Router connection",
    "INTERFACE_TO_AGG1_MTU": "[OPTIONAL] MTU of the interface towards the AGG1",
    "INTERFACE_TO_AGG2_MTU": "[OPTIONAL] MTU of the interface towards the second AGG2",
    "ISE_SERVER1": "{REQUIRED} First ISE Server IPv4 address",
    "ISE_SERVER2": "{REQUIRED} Second ISE Server IPv4 address",
    "ISE_SERVER3": "{REQUIRED} Third ISE Server IPv4 address",
    "LOOPBACK0": "{REQUIRED} LOOPBACK0 IP address of the router to be integrated",
    "LOOPBACK_MANAGEMENT": "{REQUIRED} Management IP address Loopback1 of the router to be integrated",
    "MODEL": "[OPTIONAL: ASR920] Indicates the model of the ASR920. Only considered specific case  is 'ASR920-12CZ-D'",
    "NETID": "{REQUIRED} ISIS router Net ID",
    "NTP_SERVER1": "[OPTIONAL] NTP server IP address 1 if it is different from the AGG1 Loopback address",
    "NTP_SERVER2": "[OPTIONAL] NTP server IP address 2 if it is different from the AGG2 Loopback address",
    "NTP_SERVER3": "[OPTIONAL] NTP server IP address 3 ",
    "REDDOMAIN": "[OPTIONAL] do not fill unless overriding default action. Values are True or False, indicates the router has at least one connection to the Red domain",
    "REGION": "[OPTIONAL] Region of the router, values from 1 to 9. If not given, STATE value from SNMP_LOCATION is used to get it",
    "RT3G": "<SCRIPT GENERATED> do not fill",
    "RTLTE": "<SCRIPT GENERATED> do not fill",
    "SNMP_LOCATION": "{REQUIRED} PLace where the router is installed STATE, CITY, PLACE",
    "STATE": "[OPTIONAL] do not fill unless overriding SNMP_LOCATION. Used to decide code based on STATE, like TIMEZONE",
    "TIMEZONE": "<SCRIPT GENERATED> do not fill. Uses SNMP_LOCATION and STATE value instead",
    "X2": "[OPTIONAL] Two digits representing the X2_CITY_CODE value. If not given, value is derived from the city value in SNMP_LOCATION",
    "ADDRESS_P2P_TO_TEF1": "[OPTIONAL] First Point to point address to TEF router. Required if PDC_DALIA is True",
    "ADDRESS_P2P_TO_TEF2": "[OPTIONAL] Second Point to point address to TEF router. Required if PDC_DALIA is True",
    "PDC_DALIA": "[OPTIONAL] True or False, indicates if router connects to a TEF router",
    "ADDRESS_P2P_TO_UPLINK1": "{REQUIRED} Point to point address from router to its first neighbor router in the ring. Do not include mask",
    "ADDRESS_P2P_TO_UPLINK2": "{REQUIRED} Point to point address from router to its second neighbor router in the ring. Do not include mask",
    "INTERFACE_TO_UPLINK1": "{REQUIRED} Interface to first neighbor router in the ring. Requires interface type and ID",
    "INTERFACE_TO_UPLINK2": "{REQUIRED} Interface to second neighbor router in the ring. Requires interface type and ID",
    "UPLINK1_HOSTNAME": "{REQUIRED} Hostname of the first neighbor router in the ring",
    "UPLINK2_HOSTNAME": "{REQUIRED} Hostname of the second neighbor router in the ring",
    "UPLINK1_PORT": "{REQUIRED} First neighbor router port. Used for local description on INTERFACE_TO_UPLINK1",
    "UPLINK2_PORT": "{REQUIRED} Second neighbor router port. Used for local description on INTERFACE_TO_UPLINK2",
    "INTERFACE_TO_GPON": "[OPTIONAL] Interface to a GPON connection different from the uplink interfaces",
    "VLAN_TO_GPON": "[OPTIONAL] VLAN value to use for the GPON connection",
    "ADDRESS_P2P_TO_GPON": "[OPTIONAL] Point to point interface to neighbor router over a GPON connection. Do not include mask",
    "GPON_REMOTE_ROUTER_HOSTNAME": "[OPTIONAL] Remote router hostname over the GPON connection",
    "GPON_REMOTE_ROUTER_PORT": "[OPTIONAL] Remote router interface ID over the GPON connection",
    "INTERFACE_TO_TEF1": "[OPTIONAL] Interface to connect to TEF router on first bundle",
    "INTERFACE_TO_TEF2": "[OPTIONAL] Interface to connect to TEF router on second bundle",
}

netsim_asr920_schema = Schema(
    {
        "ADDRESS_P2P_TO_AGG1": str,
        "ADDRESS_P2P_TO_AGG2": str,
        "AGG1_HOSTNAME": Regex(r"[\w\d]{10,30}"),
        "AGG2_HOSTNAME": Regex(r"[\w\d]{10,30}"),
        Optional("AGG1_LOOPBACK0"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("AGG2_LOOPBACK0"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG1_LOOPBACK_MANAGEMENT": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG2_LOOPBACK_MANAGEMENT": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG1_PORT": str,
        "AGG2_PORT": str,
        Optional("AGGREGATION_RING"): Regex(r"\d{1,2}"),
        Optional("BLUEDOMAIN"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("BORDER_REGION"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("BUNDLE_UPLINK"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("CITY_CODE"): Regex(r"\d{2,4}"),
        Optional("DALIA"):  Regex(r"[\d\:]+"),
        "HOSTNAME": Regex(r"[\w\d]{10,30}"),
        "INTERFACE_TO_AGG1": Regex(r"(Ten|Gig)\d\/\d\/\d"),
        "INTERFACE_TO_AGG2": Regex(r"(Ten|Gig)\d\/\d\/\d"),
        Optional("INTERFACE_TO_AGG1_MTU"): Regex(r"\d{4}"),
        Optional("INTERFACE_TO_AGG2_MTU"): Regex(r"\d{4}"),
        "ISE_SERVER1": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "ISE_SERVER2": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "ISE_SERVER3": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "LOOPBACK0": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "LOOPBACK_MANAGEMENT":  Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("MODEL"): "ASR920-12CZ-D",
        "NETID": str,
        Optional("NTP_SERVER1"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("NTP_SERVER2"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("NTP_SERVER3"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("REDDOMAIN"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("REGION"): Regex("[1-9]"),
        "SNMP_LOCATION": str,
        Optional("STATE"): str,
        Optional("X2"): Regex(r"\d{2}"),
    }
)

netsim_ncs560_schema = Schema(
    {
        "ADDRESS_P2P_TO_AGG1": str,
        "ADDRESS_P2P_TO_AGG2": str,
        Optional("ADDRESS_P2P_TO_TEF1"): str,
        Optional("ADDRESS_P2P_TO_TEF2"): str,
        "AGG1_HOSTNAME": Regex(r"[\w\d]{10,30}"),
        "AGG2_HOSTNAME": Regex(r"[\w\d]{10,30}"),
        Optional("AGG1_LOOPBACK0"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("AGG2_LOOPBACK0"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG1_LOOPBACK_MANAGEMENT": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG2_LOOPBACK_MANAGEMENT": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG1_PORT": Or(Regex(r"\d{1,2}\/[1-2]\/\d{1,2}"), Regex(r"\w+(\d\/)+\d"), error="Aggregation AGG1 port format is incorrect"),
        "AGG2_PORT": Or(Regex(r"\d{1,2}\/[1-2]\/\d{1,2}"), Regex(r"\w+(\d\/)+\d"), error="Aggregation AGG2 port format is incorrect"),
        Optional("AGGREGATION_RING"): Regex(r"\d{1,2}"),
        Optional("BLUEDOMAIN"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("BUNDLE_UPLINK"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("CITY_CODE"): Regex(r"\d{2,4}"),  # TODO validation or completion
        Optional("DALIA"): Regex(r"[\d\:]+"),
        "HOSTNAME": Regex(r"[\w\d]{10,30}"),
        "INTERFACE_TO_AGG1": Regex(r"(Ten|Gig)\d\/\d\/\d\/\d"),
        "INTERFACE_TO_AGG2": Regex(r"(Ten|Gig)\d\/\d\/\d\/\d"),
        Optional("INTERFACE_TO_AGG1_MTU"): Regex(r"\d{4}"),
        Optional("INTERFACE_TO_AGG2_MTU"): Regex(r"\d{4}"),
        Optional("INTERFACE_TO_TEF1"): Regex(r"(Ten|Gig)\d\/\d\/\d\/\d"),
        Optional("INTERFACE_TO_TEF2"): Regex(r"(Ten|Gig)\d\/\d\/\d\/\d"),
        "ISE_SERVER1": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "ISE_SERVER2": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "ISE_SERVER3": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "LOOPBACK0": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "LOOPBACK_MANAGEMENT":  Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "NETID": str,
        Optional("NTP_SERVER1"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("NTP_SERVER2"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("NTP_SERVER3"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("PDC_DALIA"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("REDDOMAIN"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("REGION"): Regex("[1-9]"),
        "SNMP_LOCATION": str,
        Optional("X2"): Regex(r"\d{2}"),
    }
)

ipbh_ncs540_schema = Schema(
    {
        Optional("ADDRESS_P2P_TO_GPON"): str,
        "ADDRESS_P2P_TO_UPLINK1": str,
        "ADDRESS_P2P_TO_UPLINK2": str,
        "AGG1_HOSTNAME": Regex(r"[\w\d]{10,30}"),
        "AGG2_HOSTNAME": Regex(r"[\w\d]{10,30}"),
        "AGG1_LOOPBACK0": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG2_LOOPBACK0": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG1_LOOPBACK_MANAGEMENT": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "AGG2_LOOPBACK_MANAGEMENT": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("AGGREGATION_RING"): Regex(r"\d{1,2}"),
        Optional("BLUEDOMAIN"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        "CITY_CODE": Regex(r"\d{2,4}"),
        Optional("DALIA"): str,
        Optional("GPON_REMOTE_ROUTER_HOSTNAME"): str,
        Optional("GPON_REMOTE_ROUTER_PORT"): str,
        "HOSTNAME": Regex(r"[\w\d]{10,30}"),
        Optional("INTERFACE_TO_GPON"): str,
        "INTERFACE_TO_UPLINK1": Regex(r"(Ten|Gig)\d\/\d\/\d"),
        "INTERFACE_TO_UPLINK2": Regex(r"(Ten|Gig)\d\/\d\/\d"),
        "ISE_SERVER1": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "ISE_SERVER2": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "ISE_SERVER3": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "LOOPBACK0": Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "LOOPBACK_MANAGEMENT":  Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        "NETID": str,
        Optional("NTP_SERVER1"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("NTP_SERVER2"): Regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        Optional("REDDOMAIN"): And(Use(lambda x: True if x == "True" or x == "1" else False)),
        Optional("REGION"): Regex(r"[1-9]"),
        "SNMP_LOCATION": str,
        "UPLINK1_HOSTNAME": str,
        "UPLINK2_HOSTNAME": str,
        "UPLINK1_PORT": str,
        "UPLINK2_PORT": str,
        Optional("VLAN_TO_GPON"): str,
        Optional("X2"): str,
    }
)


def load_settings() -> dict:
    settings_path = Path("settings.json")
    settings_dict = dict(default_settings)

    if not settings_path.exists() or not settings_path.is_file():
        # settings file does not exist, so one needs to be created with defaults
        file = settings_path.open("w", encoding="utf-8")
        json.dump(settings_dict, file)
        file.close()

    # settings file exists but and we don't know if settings are valid
    file = settings_path.open("r", encoding="utf-8")

    try:
        settings_dict = json.load(file)
    except ValueError:
        # sg.popup_quick_message("Invalid settings file. Recreating it")
        # default values are loaded into settings_dict
        settings_dict = dict(default_settings)
        file = settings_path.open("w", encoding="utf-8")
        json.dump(settings_dict, file)
    finally:
        file.close()

    # at this point settings_dict must have settings and file exists
    if settings_dict is None:
        return {}

    return settings_dict


def load_golden(golden_type: str) -> str:
    """
    Reads a jinja2.Template file and gets all variables expected for that file
    :param golden_type: Value for the jinja2.Template  file to be used
    :return: a string of all jinja2 variables containing that template, separated by LINESEP
    """
    filename = golden_type + ".j2.golden"

    template_source = env.loader.get_source(env, filename)
    dummy_parsed_content = env.parse(template_source)
    vars_set = meta.find_undeclared_variables(dummy_parsed_content)
    vars_list = list(vars_set)
    vars_list.sort()
    vars_str = LINESEP.join([x + SEPARATOR for x in vars_list])
    return vars_str


def generate_goldendict(input_str: str) -> dict:
    goldenvars_dict = dict()
    for line in input_str.split("\n"):
        line_vars = line.split("\t")
        if len(line_vars) == 1 or (len(line_vars) >= 2 and line_vars[1] == ''):
            pass
        elif len(line_vars) == 2:
            goldenvars_dict[line_vars[0]] = line_vars[1]

    return goldenvars_dict


def generate_golden(golden_type: str, render_dict: dict) -> str:
    if golden_type in GOLDEN_TYPES:
        template = env.get_template(golden_type+".j2.golden")
        golden_text = template.render(**render_dict)
        return golden_text


def render_vars_default_help(vars_default: str) -> dict:
    result_str = ""
    for line in vars_default.split("\n"):
        line_vars = line.split("\t")
        if len(line_vars) == 1 or (len(line_vars) == 2 and line_vars[1] == ""):
            line_var = "{}{}{}\n".format(line_vars[0], SEPARATOR, help_render_dict.get(line_vars[0].strip()))
            result_str += line_var
    return result_str


def validate_golden_dict(golden_type: str, golden_dict: dict) -> str:
    golden_schema = None
    if golden_type in GOLDEN_TYPES:
        if golden_type == "NETSIMP_ASR920":
            golden_schema = netsim_asr920_schema
        elif golden_type == "NETSIMP_NCS560":
            golden_schema = netsim_ncs560_schema
        elif golden_type == "IPBH_NCS540":
            golden_schema = ipbh_ncs540_schema
        else:
            return "No valid schema found for {}".format(golden_type)
    try:
        golden_schema.validate(golden_dict)
    except Exception as e:
        print(e)
        return e


def retrieve(golden_file: str, settings: dict) -> tuple:
    g = github.Github(base_url=settings.get("github_base"), login_or_token=settings.get("token"))
    try:
        repository = g.get_repo(full_name_or_id=settings.get("repository"))
    except (github.GithubException, requests.exceptions.ConnectionError,) as e:
        return None, None, e

    try:
        content = repository.get_contents(golden_file)
    except github.GithubException as e:
        return None, None, e

    golden_text = content.decoded_content.decode(encoding="utf-8")
    hash_str = "sha {} size {}".format(content.sha, content.size)
    return golden_text, hash_str, None


def remove_blanks(golden_text: str) -> str:
    text = LINESEP
    for line in golden_text.splitlines():
        if line.strip() == "":
            pass
        else:
            text += "\n{}".format(line.rstrip())
    return text


def complete_mop_dict(golden_type: str, mop_dict: dict) -> dict:
    if "NETSIMP_NCS560" in golden_type:
        mop_dict["DEVICE"] = "NCS560"
        mop_dict["IMAGEN"] = "7.1.2"
        mop_dict["INTERFACE_TO_CX"] = "Gig0/5/0/12"
        mop_dict["CODE_PREMW"] = "./templates/premw_NCS560.txt"
        mop_dict["CODE_POSTMW"] = "./templates/postmw_NCS560.txt"
        mop_dict["CODE_CHECKPOINT"] = "./templates/checkpoint_NCS560.txt"
        mop_dict["CODE_INTERFACES"] = "./templates/interfaces_NCS560.txt"
    elif "NETSIMP_ASR920" in golden_type:
        mop_dict["DEVICE"] = "ASR920"
        mop_dict["IMAGEN"] = "16.12.3"
        mop_dict["INTERFACE_TO_CX"] = "Gig0/0/11"
        mop_dict["CODE_PREMW"] = "./templates/premw_ASR920.txt"
        mop_dict["CODE_POSTMW"] = "./templates/postmw_ASR920.txt"
        mop_dict["CODE_CHECKPOINT"] = "./templates/checkpoint_ASR920.txt"
        mop_dict["CODE_INTERFACES"] = "./templates/interfaces_ASR920.txt"
    elif "NCS540" in golden_type:
        mop_dict["DEVICE"] = "NCS540"
        mop_dict["IMAGEN"] = "7.3.1"
        mop_dict["CODE_PREMW"] = "./templates/premw_NCS540.txt"
        mop_dict["CODE_POSTMW"] = "./templates/postmw_NCS540.txt"
        mop_dict["CODE_CHECKPOINT"] = "./templates/checkpoint_NCS540.txt"
        mop_dict["CODE_INTERFACES"] = "./templates/interfaces_NCS540.txt"

    mop_dict["DATE"] = datetime.datetime.strftime(datetime.datetime.now(), "%d-%m-%Y")
    datetime.datetime.now()
    if mop_dict.get("ADDRESS_P2P_TO_AGG1"):
        mop_dict["AGG1_P2P"] = str(ipaddress.ip_interface(mop_dict["ADDRESS_P2P_TO_AGG1"]) - 1)[:-3]
    if mop_dict.get("ADDRESS_P2P_TO_AGG2"):
        mop_dict["AGG2_P2P"] = str(ipaddress.ip_interface(mop_dict["ADDRESS_P2P_TO_AGG2"]) - 1)[:-3]

    return mop_dict


def complete_mop_dict_code(mop_dict: dict) -> dict:
    if mop_dict.get("PREMW_CODE_TRANSPORT"):
        if Path(mop_dict.get("PREMW_CODE_TRANSPORT")).is_file():
            postmw_code = Path(mop_dict.get("PREMW_CODE_TRANSPORT")).read_text(encoding="utf-8")
            mop_dict["PREMW_CODE_TRANSPORT"] = postmw_code

    if mop_dict.get("POSTMW_CODE_TRANSPORT"):
        if Path(mop_dict.get("POSTMW_CODE_TRANSPORT")).is_file():
            postmw_code = Path(mop_dict.get("POSTMW_CODE_TRANSPORT")).read_text(encoding="utf-8")
            mop_dict["POSTMW_CODE_TRANSPORT"] = postmw_code

    if mop_dict.get("CHECKPOINTCOMMANDS"):
        if Path(mop_dict.get("CHECKPOINTCOMMANDS")).is_file():
            postmw_code = Path(mop_dict.get("CHECKPOINTCOMMANDS")).read_text(encoding="utf-8")
            mop_dict["CHECKPOINTCOMMANDS"] = postmw_code

    return mop_dict


def complete_golden_dict(golden_type: str, golden_dict: dict) -> dict:

    # STATE, REGION, TIMEZONE
    if golden_dict.get("STATE") is None:
        golden_dict["STATE"] = _get_state(golden_dict)
    if golden_dict.get("REGION") is None:
        golden_dict["REGION"] = _get_region(golden_dict)
    if golden_dict.get("SITENAME") is None:
        golden_dict["SITENAME"] = _get_sitename(golden_dict)

    if "ASR920" in golden_type:
        golden_dict["TIMEZONE"] = _get_timezoneXE(golden_dict)
    else:
        golden_dict["TIMEZONE"] = _get_timezoneXR(golden_dict)

    # BLUE and RED domains
    if golden_dict.get("BLUEDOMAIN") is None:
        golden_dict["BLUEDOMAIN"] = _get_bluedomain(golden_dict)
    if golden_dict.get("REDDOMAIN") is None:
        golden_dict["REDDOMAIN"] = _get_reddomain(golden_dict)

    # RT3G
    golden_dict["RT3G"] = integration_yaml.get("3G_R{}".format(golden_dict.get("REGION")))
    if golden_dict.get("RT3G") is None:
        golden_dict["RT3G"] = "65000:1001910"

    # RTLTE
    golden_dict["RTLTE"] = integration_yaml.get("LTE_R{}".format(golden_dict.get("REGION")))
    if golden_dict.get("RTLTE") is None:
        golden_dict["RTLTE"] = "65000:1002901"

    # X2
    if golden_dict.get("X2") is None:
        golden_dict["X2"] = _get_lte_x2(golden_dict)
    else:
        golden_dict["X2"] = "65000:1002{}{}".format(golden_dict.get("REGION").strip(), golden_dict.get("X2").strip())
    return golden_dict


def _get_state(golden_dict: dict) -> str:
    if golden_dict.get("STATE") is None:
        state, city, sitename = golden_dict.get("SNMP_LOCATION").split(",")
        state = state.upper()
        return state.strip()
    return "<STATE NOT FOUND>"


def _get_sitename(golden_dict: dict) -> str:
    if golden_dict.get("SITENAME") is None:
        state, city, sitename = golden_dict.get("SNMP_LOCATION").split(",")
        sitename = sitename.upper()
        return sitename.strip()
    return "<SITENAME NOT FOUND>"


def _get_region(golden_dict: dict) -> str:
    if golden_dict.get("STATE") is None:
        if golden_dict.get("SNMP_LOCATION") is None:
            return "<REGION NOT FOUND>"
        else:
            state, _ = golden_dict.get("SNMP_LOCATION").split(1)
            state = state.strip()
            region = integration_yaml["REGIONS"].get(state.lower())
            if region is None:
                return "<REGION NOT FOUND>"
    else:
        state = golden_dict.get("STATE")
        region = integration_yaml["REGIONS"].get(state.lower())
        if region is None:
            return "<REGION NOT FOUND>"
    return region


def _get_timezoneXE(golden_dict: dict) -> str:
    unknown = "<UNKNOWN TIMEZONE>"
    if golden_dict.get("STATE") is None and golden_dict.get("SNMP_LOCATION") is None:
        return unknown
    if golden_dict.get("STATE"):
        timezone = integration_yaml.get("TIMEZONEXE").get(golden_dict.get("STATE").lower())
        if timezone is None:
            return unknown
        return timezone
    if golden_dict.get("SNMP_LOCATION"):
        state, _ = golden_dict.get("SNMP_LOCATION").split(",")
        timezone = integration_yaml.get("TIMEZONEXE").get(state.lower())
        if timezone is None:
            return unknown
        return timezone
    return unknown


def _get_timezoneXR(golden_dict: dict) -> str:
    if golden_dict.get("STATE") is None and golden_dict.get("SNMP_LOCATION") is None:
        return "<UNKNOWN TIMEZONE>"
    if golden_dict.get("STATE"):
        if integration_yaml.get("TIMEZONE").get(golden_dict.get("STATE").lower()) is None:
            return "<UNKNOWN TIMEZONE>"
        return integration_yaml.get("TIMEZONE").get(golden_dict.get("STATE").lower())
    if golden_dict.get("SNMP_LOCATION"):
        state, _ = golden_dict.get("SNMP_LOCATION").split(",")
        if integration_yaml.get("TIMEZONE").get(state.lower()) is None:
            return "<UNKNOWN TIMEZONE>"
        return integration_yaml.get("TIMEZONE").get(state.lower())
    return "<UNKNOWN TIMEZONE>"


def _get_lte_x2(golden_dict: dict) -> str:
    if golden_dict.get("SNMP_LOCATION"):
        state, city, sitename = golden_dict.get("SNMP_LOCATION").split(",")
        city = city.strip().lower()
        if golden_dict.get("REGION"):
            x2_city_code = integration_yaml.get("X2_CITY_CODE").get(golden_dict.get("REGION")).get(city)
            if x2_city_code is None:
                x2_city_code = "<UNKOWN X2 CITY CODE>"
            return "65000:1002{}{}".format(golden_dict.get("REGION"), x2_city_code)
    return "65000:1002R<UNKOWN X2 CITY CODE>"


def _get_bluedomain(golden_dict: dict) -> bool:
    blue_domain_network = ipaddress.ip_network(integration_yaml.get("BLUE_DOMAIN_MGMT_SUBNET"))
    if ipaddress.ip_interface(golden_dict.get("AGG1_LOOPBACK_MANAGEMENT")) in blue_domain_network or ipaddress.ip_interface(golden_dict.get("AGG2_LOOPBACK_MANAGEMENT")) in blue_domain_network:
        return True
    return False


def _get_reddomain(golden_dict: dict) -> bool:
    red_domain_network = ipaddress.ip_network(integration_yaml.get("RED_DOMAIN_MGMT_SUBNET"))
    if ipaddress.ip_interface(golden_dict.get("AGG1_LOOPBACK_MANAGEMENT")) in red_domain_network or ipaddress.ip_interface(golden_dict.get("AGG2_LOOPBACK_MANAGEMENT")) in red_domain_network:
        return True
    return False


def dict_to_text(in_dict: dict) -> str:
    text = ""
    for k, v in in_dict.items():
        text += "{}:{}\n".format(k, v)

    return text


def text_to_dict(in_text: str) -> dict:
    return_dict = dict()
    for line in in_text.splitlines():
        try:
            k, v = line.split(":")
        except:
            pass
        return_dict[k.strip()] = v.lstrip()

    return return_dict


def save_settings(settings: dict) -> None:
    settings_path = Path("settings.json")
    with settings_path.open("w", encoding="utf-8") as file:
        json.dump(settings, file)


def golden_with_secrets(golden_text: str, vars: dict) -> str:
    for k, v in vars.items():
        if not isinstance(v, (str,)):
            continue
        key = "<{}>".format(k)
        golden_text = golden_text.replace(key, v)

    return golden_text