import os
import tempfile
import shutil
import yaml
import chromadb
from pathlib import Path

from mempalace.miner import mine, scan_project


def test_project_mining():
    tmpdir = tempfile.mkdtemp()
    # Create a mini project
    os.makedirs(os.path.join(tmpdir, "backend"))
    with open(os.path.join(tmpdir, "backend", "app.py"), "w") as f:
        f.write("def main():\n    print('hello world')\n" * 20)
    # Create config
    with open(os.path.join(tmpdir, "mempalace.yaml"), "w") as f:
        yaml.dump(
            {
                "wing": "test_project",
                "rooms": [
                    {"name": "backend", "description": "Backend code"},
                    {"name": "general", "description": "General"},
                ],
            },
            f,
        )

    palace_path = os.path.join(tmpdir, "palace")
    mine(tmpdir, palace_path)

    # Verify
    client = chromadb.PersistentClient(path=palace_path)
    col = client.get_collection("mempalace_drawers")
    assert col.count() > 0

    shutil.rmtree(tmpdir)


def test_scan_project_respects_gitignore():
    tmpdir = tempfile.mkdtemp()
    try:
        project_root = Path(tmpdir).resolve()
        os.makedirs(project_root / "src")
        os.makedirs(project_root / "generated")

        (project_root / ".gitignore").write_text("ignored.py\ngenerated/\n", encoding="utf-8")
        (project_root / "src" / "app.py").write_text("print('hello')\n" * 20, encoding="utf-8")
        (project_root / "ignored.py").write_text("print('ignore me')\n" * 20, encoding="utf-8")
        (project_root / "generated" / "artifact.py").write_text(
            "print('ignore this dir')\n" * 20,
            encoding="utf-8",
        )

        files = scan_project(str(project_root))
        relative_files = sorted(path.relative_to(project_root).as_posix() for path in files)

        assert relative_files == ["src/app.py"]
    finally:
        shutil.rmtree(tmpdir)


def test_scan_project_handles_gitignore_negation():
    tmpdir = tempfile.mkdtemp()
    try:
        project_root = Path(tmpdir).resolve()
        os.makedirs(project_root / "generated")

        (project_root / ".gitignore").write_text(
            "generated/\n!generated/keep.py\n",
            encoding="utf-8",
        )
        (project_root / "generated" / "drop.py").write_text("print('drop')\n" * 20, encoding="utf-8")
        (project_root / "generated" / "keep.py").write_text("print('keep')\n" * 20, encoding="utf-8")

        files = scan_project(str(project_root))
        relative_files = sorted(path.relative_to(project_root).as_posix() for path in files)

        assert relative_files == ["generated/keep.py"]
    finally:
        shutil.rmtree(tmpdir)
