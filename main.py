import json
import os
import requests
import time

from kubernetes import client, config

def error(msg, resp):
    if resp.status_code not in (200, 201, 202):
        print(f'{msg} {resp.status_code} {resp.content.decode("utf-8")}')

def get_controlplane_nodes():
    cpnodes = []

    nodes = v1.list_node()

    for n in nodes.items:
        if 'node-role.kubernetes.io/control-plane' in n.metadata.labels.keys():
            cpnodes.append(n)

    cpnodes.sort(key=lambda x: x.metadata.name)

    return cpnodes

def get_ip_addresses(cpnodes):
    addresses = []

    for n in cpnodes:
        for a in n.status.addresses:
            if a.type == 'InternalIP':
                addresses.append(a.address)

    addresses.sort()

    return addresses

def remove_redundant_nodes(cpnodes, addresses):
    resp=requests.get(f"{base}/version", auth=("admin", passwd))
    error('error getting version:', resp)

    version=int(resp.content.decode('utf-8'))

    resp = requests.get(f"{base}/backends/{cluster}/servers", auth=("admin", passwd))

    if resp.status_code == 200:
        servers = json.loads(resp.content)
        while len(servers) > len(cpnodes):
            srv = servers[-1]['name']
            print(f'deleting server {srv}')
            resp = requests.delete(f"{base}/backends/{cluster}/servers/{srv}?version={version}", headers={"Content-Type": "application/json"}, auth=("admin", passwd))

            error(f'error deleting server {srv}:', resp)

            servers.pop()

passwd = os.getenv("DATAPLANE_PASSWORD")
apihost = os.getenv("DATAPLANE_API_HOST")
cluster = os.getenv("DATAPLANE_CLUSTER")
home = os.getenv("HOME")

base = f"{apihost}/v3/services/haproxy/configuration"

print("[***] starting dataplaneapi backend server updater")
print(f"[***] host {apihost} cluster {cluster}")

try:
    config.load_incluster_config()    
except:
    config.load_kube_config(config_file=f"{home}/.kube/config")

while True:
    v1 = client.CoreV1Api()

    cpnodes = get_controlplane_nodes()

    for n in cpnodes:
        print(f'controlplane: {n.metadata.name}')

    addresses = get_ip_addresses(cpnodes)

    remove_redundant_nodes(cpnodes, addresses)

    try:
        for i, address_in_k8s in enumerate(addresses):
            resp = requests.get(f"{base}/backends/{cluster}/servers/controlplane-{i+1}", auth=("admin", passwd))

            add = False

            if resp.status_code == 200:
                address_in_haproxy = resp.json()["address"]

                if address_in_k8s == address_in_haproxy:
                    continue
            else:
                add = True
                print(f'controlplane-{i+1} not found in HAProxy, adding it')

            address_in_haproxy = address_in_k8s

            resp=requests.get(f"{base}/version", auth=("admin", passwd))
            if resp.status_code != 200:
                error('error getting version: ', resp)
                continue
            version=int(resp.content.decode('utf-8'))

            if not add:
                method = "PUT"
                url = f"{base}/backends/{cluster}/servers/controlplane-{i+1}?version={version}"
            else:
                method = "POST"
                url = f"{base}/backends/{cluster}/servers?version={version}"

            body = { "name": f"controlplane-{i+1}", "address": address_in_k8s, "port": 443, "check": "enabled", "ssl": "enabled", "fall": 3, "rise": 2, "verify": "none" }    
            
            resp = requests.request(method, url, json=body, headers={"Content-Type": "application/json"}, auth=("admin", passwd))
            if resp.status_code == 200 or resp.status_code == 201:
                print(f'added controlplane-{i+1} server {address_in_k8s}')
            else:
                print(f'error adding controlplane-{i+1} to {address_in_k8s}: {resp.status_code} {resp.content.decode("utf-8")}')

        time.sleep(900)
    except requests.RequestException as e:
        print(f'error requests: {e}')

