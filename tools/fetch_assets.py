"""
Generate / fetch ancillary assets for the Giroux Daguerreotype project.

Run with Blender's python (so we get numpy and bpy.image):
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python tools/fetch_assets.py -- --out dist/

Produces:
    dist/textures/mahogany_color.png
    dist/textures/mahogany_normal.png
    dist/textures/brass_color.png
    dist/textures/leather_color.png
    dist/textures/ground_glass_normal.png
    dist/textures/silver_dark_speckle.png
    dist/textures/boulevard_du_temple_1838.png   (downloaded if possible, else procedural)
    dist/textures/boulevard_du_temple_inverted.png
    dist/textures/safelight_equi.png             (red darkroom environment)
    dist/audio/brass_click.wav
    dist/audio/wood_slide.wav
    dist/audio/dark_slide.wav
    dist/audio/chem_bubble.wav
"""
import bpy
import numpy as np
import os
import sys
import struct
import wave
import math
import urllib.request

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []
out_dir = "dist"
for i, a in enumerate(argv):
    if a == "--out" and i + 1 < len(argv):
        out_dir = argv[i + 1]
out_dir = os.path.abspath(out_dir)
TEX = os.path.join(out_dir, "textures")
AUD = os.path.join(out_dir, "audio")
os.makedirs(TEX, exist_ok=True)
os.makedirs(AUD, exist_ok=True)


# ---------- numpy -> PNG via Blender's image API ----------
def save_png(path, rgba_array):
    """rgba_array shape (H, W, 4) float32 in [0,1]. Writes via Blender."""
    h, w, _ = rgba_array.shape
    img = bpy.data.images.new(name=os.path.basename(path), width=w, height=h, alpha=True, float_buffer=False)
    # Blender expects flat array, bottom-up, RGBA
    flipped = np.flipud(rgba_array)
    img.pixels = flipped.reshape(-1).tolist()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    print(f"[asset] {path}")


def normal_from_height(height, strength=2.0):
    """Compute normal map (XYZ in [0,1]) from a height field (H,W) float32."""
    h, w = height.shape
    dx = np.zeros_like(height)
    dy = np.zeros_like(height)
    dx[:, 1:-1] = (height[:, 2:] - height[:, :-2]) * strength
    dy[1:-1, :] = (height[2:, :] - height[:-2, :]) * strength
    nz = np.ones_like(height)
    norm = np.stack([-dx, -dy, nz], axis=-1)
    length = np.linalg.norm(norm, axis=-1, keepdims=True)
    norm = norm / length
    # Map [-1,1] -> [0,1]
    out = (norm * 0.5 + 0.5).astype(np.float32)
    rgba = np.concatenate([out, np.ones((h, w, 1), dtype=np.float32)], axis=-1)
    return rgba


# ---------- Mahogany ----------
def gen_mahogany(size=512):
    rng = np.random.default_rng(7)
    x = np.linspace(0, 6, size, dtype=np.float32)
    y = np.linspace(0, 6, size, dtype=np.float32)
    X, Y = np.meshgrid(x, y)
    # Long-grain stripes oriented along X
    stripes = 0.5 + 0.5 * np.sin(Y * 18 + 0.4 * np.sin(X * 0.7) + rng.normal(0, 0.1, X.shape))
    # Soft ring/wave perturbation (simulating annual rings)
    rings = 0.5 + 0.5 * np.sin(np.sqrt((X - 3) ** 2 + (Y - 3) ** 2) * 4 + rng.normal(0, 0.05, X.shape))
    grain = 0.6 * stripes + 0.4 * rings
    # Fine-grain noise
    noise = rng.normal(0.5, 0.07, X.shape)
    h = np.clip(0.55 * grain + 0.45 * noise, 0, 1).astype(np.float32)
    # Color palette: mahogany dark→mid brown
    base_dark = np.array([0.16, 0.06, 0.03], dtype=np.float32)
    base_lit  = np.array([0.46, 0.21, 0.10], dtype=np.float32)
    color = base_dark[None, None, :] + h[..., None] * (base_lit - base_dark)[None, None, :]
    alpha = np.ones_like(h)
    rgba = np.concatenate([color, alpha[..., None]], axis=-1)
    save_png(os.path.join(TEX, "mahogany_color.png"), rgba)
    # Normal: emphasise grain ridges
    save_png(os.path.join(TEX, "mahogany_normal.png"), normal_from_height(h * 0.6, strength=4.0))


# ---------- Brass ----------
def gen_brass(size=512):
    rng = np.random.default_rng(11)
    base = np.array([0.85, 0.66, 0.32], dtype=np.float32)
    noise = rng.normal(0.0, 0.025, (size, size, 1)).astype(np.float32)
    # Slow patina blotches
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    patina = np.exp(-(((xx - 0.3) ** 2 + (yy - 0.7) ** 2) / 0.18))
    patina += np.exp(-(((xx - 0.8) ** 2 + (yy - 0.2) ** 2) / 0.10))
    patina = np.clip(patina, 0, 1)[..., None]
    patina_col = np.array([0.55, 0.50, 0.20], dtype=np.float32)
    color = base[None, None, :] * (1 + noise)
    color = color * (1 - 0.45 * patina) + patina_col[None, None, :] * (0.45 * patina)
    color = np.clip(color, 0, 1)
    alpha = np.ones((size, size, 1), dtype=np.float32)
    rgba = np.concatenate([color, alpha], axis=-1)
    save_png(os.path.join(TEX, "brass_color.png"), rgba)


# ---------- Leather ----------
def gen_leather(size=512):
    rng = np.random.default_rng(23)
    base = np.array([0.26, 0.15, 0.08], dtype=np.float32)
    cells = rng.uniform(0, 1, (size // 16, size // 16)).astype(np.float32)
    cells = np.repeat(np.repeat(cells, 16, axis=0), 16, axis=1)
    cells += rng.normal(0, 0.06, (size, size))
    cells = np.clip(cells, 0, 1)
    color = base[None, None, :] * (0.7 + 0.6 * cells[..., None])
    color = np.clip(color, 0, 1)
    alpha = np.ones((size, size, 1), dtype=np.float32)
    rgba = np.concatenate([color, alpha], axis=-1)
    save_png(os.path.join(TEX, "leather_color.png"), rgba)


# ---------- Ground glass normal ----------
def gen_ground_glass_normal(size=512):
    rng = np.random.default_rng(31)
    h = rng.normal(0, 0.5, (size, size)).astype(np.float32)
    save_png(os.path.join(TEX, "ground_glass_normal.png"), normal_from_height(h, strength=1.5))


# ---------- Boulevard du Temple ----------
def fetch_boulevard(size=768):
    """Try to fetch from Wikimedia Commons; fall back to a procedural mockup."""
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Boulevard_du_Temple_by_Daguerre.jpg/1024px-Boulevard_du_Temple_by_Daguerre.jpg"
    dst = os.path.join(TEX, "_boulevard_src.jpg")
    img_rgba = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DaguerreotypeEduBuilder/1.0 (educational)"} )
        with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as fp:
            fp.write(r.read())
        # Load via Blender
        bi = bpy.data.images.load(dst)
        w, h = bi.size
        pix = np.array(bi.pixels[:], dtype=np.float32).reshape(h, w, 4)
        pix = np.flipud(pix)
        bpy.data.images.remove(bi)
        # Convert to silver-image tones: desaturate, slight warm tint, contrast
        lum = 0.299 * pix[..., 0] + 0.587 * pix[..., 1] + 0.114 * pix[..., 2]
        lum = np.clip((lum - 0.45) * 1.6 + 0.45, 0, 1)
        tint = np.stack([lum * 0.94 + 0.06, lum * 0.92, lum * 0.84], axis=-1)
        img_rgba = np.concatenate([tint, np.ones_like(lum)[..., None]], axis=-1).astype(np.float32)
        # Resize via simple subsample if needed
        if w != size:
            step_x = max(1, w // size)
            step_y = max(1, h // size)
            img_rgba = img_rgba[::step_y, ::step_x]
        print(f"[asset] Boulevard du Temple downloaded ({w}x{h})")
    except Exception as ex:
        print(f"[warn] Boulevard du Temple download failed ({ex}); generating procedural fallback.")
        img_rgba = procedural_paris_scene(size)
    save_png(os.path.join(TEX, "boulevard_du_temple_1838.png"), img_rgba)
    # Inverted (180°, used for camera-projected image plane)
    save_png(os.path.join(TEX, "boulevard_du_temple_inverted.png"), np.rot90(img_rgba, 2).copy())


def procedural_paris_scene(size=1024):
    """A symbolic substitute: silver-toned wash with horizon, buildings, sky."""
    rng = np.random.default_rng(41)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    sky = 0.62 + 0.18 * (1 - yy)
    ground = 0.48 - 0.10 * (yy - 0.55)
    horizon = 0.55
    img = np.where(yy < horizon, sky, ground)
    # Building silhouettes
    for _ in range(20):
        bx = rng.uniform(0, 1)
        bw = rng.uniform(0.02, 0.10)
        bh = rng.uniform(0.08, 0.30)
        mask = (xx > bx) & (xx < bx + bw) & (yy > horizon - bh) & (yy < horizon)
        img = np.where(mask, 0.35 + rng.uniform(0, 0.1), img)
    img += rng.normal(0, 0.02, img.shape)
    img = np.clip(img, 0, 1).astype(np.float32)
    tint = np.stack([img * 0.94 + 0.05, img * 0.91, img * 0.83], axis=-1)
    alpha = np.ones((size, size, 1), dtype=np.float32)
    return np.concatenate([tint, alpha], axis=-1)


# ---------- Red safelight equirectangular ----------
def gen_safelight(width=1024, height=512):
    rng = np.random.default_rng(53)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    # Slight warm gradient + scattered "lamp" spot
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[..., 0] = 0.45 + 0.20 * (1.0 - yy / height)
    base[..., 1] = 0.05 + 0.02 * (1.0 - yy / height)
    base[..., 2] = 0.03
    # Lamp hotspot
    cx, cy = width * 0.55, height * 0.30
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    hotspot = np.exp(-r2 / (2 * (height * 0.10) ** 2))
    base[..., 0] += hotspot * 0.7
    base[..., 1] += hotspot * 0.1
    base[..., 2] += hotspot * 0.02
    base += rng.normal(0, 0.01, base.shape).astype(np.float32)
    base = np.clip(base, 0, 1)
    alpha = np.ones((height, width, 1), dtype=np.float32)
    rgba = np.concatenate([base, alpha], axis=-1)
    save_png(os.path.join(TEX, "safelight_equi.png"), rgba)


# ---------- Procedural audio ----------
def write_wav(path, samples, sample_rate=22050):
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    print(f"[asset] {path}")


def env(n, attack=0.005, decay=0.5, sr=22050):
    a = min(int(attack * sr), n)
    d = min(int(decay * sr), max(0, n - a))
    e = np.zeros(n, dtype=np.float32)
    if a > 0: e[:a] = np.linspace(0, 1, a)
    if d > 0: e[a:a + d] = np.exp(-np.linspace(0, 5, d))
    return e


def gen_brass_click(sr=22050):
    n = int(0.25 * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(2)
    # Bright impulse with metallic ring
    base = (np.sin(2 * np.pi * 1500 * t) * 0.4 +
            np.sin(2 * np.pi * 2900 * t) * 0.3 +
            np.sin(2 * np.pi * 5300 * t) * 0.2)
    noise = rng.normal(0, 1, n) * np.exp(-t * 80) * 0.4
    sig = (base + noise) * env(n, 0.001, 0.20)
    write_wav(os.path.join(AUD, "brass_click.wav"), sig, sr)


def gen_wood_slide(sr=22050):
    n = int(1.2 * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(3)
    # Filtered noise → wooden scraping
    noise = rng.normal(0, 1, n)
    # Low-pass via cumulative moving average
    k = 80
    kernel = np.ones(k) / k
    noise_lp = np.convolve(noise, kernel, mode="same")
    sig = noise_lp * (0.5 + 0.5 * np.sin(2 * np.pi * 1.0 * t)) * env(n, 0.05, 1.0) * 0.6
    write_wav(os.path.join(AUD, "wood_slide.wav"), sig, sr)


def gen_dark_slide(sr=22050):
    n = int(0.7 * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(4)
    noise = rng.normal(0, 1, n)
    kernel = np.ones(40) / 40
    noise_lp = np.convolve(noise, kernel, mode="same")
    sig = noise_lp * env(n, 0.02, 0.6) * 0.5
    write_wav(os.path.join(AUD, "dark_slide.wav"), sig, sr)


def gen_chem_bubble(sr=22050):
    n = int(2.0 * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(5)
    sig = np.zeros(n, dtype=np.float32)
    for _ in range(28):
        center = rng.uniform(0, t[-1])
        f0 = rng.uniform(380, 1300)
        f1 = f0 * rng.uniform(1.5, 2.5)
        bd = 0.12
        idx = (t > center) & (t < center + bd)
        local = t[idx] - center
        env_b = np.exp(-local * 25)
        freq = f0 + (f1 - f0) * (local / bd)
        sig[idx] += np.sin(2 * np.pi * freq * local) * env_b * rng.uniform(0.1, 0.25)
    sig += rng.normal(0, 0.03, n)
    sig *= env(n, 0.05, 2.0)
    write_wav(os.path.join(AUD, "chem_bubble.wav"), sig, sr)


def gen_silence_marker(sr=22050):
    n = int(0.2 * sr)
    sig = np.zeros(n, dtype=np.float32)
    write_wav(os.path.join(AUD, "silence.wav"), sig, sr)


# ---------- Run all ----------
gen_mahogany()
gen_brass()
gen_leather()
gen_ground_glass_normal()
fetch_boulevard()
gen_safelight()
gen_brass_click()
gen_wood_slide()
gen_dark_slide()
gen_chem_bubble()
gen_silence_marker()
print("[done] all assets generated:", out_dir)
