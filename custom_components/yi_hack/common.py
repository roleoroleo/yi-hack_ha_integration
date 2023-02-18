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
    HTTP_TIMEOUT,
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
