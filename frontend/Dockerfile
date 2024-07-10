FROM node:16-alpine as build

WORKDIR /frontend

COPY package*.json ./

RUN npm install

COPY . .

# RUN npm run build

# FROM nginx:alpine

# COPY --from=build /frontend/dist /usr/share/nginx/html

EXPOSE 5173

# CMD ["nginx", "-g", "daemon off;"]

CMD sh -c 'until nc -z backend 5000; do echo "Waiting for backend to be ready..."; sleep 1; done; npm run dev'