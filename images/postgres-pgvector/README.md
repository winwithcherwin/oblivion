# cnpg
https://cloudnative-pg.io/blog/creating-container-images/

# To do vector stuff with postgres we need to build a custom image.
# Here's the cluster store where I got the image reference from
https://raw.githubusercontent.com/cloudnative-pg/postgres-containers/main/Debian/ClusterImageCatalog-bookworm.yaml 

```
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: db-staging
  namespace: oblivion
spec:
  instances: 1

  bootstrap:
    initdb:
      postInitSQL:
        - create extension vector

  storage:
    size: 5Gi
```

docker build -t winwithcherwin/cnpg:15.12-13:latest
