#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import json
import glob
import os
import subprocess
from subprocess import CalledProcessError
import ConfigParser
import dpath

from rados import Rados
from rados import Error as RadosError
import rbd

CEPH_CLUSTER_CONFIGS = os.getenv('CEPH_CLUSTER_CONFIGS', '/etc/ceph/clusters/')
CEPH_KEYRING_SECRET = os.getenv('CEPH_KEYRING_SECRET', '/etc/ceph/secret/ceph-secret.yml')
CEPH_MONITOR_URL = os.getenv('CEPH_MONITOR_URL', 'ceph-mon-%(cluster_name)s.service.os:6789')


def get_ceph_clusters():
    """
    Grab dictionary of ceph clusters from the config directory specified in
    config.json
    """

    ceph_clusters = dict()
    for config_file in glob.glob(CEPH_CLUSTER_CONFIGS + '*.conf'):
        cluster_name = os.path.basename(os.path.splitext(config_file)[0])
        ceph_clusters[cluster_name] = dict()
        ceph_clusters[cluster_name]['conffile'] = CEPH_CLUSTER_CONFIGS + cluster_name + '.conf'
        ceph_clusters[cluster_name]['conf'] = dict(keyring = CEPH_CLUSTER_CONFIGS + cluster_name + '.keyring')

    return ceph_clusters


def parse_ceph_config(conffile):
    """
    Parses a ceph config file and returns a dictionary
    """

    ceph_config = dict()
    config = ConfigParser.SafeConfigParser()
    config.read(conffile)

    for section in config.sections():
        ceph_config[section] = dict()
        for option in config.items(section):
            ceph_config[section][option[0]] = option[1]

    for default in config.defaults():
        ceph_config[default[0]] = default[1]

    return ceph_config

def get_ceph_config_monitors(config_file):
    """
    Takes a ceph config file extracts the cluster name and combines it with a url
    """

    cluster_name = os.path.basename(os.path.splitext(config_file)[0])
    monitors = [CEPH_MONITOR_URL % locals()]
    return monitors

def get_cluster_rbd_images(cluster, ceph_pool = 'rbd'):
    rbd_images = []
    cluster_config = get_ceph_clusters()[cluster]
    ceph_config = parse_ceph_config(cluster_config['conffile'])
    ceph_monitors = get_ceph_config_monitors(cluster_config['conffile'])

    with Rados(**cluster_config) as cluster:
        with cluster.open_ioctx(ceph_pool) as ioctx:
            rbd_inst = rbd.RBD()
            for rbd_image_name in rbd_inst.list(ioctx):
                with rbd.Image(ioctx, rbd_image_name) as rbd_image:
                    rbd_images.append({
                        'name': rbd_image_name,
                        'size': (rbd_image.size() / 1024**3),
                        'monitors': ceph_monitors,
                        'project':'',
                        'pvc': '',
                        'pv':''
                    })

    return rbd_images

def get_cluster_ceph_openshift_volumes(cluster, ceph_pool = 'rbd'):
    """
    Matches ceph volumes with openshift persistent volumes
    """

    cluster_rbd_images = get_cluster_rbd_images(cluster, ceph_pool)
    openshift_pvs = get_openshift_pvs()

    for rbd_image in cluster_rbd_images:
        for openshift_pv in openshift_pvs:
            if (openshift_pv['spec']['rbd']['image'] == rbd_image['name']):
                rbd_image['pv'] = openshift_pv['metadata']['name']
                if 'claimRef' in openshift_pv['spec']:
                    rbd_image['pvc'] = openshift_pv['spec']['claimRef']['name']
                    rbd_image['project'] = openshift_pv['spec']['claimRef']['namespace']

    return cluster_rbd_images

def get_openshift_pvs():
    """
    Grab a list of openshift projects
    """

    openshift_pvs = json.loads(subprocess.check_output(["oc", "get", "pv", "-o", "json"]))['items']

    return openshift_pvs


def get_openshift_projects():
    """
    Returns a list of openshift projects
    """

    openshift_projects = json.loads(subprocess.check_output(["oc", "get", "projects", "-o" "json"]))['items']

    return [ project['metadata']['name'] for project in openshift_projects ]


def create_rbd_image(cluster_name, image_name, image_size, ceph_pool = 'rbd'):
    """
    Create a ceph rbd image in a cluster
    """

    ceph_clusters = get_ceph_clusters()

    with Rados(**ceph_clusters[cluster_name]) as cluster:
        with cluster.open_ioctx(ceph_pool) as ioctx:
            rbd_inst = rbd.RBD()
            size = image_size * (1024**3)
            rbd_inst.create(ioctx, image_name, size, None, False, 1)

def add_ceph_secret(project):
    """
    Adds ceph secret keyring to openshift project
    """

    try:
        subprocess.check_output(["oc", "create", "--namespace", str(project), "-f", CEPH_KEYRING_SECRET])
    except CalledProcessError as error:
        if not error.output.find('already exists'):
            raise

def create_openshift_pvc(image_name, image_size, monitors, project, ceph_pool='rbd'):
    """
    Creates an openshift PV and PVC in a list manifest for the ceph storage
    """

    add_ceph_secret(project)

    TEMP_MANIFEST_FILE = "/tmp/ceph-openshift-pv.json"

    manifest = {
        'apiVersion': 'v1',
        'kind': 'List',
        'metadata': {},
        'items': [
            {
                'apiVersion': 'v1',
                'kind': 'PersistentVolume',
                'metadata': {
                    'name': str(image_name),
                },
                'spec': {
                    'accessModes': ['ReadWriteOnce'],
                    'capacity': {
                        'storage': str(image_size) + 'Gi'
                    },
                    'persistentVolumeReclaimPolicy': 'Recycle',
                    'rbd': {
                        'fsType': 'xfs',
                        'image': str(image_name),
                        'monitors': monitors,
                        'pool': str(ceph_pool),
                        'readOnly': False,
                        'secretRef': {
                            'name': 'ceph-admin-keyring-secret'
                        },
                        'user': 'admin'
                    }
                }
            },{
                'apiVersion': 'v1',
                'kind': 'PersistentVolumeClaim',
                'metadata': {
                    'name': str(image_name),
                },
                'spec': {
                    'volumeName' : str(image_name),
                    'accessModes': ['ReadWriteOnce'],
                    'resources': {
                        'requests': {
                            'storage': str(image_size) + 'Gi'
                        }
                    }
                }
            }
        ]
    }

    with open(TEMP_MANIFEST_FILE, "w") as handle:
        handle.write(json.dumps(manifest, sort_keys=True, indent=4))

    return subprocess.check_output(["oc", "create","--namespace", str(project), "-f", TEMP_MANIFEST_FILE])


def create_ceph_openshift_volume(cluster_name, image_name, image_size, project):
    """
    Takes validated form object and creates a ceph image and assigns it to a
    project in openshift_pv
    """
    print("creating cluster_name:%(cluster_name)s, image_name:%(image_name)s, image_size:%(image_size)s, project: %(project)s" % locals())

    ceph_clusters = get_ceph_clusters()
    ceph_config = parse_ceph_config(ceph_clusters[cluster_name]['conffile'])
    ceph_monitors = get_ceph_config_monitors(ceph_clusters[cluster_name]['conffile'])

    create_rbd_image(cluster_name, image_name, image_size)
    create_openshift_pvc(image_name, image_size, ceph_monitors, project)
