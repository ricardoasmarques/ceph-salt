# -*- encoding: utf-8 -*-
import json
import time


def wait_for_admin_host(name, timeout=1800):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    starttime = time.time()
    timelimit = starttime + timeout
    configured_admin_host = None
    while not configured_admin_host:
        is_timedout = time.time() > timelimit
        if is_timedout:
            ret['comment'] = 'Timeout value reached.'
            return ret
        time.sleep(15)
        admin_hosts = __pillar__['ceph-salt']['minions']['admin']
        for admin_host in admin_hosts:
            failed = __salt__['ceph_salt.get_remote_grain'](admin_host, 'ceph-salt:execution:failed')
            if failed:
                ret['comment'] = 'One or more admin minions failed.'
                return ret
            provisioned = __salt__['ceph_salt.get_remote_grain'](admin_host,
                                                                'ceph-salt:execution:provisioned')
            if provisioned:
                ssh_user = __pillar__['ceph-salt']['ssh']['user']
                sudo = 'sudo ' if ssh_user != 'root' else ''
                status_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                                     "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                                     "'if [[ -f /etc/ceph/ceph.conf "
                                                     "&& -f /etc/ceph/ceph.client.admin.keyring ]]; "
                                                     "then timeout 60 {}ceph orch status --format=json; "
                                                     "else (exit 1); fi'".format(
                                                         ssh_user,
                                                         admin_host,
                                                         sudo))
                if status_ret['retcode'] == 0:
                    status = json.loads(status_ret['stdout'])
                    if status.get('available'):
                        configured_admin_host = admin_host
                        break

    __salt__['grains.set']('ceph-salt:execution:admin_host', configured_admin_host)
    ret['result'] = True
    return ret


def add_host(name, host):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    cmd_ret = __salt__['cmd.run_all']("ssh -o StrictHostKeyChecking=no "
                                      "-i /tmp/ceph-salt-ssh-id_rsa {}@{} "
                                      "'{}ceph orch host add {}'".format(ssh_user, admin_host,
                                                                       sudo, host))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    return ret


def copy_ceph_conf_and_keyring(name):
    ret = {'name': name, 'changes': {}, 'comment': '', 'result': False}
    admin_host = __salt__['grains.get']('ceph-salt:execution:admin_host')
    ssh_user = __pillar__['ceph-salt']['ssh']['user']
    sudo = 'sudo ' if ssh_user != 'root' else ''
    cmd_ret = __salt__['cmd.run_all']("{0}rsync --rsync-path='{0}rsync' "
                                      "-e 'ssh -o StrictHostKeyChecking=no "
                                      "-i /tmp/ceph-salt-ssh-id_rsa' "
                                      "{1}@{2}:/etc/ceph/{{ceph.conf,ceph.client.admin.keyring}} "
                                      "/etc/ceph/".format(sudo, ssh_user, admin_host))
    if cmd_ret['retcode'] == 0:
        ret['result'] = True
    return ret
