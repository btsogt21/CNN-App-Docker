#!/bin/bash
# the above is the shebang line, which tells the shell what program to use to interpret the script.
# In this case, it's /bin/bash.

# # Waits for logstash to be up on container port 5000. Times out after 60 seconds.
# /wait-for-it.sh logstash:5000 --timeout=60 --strict -- echo "Logstash is up"

# Run the command passed to the docker container. '$@' ensures that the CMD from the Dockerfile
# is passed correctly.

#change ownership of /frontend directory
# chown -R node:node /frontend

exec /usr/bin/tini -- "$@"