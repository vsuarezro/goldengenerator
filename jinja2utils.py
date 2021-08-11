import ipaddress
from pathlib import Path

import yaml

integrationdata_yaml = "integration.yaml"
integrationyaml_path = Path("integration.yaml")
integration_yaml = yaml.safe_load(integrationyaml_path.open("r", encoding="utf-8"))

def do_prefix(s: str, prefix: str) -> str:
    newline = "\n"
    s += newline

    lines = s.splitlines()
    rv = lines.pop(0)
    if lines:
        rv += newline + newline.join(
            prefix + line if line else line for line in lines
         )
    rv = prefix + rv
    return rv

def do_rstrip(s: str, remove_str: str) -> str:
    newline = "\n"
    s += newline
    lines = s.splitlines()
    rv = lines.pop(0)
    rv = rv.rstrip(remove_str)
    if lines:
        rv += newline + newline.join(
            line.rstrip(remove_str) if line else line for line in lines
         )

    return rv


def do_metric(interface: str) -> int:
    """
    jinja2 filter, uses the type of the interface to return an ISIS metric value.
    reference bandwitdh is 1Tbps
    """
    if "Ten" in interface:
        return 100
    if "Hun" in interface:
        return 10
    return 1000

def do_ip_to_sid(ip_string: str) -> int:
    """
    jinja2 filter, receives an IPv4 string and returns its corresponding SR SID Index
    IPv4 to SID funcion is octect3 * 256 + octect4
    """

    try:
        octet3 = int(ip_string.split(".")[2])
        octet4 = int(ip_string.split(".")[3])
    except ValueError:
        logger.error(
            "SID: IP address '{}' is invalid and cannot get the SID value.".format(
                ip_string
            )
        )
        return "<SID>"
    except IndexError:
        logger.error(
            "SID: IP address '{}' is invalid and cannot get the SID value.".format(
                ip_string
            )
        )
        return "<SID>"

    if octet3 > 255 or octet4 > 255 or octet3 < 0 or octet4 < 0:
        logger.error(
            "SID: IP address '{}' is invalid and cannot get the SID value.".format(
                ip_string
            )
        )
        return "<SID>"
    elif octet3 > 62:
        logger.warning(
            "SID: Third octet in '{}' mustn't be higher than 62 or risk of SID collision exist".format(
                ip_string
            )
        )
        pass
    elif octet3 == 62 and octet4 > 127:
        logger.warning(
            "SID: When third octet is 62 in '{}', fourth octet mustn't be higher than 127 or risk of SID collision exist".format(
                ip_string
            )
        )
        pass

    sid = octet3 * 256 + octet4
    return sid

def do_module(interface: str) -> str:
    """
    jinja2 filter, receives an interface name and returns the value of the module
    """
    interface_tokens = interface.split("/")
    return interface_tokens[1]

def template_test_is_ip_blue(ip_string: str) -> bool:
    """
    jinja2 filter,
    receives an IPv4 address and check if it belongs to a subnet defined in integration.yaml
    return true if IP belongs to that subnet, false otherwise
    """
    if ipaddress.ip_address(ip_string) in ipaddress.ip_network(integration_yaml["BLUE_DOMAIN_MGMT_SUBNET"]):
        return True
    return False