"""Common utils for yi-hack cam."""

from datetime import timedelta
import logging

import requests
from requests.auth import HTTPBasicAuth

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    END_OF_POWER_OFF,
    END_OF_POWER_ON,
    HTTP_TIMEOUT,
    PRIVACY,
)

_LOGGER = logging.getLogger(__name__)


def get_status(config):
    """Get system status from camera."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    user = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    error = False

    auth = None
    if user or password:
        auth = HTTPBasicAuth(user, password)

    response = None
    try:
        response = requests.get("http://" + host + ":" + str(port) + "/cgi-bin/status.json", timeout=HTTP_TIMEOUT, auth=auth)
        if response.status_code >= 300:
            _LOGGER.error("Failed to get status from device %s", host)
            error = True
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Failed to get status from device %s: error %s", host, e)
        error = True

    if error:
        response = None
        return None

    return response.json()

def get_system_conf(config):
    """Get system configuration from camera."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    user = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    error = False

    auth = None
    if user or password:
        auth = HTTPBasicAuth(user, password)

    response = None
    try:
        response = requests.get("http://" + host + ":" + str(port) + "/cgi-bin/get_configs.sh?conf=system", timeout=HTTP_TIMEOUT, auth=auth)
        if response.status_code >= 300:
            _LOGGER.error("Failed to get system configuration from device %s", host)
            error = True
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Failed to get system configuration from device %s: error %s", host, e)
        error = True

    if error:
        response = None
        return None

    return response.json()

def get_mqtt_conf(config):
    """Get mqtt configuration from camera."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    user = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    error = False

    auth = None
    if user or password:
        auth = HTTPBasicAuth(user, password)

    response = None
    try:
        response = requests.get("http://" + host + ":" + str(port) + "/cgi-bin/get_configs.sh?conf=mqtt", timeout=HTTP_TIMEOUT, auth=auth)
        if response.status_code >= 300:
            _LOGGER.error("Failed to get mqtt configuration from device %s", host)
            error = True
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Failed to get mqtt configuration from device %s: error %s", host, e)
        error = True

    if error:
        response = None
        return None

    return response.json()

def get_privacy(hass, device_name, config=None):
    """Get status of privacy from device."""
    # Privacy is true when the cam is off
    if power_off_in_progress(hass, device_name):
        return True
    # Privacy is false when the cam is on
    if power_on_in_progress(hass, device_name):
        return False

    if config is None:
        return hass.data[DOMAIN][device_name][PRIVACY]

    host = config[CONF_HOST]
    port = config[CONF_PORT]
    user = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    error = False

    auth = None
    if user or password:
        auth = HTTPBasicAuth(user, password)

    response = None
    try:
        response = requests.get("http://" + host + ":" + str(port) + "/cgi-bin/privacy.sh?value=status", timeout=HTTP_TIMEOUT, auth=auth)
        if response.status_code >= 300:
            _LOGGER.error("Failed to get status of device %s", host)
            error = True
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Error getting status of device %s: error %s", host, e)
        error = True

    if error:
        return None

    if response is not None:
        try:
            privacy_dict: dict = response.json()
            privacy: str = privacy_dict.get("status")
        except KeyError:
            _LOGGER.error("Failed to get status of device %s: error unknown", host)
            error = True
    else:
        _LOGGER.error("Failed to get status on device %s: error unknown", host)
        error = True

    if error:
        return None


    if privacy != "on":
        # Update local var
        hass.data[DOMAIN][device_name][PRIVACY] = False
        return False

    # Update local var
    hass.data[DOMAIN][device_name][PRIVACY] = True

    return True

def set_privacy(hass, device_name, newstatus, config=None):
    """Set status of privacy to device. Return true if web service completes successfully."""
    if config is None:
        hass.data[DOMAIN][device_name][PRIVACY] = newstatus
        return

    host = config[CONF_HOST]
    port = config[CONF_PORT]
    user = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    error = False
    if newstatus:
        newstatus_string = "on"
    else:
        newstatus_string = "off"

    auth = None
    if user or password:
        auth = HTTPBasicAuth(user, password)

    response = None
    try:
        response = requests.get("http://" + host + ":" + str(port) + "/cgi-bin/privacy.sh?value=" + newstatus_string, timeout=HTTP_TIMEOUT, auth=auth)
        if response.status_code >= 300:
            _LOGGER.error("Failed to switch on device %s", host)
            error = True
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Failed to switch on device %s: error %s", host, e)
        error = True

    if error:
        return None

    if response is not None:
        try:
            if response.json()["status"] != "on" and response.json()["status"] != "off":
                _LOGGER.error("Failed to switch on device %s", host)
                error = True
        except KeyError:
            _LOGGER.error("Failed to switch on device %s: error unknown", host)
            error = True
    else:
        _LOGGER.error("Failed to switch on device %s: error unknown", host)
        error = True

    if error:
        return False

    hass.data[DOMAIN][device_name][PRIVACY] = newstatus

    return True

def set_power_off_in_progress(hass, device_name):
    device_conf = get_device_conf(hass, device_name)
    device_conf[END_OF_POWER_OFF] = dt_util.utcnow() + timedelta(seconds=5)

def power_off_in_progress(hass, device_name):
    device_conf = get_device_conf(hass, device_name)
    return (
        device_conf[END_OF_POWER_OFF] is not None
        and device_conf[END_OF_POWER_OFF] > dt_util.utcnow()
    )

def set_power_on_in_progress(hass, device_name):
    device_conf = get_device_conf(hass, device_name)
    device_conf[END_OF_POWER_ON] = dt_util.utcnow() + timedelta(seconds=5)

def power_on_in_progress(hass, device_name):
    device_conf = get_device_conf(hass, device_name)
    return (
        device_conf[END_OF_POWER_ON] is not None
        and device_conf[END_OF_POWER_ON] > dt_util.utcnow()
    )

def get_device_conf(hass, device_name, param=None):
    if param is None:
        return hass.data[DOMAIN][device_name]
    return hass.data[DOMAIN][device_name][param]
