FROM openroad/orfs:latest

# Install noVNC stack + supervisor
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    websockify \
    novnc \
    supervisor \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Copy supervisor config and startup script
COPY supervisord.conf /etc/supervisor/conf.d/vnc.conf
COPY start_session.sh /usr/local/bin/start_session.sh
RUN chmod +x /usr/local/bin/start_session.sh

# websockify/noVNC port
EXPOSE 6080

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
