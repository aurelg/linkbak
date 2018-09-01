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
#
FROM python:3.7.0-slim-stretch
LABEL name="linkbak" \
			maintainer="Aurélien Grosdidier <aurelien.grosdidier@gmail.com>" \
			version="0.1" \
			description="Linkbak"

# Install Chromium
RUN apt-get update && apt-get install -y \
	chromium \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install dependencies with pip
ENV LINKBAK /linkbak
COPY requirements.txt $LINKBAK/
RUN pip install -r $LINKBAK/requirements.txt

# Copy source
COPY . $LINKBAK
ENV PYTHONPATH $LINKBAK/src

# Set input/output directory
WORKDIR /workdir
