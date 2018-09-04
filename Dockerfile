# This dockerfile is inspired from
# https://github.com/justinribeiro/dockerfiles/tree/master/chrome-headless
#
# Usage:
#
# docker run \
#   -v $(pwd):/workdir \   # Map host's cwd with linkbak's output dir
#   -u $(id -u):$(id -g) \        # Run command as current user
#   --rm \                        # Removes the container upon exit
#   -ti \                         # Run interactively, allocate a pseudo tty
#   linkbak \
#   /linkbak/src/linkbak/lnk2bak.py [OPTIONS] file_or_url
#

FROM python:3.7.0-slim-stretch
LABEL name="linkbak" \
			maintainer="Aurélien Grosdidier <aurelien.grosdidier@gmail.com>" \
			version="0.1" \
			description="Linkbak"

# Install:
# - dumb-init (to avoid zombie processes)
# - chromium
# - pandoc and texlive (required for PDF output)
# - curl/gnupg2/git (required by nodejs below)
RUN apt-get update && apt-get install -y \
  dumb-init \
	chromium \
  pandoc \
  texlive \
  texlive-latex-recommended \
  texlive-generic-recommended \
  texlive-latex-extra \
  lmodern \
  curl \
  gnupg2 \
  git \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

# Install nodejs
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - \
  && apt-get install -y nodejs

# Install nodejs dependencies globally with npm
RUN npm -g install \
  fs \
  jsdom \
  https://github.com/mozilla/readability

# Copy requirements.txt and install dependencies with pip
ENV LINKBAK /linkbak
COPY requirements.txt $LINKBAK/
RUN pip install -r $LINKBAK/requirements.txt

# Copy source
COPY . $LINKBAK
ENV PYTHONPATH $LINKBAK/src

# Set input/output directory
WORKDIR /workdir

# use dumb-init as the entry point
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
