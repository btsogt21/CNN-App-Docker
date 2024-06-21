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

CMD ["npm", "run", "dev"]