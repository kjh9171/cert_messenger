FROM node:18-alpine
WORKDIR /usr/src/app
COPY package.json ./
RUN npm install --production
COPY src ./src
COPY migrations ./migrations
EXPOSE 3100
CMD sh -c "node src/migrate.js 2>/dev/null || true && node src/server.js"
