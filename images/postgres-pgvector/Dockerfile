FROM ghcr.io/cloudnative-pg/postgresql:15.12-13

# To install any package we need to be root
USER root

# We update the package list, install our package
# and clean up any cache from the package manager
RUN set -xe; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		postgresql-contrib \
		postgresql-15-pgvector ; \
	rm -fr /tmp/* ; \
	rm -rf /var/lib/apt/lists/*;

# Change to the uid of postgres (26)
USER 26
