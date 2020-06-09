#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Unai Irigoyen (@unai-i)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ovh_vps_reboot
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
    rescue:
        type: boolean
        description:
            - yes to reboot in rescue mode, no for local boot (default: no)
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
- name: Basic usage, local boot, using auth from /etc/ovh.conf
  ovh_vps_reboot:
    service_name: vps123456.ovh.net

- name: Reboot in rescue mode providing auth in playbook
  ovh_vps_reboot:
    service_name: vps123456.ovh.net
    rescue: yes
    endpoint: ovh-eu
    application_key: yourkey
    application_secret: yoursecret
    consumer_key: yourconsumerkey
'''

RETURN = '''
'''

import os
import sys
import traceback
import time

try:
    import ovh
    import ovh.exceptions
    from ovh.exceptions import APIError
    HAS_OVH = True
except ImportError:
    HAS_OVH = False
    OVH_IMPORT_ERROR = traceback.format_exc()

from ansible.module_utils.basic import AnsibleModule

def wait_for_pending_tasks(client, service_name):
    pending_states = ['waitingAck','paused','blocked','todo','doing']
    pending_tasks = []
    for state in pending_states:
        pending_tasks.extend(
            client.get('/vps/{0}/tasks'.format(service_name),
                state=state,
        ))
    while pending_tasks:
        for task in pending_tasks:
            task_info = client.get('/vps/{0}/tasks/{1}'.format(service_name, task))
            if task_info['state'] not in pending_states:
                pending_tasks.remove(task)
        time.sleep(5)

def main():
    module = AnsibleModule(
        argument_spec=dict(
            service_name=dict(required=True),
            rescue=dict(default=False, type='bool'),
            endpoint=dict(required=False),
            application_key=dict(required=False, no_log=True),
            application_secret=dict(required=False, no_log=True),
            consumer_key=dict(required=False, no_log=True),
        ),
        supports_check_mode=True
    )

    # Get parameters
    service_name = module.params.get('service_name')
    rescue = module.params.get('rescue')
    endpoint = module.params.get('endpoint')
    application_key = module.params.get('application_key')
    application_secret = module.params.get('application_secret')
    consumer_key = module.params.get('consumer_key')
    service = ""
    msg=""

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
        service = client.get('/vps/{0}'.format(service_name))
    except ovh.exceptions.ResourceNotFoundError:
        module.fail_json(msg='service {0} does not exist'.format(service_name))

    target_boot_mode = 'rescue' if rescue else 'local'
    boot_mode = service['netbootMode']

    msg = msg + "Current mode: {0}\nRescue requested: {1}\n".format(boot_mode, rescue)

    change_boot_mode = (boot_mode != target_boot_mode)

    if module.check_mode:
        module.exit_json(changed=True, msg="Dry Run! Would {0}change boot mode{1}.".format(
            '' if change_boot_mode else 'not ',
            ' to {0}'.format(target_boot_mode) if change_boot_mode else ''))

    # Is set boot mode if not already right
    if change_boot_mode :
        try:
            client.put('/vps/{0}'.format(service_name), 
                netbootMode=target_boot_mode
            )
            wait_for_pending_tasks(client, service_name)
            module.exit_json(changed=True, msg=msg)
        except APIError as apiError:
            msg = msg + "Failed to call OVH API: {0}".format(apiError)
            module.fail_json(changed=False, msg=msg)

    # Reboot
    try:
        client.post('/vps/{0}/reboot'.format(service_name))
        wait_for_pending_tasks(client, service_name)
        module.exit_json(changed=True, msg=msg)
    except APIError as apiError:
        msg = msg + "Failed to call OVH API: {0}".format(apiError)
        module.fail_json(changed=False, msg=msg)

    # We should never reach here
    module.fail_json(msg='Internal ovh_vps_reboot module error')


if __name__ == "__main__":
    main()
