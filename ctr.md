```
k3s ctr image pull docker.io/library/nginx:latest
k3s ctr image pull docker.io/rancher/k3s:latest
k3s ctr run docker.io/library/nginx:latest image-name
k3s ctr run -t --rm docker.io/rancher/k3s:latest my-k3s /bin/bsh
```
