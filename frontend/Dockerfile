# Pulling the node image from the Docker Hub
FROM node:16-alpine as build


# Install shadow package to get access to usermod
RUN apk add --no-cache shadow

# Creating a new user called adduser with UID 1002, and adding it to the group appgroup which has
# GID 1002. The user and group match the UID and GID inherited from the host machine when we mount
# the ./frontend volume from our host machine and map it to the /frontend directory in the container.
# RUN addgroup -S appgroup && adduser -S appuser -G appgroup -u 1002

# Alternatively, we can edit the 'node' user that comes with the node image to have the same UID and
# GID as the volume mounted from the host machine.
RUN usermod -u 1002 node && groupmod -g 1002 node

# USER node

WORKDIR /frontend

COPY package*.json ./

RUN npm install

COPY . .

# RUN npm run build

# FROM nginx:alpine

# COPY --from=build /frontend/dist /usr/share/nginx/html

# COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# RUN chmod +x /usr/local/bin/entrypoint.sh

# RUN chown -R appuser:appgroup /frontend

RUN chown -R node:node /frontend

# USER appuser

# USER node

EXPOSE 5173

# CMD ["nginx", "-g", "daemon off;"]

# ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD sh -c 'until nc -z backend 5000; do echo "Waiting for backend to be ready..."; sleep 1; done; npm run dev'


# chown -R node:node /frontend &&  