"""Extract an untrusted zip into an empty directory.

Refuses absolute paths, '..' components, symlinks and anything resolving
outside the destination; caps the total size and each entry's real size.
Run with `python3 -I`.
"""
import os
import sys
import zipfile

LIMIT = 1_500_000_000


def main(src, dst):
    if os.path.exists(dst) and os.listdir(dst):
        raise SystemExit("destination must be empty: " + dst)
    os.makedirs(dst, exist_ok=True)
    root = os.path.realpath(dst)
    total = 0
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                print("skip symlink", name)
                continue
            if name.startswith("/") or ".." in name.split("/") or ":" in name:
                print("skip unsafe", name)
                continue
            out = os.path.realpath(os.path.join(root, name))
            if not out.startswith(root + os.sep):
                print("skip escape", name)
                continue
            if info.is_dir():
                os.makedirs(out, exist_ok=True)
                continue
            total += info.file_size
            if total > LIMIT:
                raise SystemExit("size limit exceeded")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            written = 0
            with z.open(info) as r, open(out, "wb") as w:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > info.file_size + 1024:
                        raise SystemExit("entry larger than declared: " + name)
                    w.write(chunk)
            os.chmod(out, 0o644)
    print("extracted", total, "bytes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
