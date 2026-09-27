FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html
USER 101:101
EXPOSE 80
# Bypass image entrypoint scripts; configuration is supplied at build time.
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
