"""
Command line tool to upload TEI-files and directories to BlackLab.
Zips the specified files or directories and uploads them to the specified host.
"""

from argparse import ArgumentParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import ParseResult, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from scripts.web.ziputil import MultiPartFile, zip_folder


def create_corpus(base_url: str, corpus_name: str, fmt: str = "GalahadCobaltTEI"):
    data = urlencode({"name": corpus_name, "format": fmt}).encode()
    url = urljoin(base_url, "lancelot/blacklab-server/")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    urlopen(req)
    print(f"Created {corpus_name}")


def delete_corpus(base_url: str, corpus: str):
    url = urljoin(base_url, f"lancelot/blacklab-server/{corpus}")
    try:
        urlopen(Request(url, method="DELETE"))
        print(f"Deleted {corpus}")
    except Exception:
        pass


def add_scheme(url: str) -> str:
    parse_result: ParseResult = urlparse(url)
    if not parse_result.scheme:
        return "http://" + parse_result.geturl()
    return parse_result.geturl()


def upload_corpus(base_url: str, corpus: str, zip_path: Path):
    url = urljoin(base_url, f"lancelot/blacklab-server/{corpus}/docs")
    mp = MultiPartFile(zip_path.read_bytes())
    req = Request(url, data=bytes(mp), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={mp.boundary}")
    urlopen(req)
    print(f"Uploaded files to {corpus}")


def check_exists_corpus(base_url: str, corpus: str):
    url = urljoin(base_url, f"lancelot/blacklab-server/{corpus}")
    try:
        with urlopen(url) as res:
            if res.status == 200:
                raise Exception(f"Corpus {corpus} already exists. Use -f to overwrite.")
    except HTTPError:
        pass  # corpus was not found, can be safely created


def handle_single_corpus(
    base_url: str,
    input: Path,
    force: bool,
    recursive: bool = False,
):
    corpus = (
        "lancelot:galahad-corpus-data"
        if input.name == "source-data"
        else f"lancelot:{input.name}"
    )
    if force:
        delete_corpus(base_url, corpus)
    else:
        check_exists_corpus(base_url, corpus)
    create_corpus(base_url, corpus)
    zip_bytes = zip_folder(input, recursive=recursive)
    print(f"Zipped {input.name}")
    zip_file = Path("corpus.zip")
    zip_file.write_bytes(zip_bytes.read())
    upload_corpus(base_url, corpus, zip_file)


if __name__ == "__main__":
    cli = ArgumentParser()
    cli.add_argument("-r", action="store_true")
    cli.add_argument("-f", action="store_true")
    cli.add_argument("--host", default="localhost")
    cli.add_argument("input", type=Path)
    args = cli.parse_args()
    base_url = add_scheme(args.host)

    if not args.r:
        handle_single_corpus(base_url, args.input, args.f)
    else:  # handle upper folder as single corpus and subfolders as subcorpora
        # subcorpora
        for subdir in args.input.iterdir():
            handle_single_corpus(base_url, subdir, args.f)
        # total corpus
        handle_single_corpus(base_url, args.input, args.f, recursive=True)
