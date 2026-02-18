python -m venv venv
venv/Scripts/activate

python -m pip install -r requirements.txt
python -m pip install pyinstaller pillow
python -m pip install tools/nodegraph/nodegraphqt-0.1.7-py3-none-any.whl

python tools/update_version.py "$VERSION"
python tools/make_distro.py
cd distro

python -m PyInstaller --clean --noconfirm zoia_lib_windows.spec
