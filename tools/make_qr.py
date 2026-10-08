"""사이트 주소 QR 두 가지: 기본 QR, 하트 QR. 만든 뒤 실제로 읽히는지 OpenCV로 확인한다."""
import math, random, cv2, numpy as np, qrcode
from PIL import Image, ImageDraw

URL = 'https://gardenhotelwedding.github.io'
INK, BG, PINK = (58, 47, 41), (250, 249, 246), (217, 163, 168)

def matrix():
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    q.add_data(URL); q.make(fit=True)
    return q.get_matrix()

def plain(path):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=40, border=4)
    q.add_data(URL); q.make(fit=True)
    q.make_image(fill_color='black', back_color='white').save(path)

def heart_poly(cx, cy, s, n=400):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts

def heart(path, W=2000, lace=False):
    M = matrix(); n = len(M)
    s = W / (39 if lace else 36)                        # 하트 크기 단위 (레이스는 가장자리 여유)
    hx, hy = W / 2, W * 0.47                            # 하트 중심
    poly = heart_poly(hx, hy, s)
    # QR(+둘레 4칸)이 하트 안에 완전히 들어가도록: 윗변은 가운데 오목한 곳보다 아래, 아래 모서리는 하트 안쪽
    m = 2 * 5.7 * s / (n + 8)                           # QR 한 칸 크기
    cx, cy = hx, hy + 0.9 * s                           # QR 중심(살짝 아래로)
    img = Image.new('RGB', (W, W), BG); d = ImageDraw.Draw(img)
    mask = Image.new('L', (W, W), 0); ImageDraw.Draw(mask).polygon(poly, fill=255); mask = np.array(mask)
    if lace: draw_lace(d, poly, mask, s)
    x0, y0 = cx - n * m / 2, cy - n * m / 2
    quiet = 4 * m
    rnd = random.Random(328)
    for gy in range(-80, 80):
        for gx in range(-80, 80):
            px, py = x0 + gx * m + m / 2, y0 + gy * m + m / 2
            if not (m < px < W - m and m < py < W - m) or mask[int(py), int(px)] == 0: continue
            if x0 - quiet <= px <= x0 + n * m + quiet and y0 - quiet <= py <= y0 + n * m + quiet: continue
            # 하트 테두리 바로 안쪽 한 칸은 비워서 윤곽선이 또렷하게
            if min(mask[int(py + dy), int(px + dx)] for dx in (-m, 0, m) for dy in (-m, 0, m)) == 0: continue
            if rnd.random() < .5:
                r = m * .38; d.ellipse([px - r, py - r, px + r, py + r], fill=INK)
    if not lace: d.line(poly + [poly[0]], fill=INK, width=max(4, int(m * .3)), joint='curve')
    def finder(fx, fy):
        X, Y = x0 + fx * m, y0 + fy * m
        d.rounded_rectangle([X, Y, X + 7 * m, Y + 7 * m], radius=m * 1.6, fill=INK)
        d.rounded_rectangle([X + m, Y + m, X + 6 * m, Y + 6 * m], radius=m * 1.1, fill=BG)
        d.rounded_rectangle([X + 2 * m, Y + 2 * m, X + 5 * m, Y + 5 * m], radius=m * .8, fill=INK)
    finders = [(0, 0), (n - 7, 0), (0, n - 7)]
    for r in range(n):
        for c in range(n):
            if any(fx <= c < fx + 7 and fy <= r < fy + 7 for fx, fy in finders): continue
            if M[r][c]:
                X, Y = x0 + c * m, y0 + r * m
                d.rounded_rectangle([X + m * .05, Y + m * .05, X + m * .95, Y + m * .95], radius=m * .28, fill=INK)
    for f in finders: finder(*f)
    hs = m * 3
    d.ellipse([cx - hs * 1.15, cy - hs * 1.15, cx + hs * 1.15, cy + hs * 1.15], fill=BG)
    d.polygon(heart_poly(cx, cy - hs * .1, hs / 17), fill=PINK)
    img.save(path)

def draw_lace(d, poly, mask, s):
    """하트 가장자리를 레이스처럼: 바깥으로 둥근 물결(스캘럽) + 물결마다 작은 구멍 + 안쪽 실선과 땀(점선)."""
    W = mask.shape[0]
    P = np.array(poly + [poly[0]])
    seg = np.hypot(*np.diff(P, axis=0).T); L = np.concatenate([[0], np.cumsum(seg)])
    step = s * 1.25                                     # 물결 하나의 폭
    k = int(L[-1] // step); step = L[-1] / k
    def at(t):
        i = min(np.searchsorted(L, t) - 1, len(P) - 2); i = max(i, 0)
        f = (t - L[i]) / max(seg[i], 1e-9); pt = P[i] + (P[i + 1] - P[i]) * f
        tg = (P[i + 1] - P[i]) / max(seg[i], 1e-9); nrm = np.array([tg[1], -tg[0]])
        probe = pt + nrm * 6
        if 0 <= probe[0] < W and 0 <= probe[1] < W and mask[int(probe[1]), int(probe[0])]: nrm = -nrm   # 바깥쪽으로
        return pt, nrm
    lw = max(3, int(s * .09)); r = step * .6
    notch = np.array([W / 2, poly[0][1]])               # 위쪽 오목한 곳(t=0)
    pts = [at(i * step + step / 2) for i in range(k)]
    pts = [(pt, n) for pt, n in pts if np.hypot(*(pt - notch)) > step * 1.6]
    circ = lambda c, rr, **kw: d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], **kw)
    for pt, nrm in pts: circ(pt + nrm * r * .3, r, fill=INK)          # 물결 바깥 윤곽(겹쳐서 하나의 띠)
    for pt, nrm in pts: circ(pt + nrm * r * .3, r - lw, fill=BG)
    d.polygon(poly, fill=BG)                                           # 안쪽 절반 지우기
    for pt, nrm in pts: circ(pt + nrm * r * .58, r * .2, outline=INK, width=max(2, lw - 1))   # 아일렛 구멍
    d.line(poly + [poly[0]], fill=INK, width=lw, joint='curve')
    inner = [(x, y) for x, y in poly]                                 # 안쪽 가는 두 번째 선
    cxh = sum(x for x, _ in poly) / len(poly); cyh = sum(y for _, y in poly) / len(poly)
    inner = [(cxh + (x - cxh) * .965, cyh + (y - cyh) * .965) for x, y in poly]
    d.line(inner + [inner[0]], fill=INK, width=max(2, lw // 2), joint='curve')

def square_lace(path, W=2000):
    """네모 QR + 가운데 핑크 하트 + 네모 테두리를 레이스(바깥 물결·구멍·안쪽 두 줄)로."""
    M = matrix(); n = len(M)
    img = Image.new('RGB', (W, W), BG); d = ImageDraw.Draw(img)
    frame = W * .78                                     # 레이스 안쪽 네모 한 변
    m = frame / (n + 10)                                # QR 한 칸 (둘레 5칸씩 여백)
    cx = cy = W / 2; x0, y0 = cx - n * m / 2, cy - n * m / 2
    F0, F1 = cx - frame / 2, cx + frame / 2
    lw = max(3, int(m * .32)); k = 16; step = frame / k; r = step * .6
    circ = lambda c, rr, **kw: d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], **kw)
    edge = []                                           # (물결 중심, 바깥 방향)
    for i in range(k):
        t = F0 + (i + .5) * step
        edge += [((t, F0), (0, -1)), ((t, F1), (0, 1)), ((F0, t), (-1, 0)), ((F1, t), (1, 0))]
    corners = [((F0, F0), (-.707, -.707)), ((F1, F0), (.707, -.707)), ((F0, F1), (-.707, .707)), ((F1, F1), (.707, .707))]
    allp = edge + corners
    for (x, y), (nx, ny) in allp: circ((x + nx * r * .3, y + ny * r * .3), r, fill=INK)
    for (x, y), (nx, ny) in allp: circ((x + nx * r * .3, y + ny * r * .3), r - lw, fill=BG)
    d.rectangle([F0, F0, F1, F1], fill=BG)              # 안쪽 절반 지워 물결만 남김
    for (x, y), (nx, ny) in allp: circ((x + nx * r * .6, y + ny * r * .6), r * .2, outline=INK, width=max(2, lw - 1))
    d.rectangle([F0, F0, F1, F1], outline=INK, width=lw)
    g = m * 1.1; d.rectangle([F0 + g, F0 + g, F1 - g, F1 - g], outline=INK, width=max(2, lw // 2))
    def finder(fx, fy):
        X, Y = x0 + fx * m, y0 + fy * m
        d.rounded_rectangle([X, Y, X + 7 * m, Y + 7 * m], radius=m * 1.6, fill=INK)
        d.rounded_rectangle([X + m, Y + m, X + 6 * m, Y + 6 * m], radius=m * 1.1, fill=BG)
        d.rounded_rectangle([X + 2 * m, Y + 2 * m, X + 5 * m, Y + 5 * m], radius=m * .8, fill=INK)
    finders = [(0, 0), (n - 7, 0), (0, n - 7)]
    for rr in range(n):
        for c in range(n):
            if any(fx <= c < fx + 7 and fy <= rr < fy + 7 for fx, fy in finders): continue
            if M[rr][c]:
                X, Y = x0 + c * m, y0 + rr * m
                d.rounded_rectangle([X + m * .05, Y + m * .05, X + m * .95, Y + m * .95], radius=m * .28, fill=INK)
    for f in finders: finder(*f)
    hs = m * 3
    d.ellipse([cx - hs * 1.15, cy - hs * 1.15, cx + hs * 1.15, cy + hs * 1.15], fill=BG)
    d.polygon(heart_poly(cx, cy - hs * .1, hs / 17), fill=PINK)
    img.save(path)

def check(path, under=(255, 255, 255)):
    src = Image.open(path).convert('RGBA'); bgimg = Image.new('RGBA', src.size, under + (255,))
    im = cv2.cvtColor(np.asarray(Image.alpha_composite(bgimg, src).convert('RGB')), cv2.COLOR_RGB2BGR)
    im = cv2.resize(im, (800, 800 * im.shape[0] // im.shape[1]))
    res, _ = cv2.wechat_qrcode_WeChatQRCode().detectAndDecode(im)   # 휴대폰 스캐너와 비슷한 ZXing 계열 검출기
    return res[0] if res else ''

def unmatte(src, dst, bg, keep=None):
    """배경색을 투명하게(누끼). keep 마스크 안쪽은 배경색 그대로 남긴다."""
    a = np.asarray(Image.open(src).convert('RGB')).astype(float); B = np.array(bg, float)
    dist = np.abs(a - B).max(-1); alpha = np.clip(dist / 120, 0, 1)        # 배경에서 멀수록 불투명
    rgb = np.where(alpha[..., None] > 0, (a - B * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 1e-6), B)
    if keep is not None:                                                  # 하트 안쪽은 아이보리 바탕 유지
        rgb = np.where(keep[..., None], a, rgb); alpha = np.where(keep, 1, alpha)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(dst)

def heart_mask(W=2000):
    m = Image.new('L', (W, W), 0)
    ImageDraw.Draw(m).polygon(heart_poly(W / 2, W * 0.47, W / 36), fill=255)
    return np.asarray(m) > 0

if __name__ == '__main__':
    plain('qr/qr-basic.png'); heart('qr/qr-heart.png')
    unmatte('qr/qr-heart.png', 'qr/qr-heart-cutout.png', BG, keep=heart_mask())   # 하트 밖만 투명
    unmatte('qr/qr-heart.png', 'qr/qr-heart-transparent.png', BG)                # 점과 선만 남김
    unmatte('qr/qr-basic.png', 'qr/qr-basic-transparent.png', (255, 255, 255))  # 검정 칸만 남김
    heart('qr/qr-lace.png', lace=True)
    unmatte('qr/qr-lace.png', 'qr/qr-lace-transparent.png', BG)               # 레이스 하트, 투명 배경
    square_lace('qr/qr-square-lace.png')
    unmatte('qr/qr-square-lace.png', 'qr/qr-square-lace-transparent.png', BG)  # 네모 레이스, 투명 배경
    for f in ('qr/qr-basic.png', 'qr/qr-heart.png', 'qr/qr-heart-cutout.png', 'qr/qr-heart-transparent.png', 'qr/qr-basic-transparent.png', 'qr/qr-lace-transparent.png', 'qr/qr-square-lace-transparent.png'):
        print(f, '→ 흰 바탕:', check(f) or '실패', '/ 연핑크 바탕:', check(f, (244, 214, 214)) or '실패')
