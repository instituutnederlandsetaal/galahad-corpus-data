"""Convert TEI XML files to TSV format using the Galahad API."""

import json
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import Path as ZipPath
from zipfile import ZipFile

from scripts.util.timer import Timer
from scripts.web.ziputil import MultiPartFile, zip_folder


def create(name: str, api: str) -> str:
    """Create a new corpus with the given name and return its UUID."""
    data = json.dumps(
        {"name": name, "owner": "user", "collaborators": [], "viewers": []},
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = Request(f"{api}/corpora", data=data, headers=headers)
    with urlopen(req) as res:
        return json.load(res)


def delete(api: str, uuid: str) -> None:
    """Delete the corpus with the given UUID for cleaning."""
    req = Request(f"{api}/corpora/{uuid}", method="DELETE")
    urlopen(req)


def upload(api: str, uuid: str, zip_file: BytesIO) -> None:
    """Upload the files as a zip to the given corpus."""
    mp = MultiPartFile(zip_file.read(), name="file")
    req = Request(
        f"{api}/corpora/{uuid}/layers/source/documents",
        data=bytes(mp),
        method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={mp.boundary}")
    urlopen(req)


def export(api: str, uuid: str) -> BytesIO:
    """Export the corpus as TSV files in a zip."""
    url = f"{api}/corpora/{uuid}/layers/source/export/convert?format=tsv"
    with urlopen(url) as res:
        return BytesIO(res.read())


def unzip(data: BytesIO, out: Path) -> None:
    """Unzip zip file bytes to out."""
    with ZipFile(data, "r") as zip_file:
        for path in ZipPath(zip_file).iterdir():
            if path.is_file():  # ignore metadata/ dir
                zip_file.extract(path.name, out)


def convert(folder: Path, api: str, out: Path) -> None:
    """Convert all TEI files in the folder to TSV in out."""
    print(f"Processing {folder.name}")
    uuid = create(folder.name, api)
    with Timer("Zipping"):
        zip_file = zip_folder(folder)

    with Timer("Uploading"):
        upload(api, uuid, zip_file)

    with Timer("Exporting"):
        zip_file = export(api, uuid)

    with Timer("Extracting"):
        unzip(zip_file, out / folder.name)

    with Timer("Cleaning"):
        delete(api, uuid)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Lancelot-Galahad TEI to TSV converter",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api",
        type=str,
        default="http://localhost:8010",
        help="Galahad API base URL",
    )
    parser.add_argument("-r", action="store_true", help="Recursive")
    parser.add_argument(
        "input",
        type=Path,
        help="Directory containing project or project subdirectories",
    )
    parser.add_argument("outdir", type=Path, help="Output directory for TSV data")
    args = parser.parse_args()

    args.outdir.mkdir(exist_ok=True, parents=True)

    with Timer("Total"):
        if args.r:
            for project_dir in args.input.iterdir():
                if project_dir.is_dir():
                    convert(project_dir, args.api, args.outdir)
        else:
            convert(args.input, args.api, args.outdir)
