# Update IP address of HAProxy backend servers

* Install haproxy
* Configure backends
* Install dataplaneapi
* Translate curl to requests python

## Backend configuration

Make sure to name the servers controlplane-1 to x

backend k8s-cluster
  mode http
  balance roundrobin
  http-request set-header Host host.example.com
  server controlplane-1 192.168.130.28:443 check ssl fall 3 rise 2 verify none
  server controlplane-2 192.168.130.30:443 check ssl fall 3 rise 2 verify none
  server controlplane-3 192.168.130.31:443 check ssl fall 3 rise 2 verify none

## Get all servers

```curl -sX GET --user admin:pw "http://localhost:5555/v3/services/haproxy/configuration/backends/k8s-cluster/servers"```

## Get single server

```curl -sX GET   --user admin:pw   "http://localhost:5555/v3/services/haproxy/configuration/backends/k8s-cluster/servers/controlplane-1"
{
  "check": "enabled",
  "fall": 3,
  "rise": 2,
  "ssl": "enabled",
  "verify": "none",
  "address": "192.168.130.82",
  "name": "controlplane-1",
  "port": 443
}
```

## Update the IP address

Get current version first
```
CFGVER=$(curl -s -u admin:pw http://localhost:5555/v3/services/haproxy/configuration/version)

curl -X PUT --user admin:pw "http://localhost:5555/v3/services/haproxy/configuration/backends/services-cluster/servers/controlplane-1?version=$CFGVER" 
     -H "Content-Type: application/json" 
     -d '{ "name": "controlplane-1", "address": "10.10.10.10" }'
```

output: {"address":"10.10.10.10","name":"controlplane-1"}
