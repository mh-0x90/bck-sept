FROM axllent/mailpit:v1.30.7 AS mailpit

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       nginx postgresql curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=mailpit /mailpit /usr/local/bin/mailpit

COPY runtime_host/requirements /tmp/app-requirements
RUN python -m venv /opt/venvs/companyemail \
    && /opt/venvs/companyemail/bin/pip install --no-cache-dir -r /tmp/app-requirements/companyemail.txt \
    && python -m venv /opt/venvs/minglefeed \
    && /opt/venvs/minglefeed/bin/pip install --no-cache-dir -r /tmp/app-requirements/minglefeed.txt \
    && python -m venv /opt/venvs/parcel-room \
    && /opt/venvs/parcel-room/bin/pip install --no-cache-dir -r /tmp/app-requirements/parcel-room.txt \
    && python -m venv /opt/venvs/parcelpad \
    && /opt/venvs/parcelpad/bin/pip install --no-cache-dir -r /tmp/app-requirements/parcelpad.txt \
    && python -m venv /opt/venvs/pulseboard \
    && /opt/venvs/pulseboard/bin/pip install --no-cache-dir -r /tmp/app-requirements/pulseboard.txt \
    && python -m venv /opt/venvs/quickcart \
    && /opt/venvs/quickcart/bin/pip install --no-cache-dir -r /tmp/app-requirements/quickcart.txt \
    && python -m venv /opt/venvs/shellnest \
    && python -m venv /opt/venvs/documentsmng \
    && /opt/venvs/documentsmng/bin/pip install --no-cache-dir -r /tmp/app-requirements/documentsmng.txt \
    && rm -rf /tmp/app-requirements

RUN for u in dashboard companyemail mailbox minglefeed parcelroom parcelpad pulseboard quickcart shellnest documentsmng; do \
      groupadd --system "$u"; \
      useradd --system --gid "$u" --home-dir /nonexistent --shell /usr/sbin/nologin "$u"; \
    done \
    && mkdir -p /opt/apps /opt/host /tmp/runtime /run/parcelpad

COPY services/companyemail/code/app_code /opt/apps/companyemail/app_code
COPY services/mailbox/code/app_code /opt/apps/mailbox/app_code
COPY services/minglefeed/code/app_code /opt/apps/minglefeed/app_code
COPY services/parcel-room/code/app_code /opt/apps/parcel-room/app_code
COPY services/parcelpad/code/app_code /opt/apps/parcelpad/app_code
COPY services/pulseboard/code/app_code /opt/apps/pulseboard/app_code
COPY services/quickcart/code/app_code /opt/apps/quickcart/app_code
COPY services/shellnest/code/app_code /opt/apps/shellnest/app_code
COPY services/documentsmng /opt/apps/documentsmng
COPY runtime_host/host /opt/host

RUN chown -R companyemail:companyemail /opt/apps/companyemail \
    && chown -R mailbox:mailbox /opt/apps/mailbox \
    && chown -R minglefeed:minglefeed /opt/apps/minglefeed \
    && chown -R parcelroom:parcelroom /opt/apps/parcel-room \
    && chown -R parcelpad:parcelpad /opt/apps/parcelpad \
    && chown -R pulseboard:pulseboard /opt/apps/pulseboard \
    && chown -R quickcart:quickcart /opt/apps/quickcart \
    && chown -R shellnest:shellnest /opt/apps/shellnest \
    && chown -R documentsmng:documentsmng /opt/apps/documentsmng \
    && chmod 0711 /opt/apps \
    && find /opt/apps -mindepth 1 -maxdepth 1 -type d -exec chmod 0750 {} + \
    && find /opt/apps -mindepth 2 -type d -exec chmod 0750 {} + \
    && find /opt/apps -type f -exec chmod 0640 {} + \
    && chmod 0555 /opt/host/*.py \
    && chmod 0444 /opt/host/nginx-mailbox.conf \
    && mkdir -p \
       /tmp/runtime/dashboard \
       /tmp/runtime/companyemail \
       /tmp/runtime/minglefeed \
       /tmp/runtime/parcel-room \
       /tmp/runtime/parcelpad \
       /tmp/runtime/pulseboard \
       /tmp/runtime/quickcart \
       /tmp/runtime/shellnest/workspace \
       /tmp/runtime/documentsmng \
    && chown -R dashboard:dashboard /tmp/runtime/dashboard \
    && chown -R companyemail:companyemail /tmp/runtime/companyemail \
    && chown -R minglefeed:minglefeed /tmp/runtime/minglefeed \
    && chown -R parcelroom:parcelroom /tmp/runtime/parcel-room \
    && chown -R parcelpad:parcelpad /tmp/runtime/parcelpad \
    && chown -R pulseboard:pulseboard /tmp/runtime/pulseboard \
    && chown -R quickcart:quickcart /tmp/runtime/quickcart \
    && chown -R shellnest:shellnest /tmp/runtime/shellnest \
    && chown -R documentsmng:documentsmng /tmp/runtime/documentsmng \
    && chmod 0755 /run/parcelpad

EXPOSE 8025 8080 8101 8102 8103 8104 8105 8106 8107 8108 8109

HEALTHCHECK --interval=15s --timeout=3s --start-period=25s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()" || exit 1

ENTRYPOINT ["python", "/opt/host/launcher.py"]
