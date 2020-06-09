#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Unai Irigoyen (@unai-i)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ovh_vps_info
author: Unai Irigoyen (@unai-i)
short_description: Get information about a VPS in OVH infrastructure
description:
    - Get information about a VPS in OVH infrastructure.
requirements: [ "ovh" ]
options:
    service_name:
        required: true
        type: str
        description:
            - Name of the service, get it with U(https://api.ovh.com/console/#/vps#GET)
    endpoint:
        type: str
        description:
            - The endpoint to use (for instance ovh-eu)
    application_key:
        type: str
        description:
            - The applicationKey to use
    application_secret:
        type: str
        description:
            - The application secret to use
    consumer_key:
        type: str
        description:
            - The consumer key to use
'''

EXAMPLES = '''
- name: Basic usage, using auth from /etc/ovh.conf
  ovh_vps_info:
    service_name: vps123456.ovh.net

- name: Usage providing auth in playbook
  ovh_vps_info:
    service_name: vps123456.ovh.net
    endpoint: ovh-eu
    application_key: yourkey
    application_secret: yoursecret
    consumer_key: yourconsumerkey
'''

RETURN = '''
vps_info: Information about the vps (type: dict)
service_info: Information about the service (type: dict)
'''

import os
import sys
import traceback

try:
    import ovh
    import ovh.exceptions
    from ovh.exceptions import APIError
    HAS_OVH = True
except ImportError:
    HAS_OVH = False
    OVH_IMPORT_ERROR = traceback.format_exc()

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            service_name=dict(required=True),
            endpoint=dict(required=False),
            application_key=dict(required=False, no_log=True),
            application_secret=dict(required=False, no_log=True),
            consumer_key=dict(required=False, no_log=True),
        ),
        supports_check_mode=True
    )

    # Get parameters
    service_name = module.params.get('service_name')
    endpoint = module.params.get('endpoint')
    application_key = module.params.get('application_key')
    application_secret = module.params.get('application_secret')
    consumer_key = module.params.get('consumer_key')
    vps_info = None

    if not HAS_OVH:
        module.fail_json(msg='python-ovh is required to run this module, see https://github.com/ovh/python-ovh')

    # Connect to OVH API
    client = ovh.Client(
        endpoint=endpoint,
        application_key=application_key,
        application_secret=application_secret,
        consumer_key=consumer_key
    )

    # Check that the service exists
    try:
        vps_info = client.get('/vps/{0}'.format(service_name))
    except ovh.exceptions.ResourceNotFoundError:
        module.fail_json(msg='service {0} does not exist'.format(service_name))

    try:
        service_info = client.get('/vps/{0}/serviceInfos'.format(service_name))
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))

    # Is monthlyBilling already enabled or pending ?
    module.exit_json(changed=False, vps_info=vps_info, service_info=service_info)

    # We should never reach here
    module.fail_json(msg='Internal ovh_vps_info module error')


if __name__ == "__main__":
    main()
