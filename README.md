# What is `linkbak`

`linkbak` is a web page archiver : it reads a list of links and dumps the
corresponding pages in HTML and PDF. It is somewhat similar to
[bookmark-archiver](https://github.com/pirate/bookmark-archiver), but lighter
(no UI, just raw HTML/PDF dumps) and faster (allowing for several downloads in
parallel).

The HTML content is extracted with `readability`, PDFs are generated with
`chromium` in `headless` mode. Links can be downloaded in parallel, previous
failed attempts can be ignored or retried, and a custom timeout is supported.

## Input

- Atom (URL or local)
- RSS (URL or local)
- HTML (local)
- text file containing a list of URLs (one per line)

## Output

Pages (HTML/PDF) are stored in output directories identified by the sha256 of
the links to avoid collisions. An additional JSON index is also written to keep
track of which links are stored in which directory.

# Installation

The easy way, with Docker:

```
git clone https://github.com/aurelg/linkbak.git
cd linkbak
docker build -t linkbak .
```

# Example

Example: `lnk2bak.py -v -j10 https://github.com/shaarli/Shaarli/releases.atom`

Or with docker:

```
docker run \
  -v $(pwd):/workdir \
  -u $(id -u):$(id -g) \
  --rm -ti linkbak \
  /linkbak/src/linkbak/lnk2bak.py -j1 -v links.txt
```

You may want to define an alias like:

`alias linkbak='docker run -v $(pwd):/workdir -u $(id -u):$(id -g) --rm -ti linkbak /linkbak/src/linkbak/lnk2bak.py'`

This command downloads HTML and generates PDFs for each of the links found in
the Shaarli atom feed on Github, allowing up to 10 downloads in parallel.

Output:

```
.
├── 394a30c14c9f36....
│   ├── index.html
│   ├── metadata.json
│   └── output.pdf
├── 4357bbfb8b7788....
│   ├── index.html
│   ├── metadata.json
│   └── output.pdf
├── 51ec955a6fe728....
│   ├── index.html
│   ├── metadata.json
│   └── output.pdf
...

10 directories, 31 files
```

If the HTML, metadata or PDF cannot be retrieved, an error message is written in
a logfile named `{index.html,metadata.json,output.pdf}.log`, respectively.

In each link directory, a `metadata.json` file containing the `sha156` and the
URL is written:

```
{
 "id": "394a30c14c9f36830d77dca945ed6d558ea3ede08b9009bbffa3b6e92dc68f30",
 "link": "https://github.com/shaarli/Shaarli/releases/tag/v0.9.6"
}
```

All these `metadata.json` files are eventually merged in `results.json` once all
links are processed:

```
[
 {
  "id": "51ec955a6fe728451be9c8ae654f1012e376e77ae45ad8235ef9dd67b3f016d8",
  "link": "https://github.com/shaarli/Shaarli/releases/tag/v0.8.7"
 },
 {
  "id": "ea2cf19731ad7a1378e6d7d1b4dc84c65ee8808328db98dd80cc17cce6728bb3",
  "link": "https://github.com/shaarli/Shaarli/releases/tag/v0.9.3"
 },
 {
  "id": "394a30c14c9f36830d77dca945ed6d558ea3ede08b9009bbffa3b6e92dc68f30",
  "link": "https://github.com/shaarli/Shaarli/releases/tag/v0.9.6"
 },
 ...
]
```

This JSON file can probably be used to generate an HTML interface (with
pagination, hopefully).
