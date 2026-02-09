VERSION="${1}"
ARCHITECTURE="${2:-$(uname -m)}"

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> [architecture]"
    exit 1
fi

if [ "$ARCHITECTURE" = "x86_64" ]; then
    source venv_x86/bin/activate
else
    source venv/bin/activate
fi

python tools/update_version.py "$VERSION"
python tools/make_distro.py
cd distro

if [ "$ARCHITECTURE" = "x86_64" ]; then
    sed -i '' -E "s/^[[:space:]]*#?[[:space:]]*target_arch='x86_64'.*/    target_arch='x86_64',/" "zoia_lib_mac.spec"
else
    sed -i '' -E "s/^[[:space:]]*#?[[:space:]]*target_arch='x86_64'.*/    # target_arch='x86_64', # uncomment for Intel-based Mac/" "zoia_lib_mac.spec"
fi
python -m PyInstaller --clean --noconfirm zoia_lib_mac.spec
