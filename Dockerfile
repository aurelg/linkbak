FROM python:3.7-alpine3.8

RUN \
  apk --no-cache update \
  && apk --no-cache upgrade \
RUN apk add gcc
RUN apk add g++
RUN apk add libxslt-dev
RUN apk add chromium
RUN rm -rf /var/cache/apk/* /tmp/*

ENV LINKBAK /linkbak
WORKDIR $LINKBAK
COPY Pipfile Pipfile.lock $LINKBAK/
RUN pip install pipenv \
  && pipenv install

COPY . $LINKBAK
ENV PYTHONPATH $LINKBAK/src


ENV DATADIR $LINKBAK/output
RUN mkdir $DATADIR

# TODO Dirty hack for now
RUN ln -s /usr/bin/chromium-browser /usr/bin/chromium
# FIXME for some reason, chromium segfault and PDFs are not dumped :-/
ENTRYPOINT ["/usr/local/bin/pipenv", "run", "src/linkbak/lnk2bak.py"]
