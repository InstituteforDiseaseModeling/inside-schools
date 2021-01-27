'''
Scraper to auto-generate the NOTICE file.
'''


import os
import re
import subprocess
from argparse import ArgumentParser
from pathlib import Path
from packaging.requirements import REQUIREMENT
import importlib_metadata as im
import sciris as sc


NOTICE_FILE = 'NOTICE' # Define the output file here
project_name = 'covasim_schools' # Define the package name here

cwd = Path(os.path.dirname(os.path.abspath(__file__)))
project = cwd.parent.resolve()
encoding = "utf-8"
config = None

# Manually substitute missing licenses -- add here if any are missing
MIT = 'MIT'
sharealike = 'Creative Commons Attribution-ShareAlike 4.0 International Public License'
missing_licenses = dict(
    sciris = MIT,
    optuna = MIT,
    covasim = sharealike,
    synthpops = sharealike,
)


class Config:
    encoding = encoding
    format = 'text'
    excludes = ['pip', 'setuptools', 'wheel', 'pkg-resources', 'packaging', project_name]
    includes = list(map(lambda r: REQUIREMENT.parseString(r)[0], im.distribution(project_name).requires))
    verbose = False
    graph = False
    outfile = cwd.joinpath(NOTICE_FILE).as_posix()

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            setattr(self, key, val)
        if self.graph:
            self.includes.clear()
        includestr = '\n  '.join(self.includes)
        print(f'Compiling licenses for "{project_name}":\n  {includestr}')
        print(f'Saving to: {self.outfile}')
        return

    def exclude_package(self, name:str):
        return self.excludes is not None and name in self.excludes

    def include_package(self, name:str):
        return not self.exclude_package(name) \
               and self.includes is not None and name in self.includes

    def keep_dist(self, dist: im.Distribution):
        return self.include_package(dist.metadata['Name'])


class Record:
    name = ""
    version = ""
    url = ""
    license = ""
    license_text = ""

    def __init__(self, name="", version="", url="", license="", license_text="", **kwargs):
        self.name = name
        self.version = version
        self.url = url
        self.license = license
        self.license_text = license_text


    @staticmethod
    def get_license(dist_path):
        license_text = ""

        dist_dir = Path(dist_path)
        license_files = []
        license_files.extend(list(dist_dir.rglob('LICEN[SC]E')))
        if len(license_files) == 0:
            license_files.extend(list(dist_dir.rglob('LICEN[SC]E.*')))

        if len(license_files) > 0:
            license_text = license_files[0].read_text(encoding=encoding)

        return license_text


    @staticmethod
    def from_distribution(dist):
        record = Record()
        record.name = f"{dist.metadata['Name']}"
        record.version = dist.version
        record.url = f"{dist.metadata['Home-page']}"
        record.license = f"{dist.metadata['License']}"
        if record.license == 'UNKNOWN':
            print(f'Warning!! Manually substituting license for "{record.name}"')
            try:
                record.license = missing_licenses[record.name]
            except KeyError as E:
                errormsg = f'License is unknown for {record.name} and is not found manually; please add to the dict'
                raise Exception(errormsg) from E
        record.license_text = Record.get_license(dist.locate_file('.'))

        return record


    @staticmethod
    def from_name(name:str):
        try:
            dist = im.distribution(name)
            return Record.from_distribution(dist)
        except im.PackageNotFoundError as e:
            print(f"No package named '{name}' found.", e)


def get_pkg_name(path: Path):
    return re.sub(r'^(.*?)-\d+(\.\d+)+$', r'\1', path.stem).replace('_', '-')



def get_js_requirements(config:Config):
    js_reqs_json = subprocess.run(
            ['node', cwd.joinpath('notice.js')],
            capture_output=True
    ).stdout.decode(encoding=encoding)

    return list(
            map(
                    lambda r: Record(**r),
                    sc.loadjson(js_reqs_json, fromfile=False)
            )
    )

def get_requirements(config:Config):
    py_reqs = []
    if config.graph:
        py_reqs = list(
                map(
                        Record.from_distribution,
                        filter(config.keep_dist, im.distributions())
                )
        )
    else:
        py_reqs = list(
                map(
                        Record.from_name,
                        config.includes
                )
        )
    py_reqs = list(filter(lambda r: r is not None, py_reqs))

    reqs = [*py_reqs]
    reqs.sort(key=lambda r: r.name)
    if config.verbose:
        for req in reqs:
            sc.pp(req.__dict__)
    return reqs


def as_json(file, reqs):
    return sc.savejson(file, reqs, indent=True)


def text_format(req: Record):
    record = []
    for key, value in vars(req).items():
        if key != 'license_text':
            record.append(f"{key}: {value}")
        else:
            record.append("-" * 16)
            record.append(value)
    return record


def as_text(file, reqs):
    records = list(map(text_format, reqs))
    nl = "\n"
    hr = "".join([nl, "=" * 80, nl])
    header = nl.join([
        project_name,
        "THIRD - PARTY SOFTWARE NOTICES AND INFORMATION",
        "This project incorporates components from the projects listed below.",
        hr,
        nl
    ])

    footer = nl.join([hr, nl])
    file.write(header)
    for record in records:
        file.write(nl.join(record))
        file.write(footer)
        file.flush()
    return


if __name__ == '__main__':
    parser = ArgumentParser(description="Generate license NOTICE file for 3rd party packages")
    parser.add_argument("-f", "--format", default="text", choices=['text', 'json', 'csv'])
    parser.add_argument("-o", "--outfile", default=Config.outfile, help=f"Path to output file. Default: {Config.outfile}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Output more verbose logging.")
    parser.add_argument("-g", "--graph", action="store_true", help="Include transitive dependencies")
    args = parser.parse_args()

    config = Config(**args.__dict__)
    if args.verbose:
        sc.pp(args)
        sc.pp(config.__dict__)
    requirements = get_requirements(config)
    writer_fn = getattr(globals(), f"as_{args.format}".lower(), as_text)

    with open(config.outfile, "w", encoding="utf-8", newline="\n") as f:
        writer_fn(f, requirements)
        f.close()