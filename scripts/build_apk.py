"""Build NaiShi offline APK. Set ANDROID_BUILD_TOOLS and ANDROID_JAR to reuse a local SDK."""
from pathlib import Path
import os, subprocess, zipfile, secrets, hashlib, shutil, json
import sys
import re
import xml.etree.ElementTree as ET
os.environ['PYTHONUTF8'] = '1'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(os.environ['ANDROID_BUILD_TOOLS'])
JAR = Path(os.environ['ANDROID_JAR'])
JAVA = Path(os.environ['JAVA_HOME']) / 'bin'
BUILD = ROOT / 'android/build'
for folder in [BUILD, ROOT/'dist', ROOT/'.private', ROOT/'android/assets', ROOT/'android/res/drawable']:
    folder.mkdir(parents=True, exist_ok=True)
shutil.copyfile(JAR, BUILD/'android.jar')
JAR = BUILD/'android.jar'

def run(args):
    argv = [p.relative_to(ROOT).as_posix() if isinstance(p, Path) and p.is_relative_to(ROOT) else str(p) for p in args]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stdout: print(result.stdout.strip())
    if result.stderr: print(result.stderr.strip())
    result.check_returncode()
    return result.stdout

run(['python', ROOT/'词库/tools/render_reader.py'])
run(['python', ROOT/'词库/tools/validate.py'])
shutil.copyfile(ROOT/'词库/打开词库.html', ROOT/'android/assets/index.html')
shutil.copyfile(ROOT/'词库/source/LICENSE', ROOT/'android/assets/LICENSE.txt')
with Image.open(ROOT/'app图标/奶屎.png') as im:
    im.resize((192,192), Image.Resampling.LANCZOS).save(ROOT/'android/res/drawable/icon.png')
classes = BUILD/'classes'; dex = BUILD/'dex'
for folder in [classes, dex]:
    folder.mkdir(exist_ok=True)
    for p in folder.rglob('*'):
        if p.is_file():
            assert not p.is_symlink() and p.resolve().is_relative_to(BUILD.resolve())
            p.unlink()
run([JAVA/'javac.exe', '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-bootclasspath', str(JAR)+os.pathsep+str(TOOLS/'core-lambda-stubs.jar'), '-d', classes, ROOT/'android/src/MainActivity.java'])
run([JAVA/'java.exe', '-cp', TOOLS/'lib/d8.jar', 'com.android.tools.r8.D8', '--lib', JAR, '--min-api', '26', '--output', dex, *classes.rglob('*.class')])
run([TOOLS/'aapt.exe', 'package', '-f', '-M', ROOT/'android/AndroidManifest.xml', '-S', ROOT/'android/res', '-A', ROOT/'android/assets', '-I', JAR, '-F', BUILD/'unsigned.apk'])
with zipfile.ZipFile(BUILD/'unsigned.apk', 'a', compression=zipfile.ZIP_DEFLATED) as archive:
    archive.write(dex/'classes.dex', 'classes.dex')
run([TOOLS/'zipalign.exe', '-f', '4', BUILD/'unsigned.apk', BUILD/'aligned.apk'])
password = ROOT/'.private/signing-password.txt'
key = ROOT/'.private/naishi-release.jks'
if (ROOT/'dist/NaiShi-1.0.0.apk').exists() and not key.exists(): raise RuntimeError('Original signing key missing')
if key.exists() and not password.exists(): raise RuntimeError('Signing password missing; preserve existing key')
if not password.exists(): password.write_text(secrets.token_urlsafe(32), encoding='utf-8')
os.environ['NAISHI_SIGN_PASS'] = password.read_text(encoding='utf-8').strip()
if not key.exists():
    run([JAVA/'keytool.exe', '-genkeypair', '-keystore', key, '-storepass:env', 'NAISHI_SIGN_PASS', '-keypass:env', 'NAISHI_SIGN_PASS', '-alias', 'naishi', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000', '-dname', 'CN=NaiShi'])
version=ET.parse(ROOT/'android/AndroidManifest.xml').getroot().get('{http://schemas.android.com/apk/res/android}versionName')
assert re.fullmatch(r'\d+\.\d+\.\d+',version)
target = ROOT/f'dist/NaiShi-{version}.apk'
run([JAVA/'java.exe', '-jar', TOOLS/'lib/apksigner.jar', 'sign', '--ks', key, '--ks-key-alias', 'naishi', '--ks-pass', 'env:NAISHI_SIGN_PASS', '--key-pass', 'env:NAISHI_SIGN_PASS', '--out', target, BUILD/'aligned.apk'])
verification = run([JAVA/'java.exe', '-jar', TOOLS/'lib/apksigner.jar', 'verify', '--verbose', target])
if (ROOT/'dist/NaiShi-1.0.0.apk').exists():
    old_cert=run([JAVA/'java.exe','-jar',TOOLS/'lib/apksigner.jar','verify','--print-certs',ROOT/'dist/NaiShi-1.0.0.apk'])
    new_cert=run([JAVA/'java.exe','-jar',TOOLS/'lib/apksigner.jar','verify','--print-certs',target])
    assert re.search(r'certificate SHA-256 digest: (\w+)',old_cert)[1]==re.search(r'certificate SHA-256 digest: (\w+)',new_cert)[1]
badging = run([TOOLS/'aapt.exe', 'dump', 'badging', target])
assert "package: name='app.naishi.android'" in badging
assert "application-label:'NaiShi'" in badging
assert 'uses-permission:' not in badging
with zipfile.ZipFile(target) as archive:
    assert archive.read('assets/index.html') == (ROOT/'词库/打开词库.html').read_bytes()
    assert archive.read('classes.dex') == (dex/'classes.dex').read_bytes()
    assert not any('.private' in name or name.endswith('.jks') for name in archive.namelist())
(ROOT/'dist/apk-verification.txt').write_text(verification+'\n'+badging+'\nAssets and DEX match current source build. No device test performed.\n', encoding='utf-8')
(ROOT/'dist/SHA256SUMS.txt').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n', encoding='utf-8')
print('APK verified:', target.name, target.stat().st_size, 'bytes')
